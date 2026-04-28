"""Professor responses to preparation scheduling requests (votes → session)."""

from datetime import UTC, date, datetime, time
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    AcademicEvent,
    ConsultationSession,
    ConsultationType,
    Course,
    CourseProfessor,
    CourseStudent,
    CourseStudentStatus,
    PreparationVote,
    SchedulingRequest,
    SchedulingRequestStatus,
    SessionFormat,
    SessionStatus,
    User,
    UserRole,
)

PREPARATION_SESSION_CAPACITY = 30


def collect_vote_time_hints(session_votes: list[PreparationVote]) -> list[str]:
    """Flatten and de-duplicate preferred_times from preparation votes."""
    raw: list[str] = []
    for v in session_votes:
        if not v.preferred_times:
            continue
        for item in v.preferred_times:
            if isinstance(item, str) and (s := item.strip()):
                raw.append(s)
    seen: set[str] = set()
    out: list[str] = []
    for s in raw:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out[:40]


async def _student_ids_for_course_notifications(
    session: AsyncSession, *, professor_id: int, course_id: int
) -> list[int]:
    """Active students enrolled in course for years this professor teaches (same as professor announcements)."""
    cps = list(
        (
            await session.scalars(
                select(CourseProfessor).where(
                    CourseProfessor.professor_id == professor_id,
                    CourseProfessor.course_id == course_id,
                )
            )
        ).all()
    )
    if not cps:
        return []
    years = {cp.academic_year for cp in cps}
    ids = list(
        (
            await session.scalars(
                select(CourseStudent.student_id).where(
                    CourseStudent.course_id == course_id,
                    CourseStudent.academic_year.in_(years),
                    CourseStudent.status == CourseStudentStatus.active,
                ).distinct()
            )
        ).all()
    )
    if not ids:
        return []
    users = list(
        (
            await session.scalars(
                select(User).where(User.id.in_(ids), User.role == UserRole.student)
            )
        ).all()
    )
    return [u.id for u in users]


async def respond_preparation_request(
    session: AsyncSession,
    *,
    professor: User,
    request_id: int,
    accept: bool,
    session_id: Optional[int] = None,
    slot_date: Optional[date] = None,
    time_from: Optional[time] = None,
    time_to: Optional[time] = None,
) -> tuple[SchedulingRequest, Optional[ConsultationSession]]:
    """
    Accept or decline a scheduling request.

    When accepting: either link ``session_id`` to an existing preparation session owned by the professor,
    or create a new preparation session from ``slot_date`` / ``time_from`` / ``time_to``.
    Notifies enrolled students (same cohort as course announcements).
    """
    from backend.services import notification_service

    r = await session.get(SchedulingRequest, request_id)
    if not r or r.professor_id != professor.id:
        raise ValueError("Request not found")
    if r.status != SchedulingRequestStatus.pending:
        raise ValueError("This request is no longer pending")

    now = datetime.now(UTC)
    if not accept:
        r.status = SchedulingRequestStatus.declined
        r.responded_at = now
        r.session_id = None
        await session.flush()
        voters = list(
            (
                await session.scalars(
                    select(PreparationVote.student_id).where(
                        PreparationVote.academic_event_id == r.academic_event_id
                    ).distinct()
                )
            ).all()
        )
        for sid in voters:
            await notification_service.notify_user(
                session,
                sid,
                f"Prof. {professor.last_name} will not schedule a group preparation session for this exam vote.",
                notification_type="scheduling_request",
                link="/student/exams",
            )
        await session.flush()
        return r, None

    cs: ConsultationSession | None = None
    if session_id is not None:
        cs = await session.get(ConsultationSession, session_id)
        if not cs or cs.professor_id != professor.id:
            raise ValueError("Invalid session for this professor")
        if cs.consultation_type != ConsultationType.preparation:
            raise ValueError("Linked session must be a preparation session")
        if cs.course_id != r.course_id:
            raise ValueError("Session course does not match the request")
        if cs.event_id is not None and cs.event_id != r.academic_event_id:
            raise ValueError("Session is linked to a different exam event")
    else:
        if slot_date is None or time_from is None or time_to is None:
            raise ValueError("Provide either session_id or slot_date, time_from, and time_to to accept")
        if not isinstance(slot_date, date):
            raise ValueError("Invalid slot date")
        ev = await session.get(AcademicEvent, r.academic_event_id)
        if not ev:
            raise ValueError("Exam event missing for this request")
        cs = ConsultationSession(
            professor_id=professor.id,
            course_id=r.course_id,
            consultation_type=ConsultationType.preparation,
            session_date=slot_date,
            time_from=time_from,
            time_to=time_to,
            format=SessionFormat.in_person,
            status=SessionStatus.confirmed,
            capacity=PREPARATION_SESSION_CAPACITY,
            announced_by_professor=True,
            event_id=r.academic_event_id,
        )
        session.add(cs)
        await session.flush()

    r.status = SchedulingRequestStatus.accepted
    r.session_id = cs.id
    r.responded_at = now
    await session.flush()

    course = await session.get(Course, r.course_id)
    course_label = course.name if course else "the course"
    ev = await session.get(AcademicEvent, r.academic_event_id)
    ev_name = ev.name if ev else "exam"
    date_s = cs.session_date.isoformat()
    tf = cs.time_from.strftime("%H:%M")
    tt = cs.time_to.strftime("%H:%M")

    student_ids = await _student_ids_for_course_notifications(
        session, professor_id=professor.id, course_id=r.course_id
    )
    for sid in student_ids:
        await notification_service.notify_user(
            session,
            sid,
            f"Prof. {professor.last_name} scheduled exam preparation for «{ev_name}» ({course_label}) "
            f"on {date_s} {tf}–{tt}. Book from My Bookings or the booking assistant.",
            notification_type="preparation",
            link="/student/bookings",
        )
    await session.flush()
    return r, cs
