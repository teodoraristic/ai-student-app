"""Exam periods, academic events, registrations, and professor exam notifications."""

from __future__ import annotations

import logging
from calendar import monthrange
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models import (
    AcademicEvent,
    AcademicEventType,
    ConsultationSession,
    ConsultationType,
    ConsultationWindow,
    Course,
    CourseProfessor,
    CourseStudent,
    CourseStudentStatus,
    ExamPeriod,
    ExamRegistration,
    ExamRegistrationStatus,
    ProfessorAnnouncement,
    SessionFormat,
    SessionStatus,
    User,
    UserRole,
    WindowType,
)
from backend.services import notification_service

logger = logging.getLogger(__name__)

_WEEKDAY_TO_INT = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def _utc_today() -> date:
    return datetime.now(UTC).date()


def _registration_deadline_ok(event_date: date) -> bool:
    """Register/cancel allowed only while today is strictly before exam day."""
    return _utc_today() < event_date


async def patch_academic_event(
    session: AsyncSession,
    event_id: int,
    updates: dict[str, Any],
    *,
    clear_exam_period: bool = False,
) -> AcademicEvent:
    """Apply only keys present in ``updates`` (API field names: type, date, ...)."""
    ev = await session.get(AcademicEvent, event_id)
    if not ev:
        raise ValueError("Unknown academic event")
    if "course_id" in updates:
        cid = updates["course_id"]
        c = await session.get(Course, int(cid))
        if not c:
            raise ValueError("Invalid course")
        ev.course_id = int(cid)
    if "type" in updates:
        ev.event_type = updates["type"]
    if "date" in updates:
        ev.event_date = updates["date"]
    if "name" in updates:
        ev.name = updates["name"]
    if "time_from" in updates:
        ev.time_from = updates["time_from"]
    if "time_to" in updates:
        ev.time_to = updates["time_to"]
    if "hall" in updates:
        ev.hall = updates["hall"]
    if clear_exam_period:
        ev.exam_period_id = None
    elif "exam_period_id" in updates:
        ev.exam_period_id = updates["exam_period_id"]
    if "academic_year" in updates:
        ev.academic_year = updates["academic_year"]
    if ev.event_type == AcademicEventType.midterm:
        ev.exam_period_id = None
    ep_id = None if ev.event_type == AcademicEventType.midterm else ev.exam_period_id
    await validate_academic_event_fields(
        session,
        event_type=ev.event_type,
        event_date=ev.event_date,
        exam_period_id=ep_id,
    )
    await session.flush()
    return ev


async def validate_academic_event_fields(
    session: AsyncSession,
    *,
    event_type: AcademicEventType,
    event_date: date,
    exam_period_id: Optional[int],
) -> None:
    if event_type == AcademicEventType.midterm and exam_period_id is not None:
        raise ValueError("Midterm exams must not be linked to an exam period")
    if exam_period_id is not None:
        ep = await session.get(ExamPeriod, exam_period_id)
        if not ep:
            raise ValueError("Invalid exam period")
        if not (ep.date_from <= event_date <= ep.date_to):
            raise ValueError("Exam date must fall within the selected exam period")


async def _student_active_enrollment(
    session: AsyncSession, student_id: int, course_id: int, academic_year: str
) -> bool:
    row = await session.scalar(
        select(CourseStudent).where(
            CourseStudent.student_id == student_id,
            CourseStudent.course_id == course_id,
            CourseStudent.academic_year == academic_year,
            CourseStudent.status == CourseStudentStatus.active,
        )
    )
    return row is not None


async def _primary_professor_name(session: AsyncSession, course_id: int, academic_year: str) -> str | None:
    cp = await session.scalar(
        select(CourseProfessor)
        .where(
            CourseProfessor.course_id == course_id,
            CourseProfessor.academic_year == academic_year,
        )
        .order_by(CourseProfessor.id)
        .limit(1)
    )
    if not cp:
        return None
    u = await session.get(User, cp.professor_id)
    if not u:
        return None
    return f"{u.first_name} {u.last_name}"


async def list_student_eligible_exams(session: AsyncSession, student_id: int) -> list[dict[str, Any]]:
    """Upcoming academic events for courses the student is actively enrolled in (matching academic year)."""
    q = (
        select(AcademicEvent, Course)
        .join(Course, Course.id == AcademicEvent.course_id)
        .join(
            CourseStudent,
            (CourseStudent.course_id == AcademicEvent.course_id)
            & (CourseStudent.student_id == student_id)
            & (CourseStudent.academic_year == AcademicEvent.academic_year)
            & (CourseStudent.status == CourseStudentStatus.active),
        )
        .where(AcademicEvent.event_date >= _utc_today())
        .order_by(AcademicEvent.event_date, AcademicEvent.name)
    )
    rows = list((await session.execute(q)).all())
    out: list[dict[str, Any]] = []
    for ev, course in rows:
        reg = await session.scalar(
            select(ExamRegistration).where(
                ExamRegistration.student_id == student_id,
                ExamRegistration.academic_event_id == ev.id,
            )
        )
        is_registered = reg is not None and reg.status == ExamRegistrationStatus.registered
        count_reg = await session.scalar(
            select(func.count())
            .select_from(ExamRegistration)
            .where(
                ExamRegistration.academic_event_id == ev.id,
                ExamRegistration.status == ExamRegistrationStatus.registered,
            )
        )
        prof_name = await _primary_professor_name(session, course.id, ev.academic_year)
        period_name: str | None = None
        if ev.exam_period_id:
            ep = await session.get(ExamPeriod, ev.exam_period_id)
            if ep:
                period_name = ep.name
        out.append(
            {
                "academic_event_id": ev.id,
                "course_id": course.id,
                "course_code": course.code,
                "course_name": course.name,
                "event_type": ev.event_type.value,
                "event_name": ev.name,
                "event_date": ev.event_date.isoformat(),
                "time_from": ev.time_from.isoformat() if ev.time_from else None,
                "time_to": ev.time_to.isoformat() if ev.time_to else None,
                "hall": ev.hall,
                "exam_period_name": period_name,
                "lecturer_name": prof_name,
                "registration_count": int(count_reg or 0),
                "already_registered": is_registered,
                "can_register": _registration_deadline_ok(ev.event_date) and not is_registered,
            }
        )
    return out


async def list_student_registrations(session: AsyncSession, student_id: int) -> list[dict[str, Any]]:
    """Active and historical rows for the student, but only events on or after today (past sittings omitted)."""
    today = _utc_today()
    q = (
        select(ExamRegistration, AcademicEvent, Course)
        .join(AcademicEvent, AcademicEvent.id == ExamRegistration.academic_event_id)
        .join(Course, Course.id == AcademicEvent.course_id)
        .where(ExamRegistration.student_id == student_id, AcademicEvent.event_date >= today)
        .order_by(AcademicEvent.event_date.asc(), ExamRegistration.id.desc())
    )
    rows = list((await session.execute(q)).all())
    out: list[dict[str, Any]] = []
    for reg, ev, course in rows:
        period_name: str | None = None
        if ev.exam_period_id:
            ep = await session.get(ExamPeriod, ev.exam_period_id)
            if ep:
                period_name = ep.name
        prof_name = await _primary_professor_name(session, course.id, ev.academic_year)
        out.append(
            {
                "registration_id": reg.id,
                "status": reg.status.value,
                "academic_event_id": ev.id,
                "course_code": course.code,
                "course_name": course.name,
                "event_type": ev.event_type.value,
                "event_name": ev.name,
                "event_date": ev.event_date.isoformat(),
                "time_from": ev.time_from.isoformat() if ev.time_from else None,
                "time_to": ev.time_to.isoformat() if ev.time_to else None,
                "hall": ev.hall,
                "exam_period_name": period_name,
                "lecturer_name": prof_name,
                "can_cancel": reg.status == ExamRegistrationStatus.registered
                and _registration_deadline_ok(ev.event_date),
            }
        )
    return out


async def student_academic_event_ids_for_preparation_panel(
    session: AsyncSession, student_id: int
) -> set[int]:
    """
    Exam events relevant for showing announced preparation sessions:
    upcoming eligible exams on enrolled courses, plus exams the student is registered for.
    """
    eligible = await list_student_eligible_exams(session, student_id)
    ids: set[int] = {int(r["academic_event_id"]) for r in eligible}
    for row in await list_student_registrations(session, student_id):
        if row["status"] == ExamRegistrationStatus.registered.value:
            ids.add(int(row["academic_event_id"]))
    return ids


async def register_for_exam(session: AsyncSession, student_id: int, academic_event_id: int) -> ExamRegistration:
    ev = await session.get(AcademicEvent, academic_event_id)
    if not ev:
        raise ValueError("Unknown exam event")
    if ev.event_date < _utc_today():
        raise ValueError("Cannot register for a past exam")
    if not _registration_deadline_ok(ev.event_date):
        raise ValueError("Registration is closed for this exam")
    if not await _student_active_enrollment(session, student_id, ev.course_id, ev.academic_year):
        raise ValueError("You are not enrolled in this course for this academic year")
    existing = await session.scalar(
        select(ExamRegistration).where(
            ExamRegistration.student_id == student_id,
            ExamRegistration.academic_event_id == academic_event_id,
        )
    )
    if existing:
        if existing.status == ExamRegistrationStatus.registered:
            raise ValueError("Already registered for this exam")
        existing.status = ExamRegistrationStatus.registered
        existing.registered_at = datetime.now(UTC)
        existing.cancelled_at = None
        await session.flush()
        return existing
    reg = ExamRegistration(
        student_id=student_id,
        academic_event_id=academic_event_id,
        status=ExamRegistrationStatus.registered,
    )
    session.add(reg)
    await session.flush()
    return reg


async def cancel_registration(session: AsyncSession, student_id: int, registration_id: int) -> None:
    reg = await session.get(ExamRegistration, registration_id)
    if not reg or reg.student_id != student_id:
        raise ValueError("Registration not found")
    ev = await session.get(AcademicEvent, reg.academic_event_id)
    if not ev:
        raise ValueError("Invalid registration")
    if reg.status != ExamRegistrationStatus.registered:
        raise ValueError("Registration is not active")
    if not _registration_deadline_ok(ev.event_date):
        raise ValueError("Cancellation is no longer allowed for this exam")
    reg.status = ExamRegistrationStatus.cancelled
    reg.cancelled_at = datetime.now(UTC)
    await session.flush()


async def list_student_exams_calendar(
    session: AsyncSession, student_id: int, *, year: int, month: int
) -> list[dict[str, Any]]:
    if not (1 <= month <= 12) or not (2000 <= year <= 2100):
        raise ValueError("Invalid calendar month")
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])
    q = (
        select(ExamRegistration, AcademicEvent, Course)
        .join(AcademicEvent, AcademicEvent.id == ExamRegistration.academic_event_id)
        .join(Course, Course.id == AcademicEvent.course_id)
        .where(
            ExamRegistration.student_id == student_id,
            ExamRegistration.status == ExamRegistrationStatus.registered,
            AcademicEvent.event_date >= first,
            AcademicEvent.event_date <= last,
        )
        .order_by(AcademicEvent.event_date, AcademicEvent.time_from)
    )
    rows = list((await session.execute(q)).all())
    out: list[dict[str, Any]] = []
    for reg, ev, course in rows:
        out.append(
            {
                "registration_id": reg.id,
                "academic_event_id": ev.id,
                "session_date": ev.event_date.isoformat(),
                "time_from": (ev.time_from or time(0, 0)).isoformat(timespec="seconds"),
                "time_to": (ev.time_to or time(23, 59)).isoformat(timespec="seconds"),
                "course_code": course.code,
                "course_name": course.name,
                "event_type": ev.event_type.value,
                "event_name": ev.name,
                "hall": ev.hall or "",
            }
        )
    return out


async def list_professor_exams(session: AsyncSession, professor_id: int) -> list[dict[str, Any]]:
    q = (
        select(AcademicEvent, Course)
        .join(CourseProfessor, CourseProfessor.course_id == AcademicEvent.course_id)
        .join(Course, Course.id == AcademicEvent.course_id)
        .where(
            CourseProfessor.professor_id == professor_id,
            CourseProfessor.academic_year == AcademicEvent.academic_year,
        )
        .distinct()
        .order_by(AcademicEvent.event_date, AcademicEvent.name)
    )
    rows = list((await session.execute(q)).all())
    today = _utc_today()

    sent_rows = (
        await session.execute(
            select(ProfessorAnnouncement.academic_event_id, ProfessorAnnouncement.announcement_type).where(
                ProfessorAnnouncement.professor_id == professor_id,
                ProfessorAnnouncement.academic_event_id.is_not(None),
            )
        )
    ).all()
    sent_by_event: dict[int, set[str]] = {}
    for eid, atype in sent_rows:
        if eid is None:
            continue
        sent_by_event.setdefault(int(eid), set()).add(str(atype))

    out: list[dict[str, Any]] = []
    for ev, course in rows:
        cnt = await session.scalar(
            select(func.count())
            .select_from(ExamRegistration)
            .where(
                ExamRegistration.academic_event_id == ev.id,
                ExamRegistration.status == ExamRegistrationStatus.registered,
            )
        )
        sent = sent_by_event.get(ev.id, set())
        prep_sent = "preparation" in sent
        graded_sent = "graded_work_review" in sent
        out.append(
            {
                "academic_event_id": ev.id,
                "course_id": course.id,
                "course_code": course.code,
                "course_name": course.name,
                "event_type": ev.event_type.value,
                "event_name": ev.name,
                "event_date": ev.event_date.isoformat(),
                "time_from": ev.time_from.isoformat() if ev.time_from else None,
                "time_to": ev.time_to.isoformat() if ev.time_to else None,
                "hall": ev.hall,
                "registration_count": int(cnt or 0),
                "preparation_notice_sent": prep_sent,
                "graded_review_notice_sent": graded_sent,
                "can_notify_preparation": today < ev.event_date and not prep_sent,
                "can_notify_graded_review": today > ev.event_date and not graded_sent,
            }
        )
    return out


def _last_weekday_before(end_exclusive: date, weekday_index: int) -> date | None:
    d = end_exclusive - timedelta(days=1)
    for _ in range(7):
        if d.weekday() == weekday_index:
            return d
        d -= timedelta(days=1)
    return None


def _first_weekday_on_or_after(start: date, weekday_index: int) -> date:
    d = start
    for _ in range(8):
        if d.weekday() == weekday_index:
            return d
        d += timedelta(days=1)
    return start


async def suggest_consultation_slot(
    session: AsyncSession,
    professor_id: int,
    *,
    event_date: date,
    purpose: Literal["preparation", "graded_review"],
) -> dict[str, Any | None]:
    windows = list(
        (
            await session.scalars(
                select(ConsultationWindow).where(
                    ConsultationWindow.professor_id == professor_id,
                    ConsultationWindow.is_active.is_(True),
                    ConsultationWindow.window_type == WindowType.regular,
                )
            )
        ).all()
    )
    if not windows:
        return {"date": None, "time_from": None, "time_to": None}

    best: tuple[date, time, time] | None = None
    today = _utc_today()

    if purpose == "preparation":
        for w in windows:
            try:
                dow = _WEEKDAY_TO_INT[w.day_of_week.strip().lower()]
            except KeyError:
                continue
            cand = _last_weekday_before(event_date, dow)
            if cand is None:
                continue
            if best is None or cand > best[0] or (cand == best[0] and w.time_from > best[1]):
                best = (cand, w.time_from, w.time_to)
    else:
        for w in windows:
            try:
                dow = _WEEKDAY_TO_INT[w.day_of_week.strip().lower()]
            except KeyError:
                continue
            cand = _first_weekday_on_or_after(today, dow)
            if best is None or cand < best[0] or (cand == best[0] and w.time_from < best[1]):
                best = (cand, w.time_from, w.time_to)

    if not best:
        return {"date": None, "time_from": None, "time_to": None}
    d, tf, tt = best
    return {
        "date": d.isoformat(),
        "time_from": tf.isoformat(timespec="seconds"),
        "time_to": tt.isoformat(timespec="seconds"),
    }


async def professor_owns_event(session: AsyncSession, professor_id: int, academic_event_id: int) -> bool:
    ev = await session.get(AcademicEvent, academic_event_id)
    if not ev:
        return False
    cp = await session.scalar(
        select(CourseProfessor).where(
            CourseProfessor.professor_id == professor_id,
            CourseProfessor.course_id == ev.course_id,
            CourseProfessor.academic_year == ev.academic_year,
        )
    )
    return cp is not None


async def notify_exam_session(
    session: AsyncSession,
    professor: User,
    academic_event_id: int,
    *,
    purpose: Literal["preparation", "graded_review"],
    slot_date: date,
    time_from: time,
    time_to: time,
    title: str | None,
    message: str | None,
) -> ProfessorAnnouncement:
    if professor.role != UserRole.professor:
        raise ValueError("Only professors can send this notification")
    ev = await session.get(AcademicEvent, academic_event_id)
    if not ev:
        raise ValueError("Unknown exam event")
    if not await professor_owns_event(session, professor.id, academic_event_id):
        raise ValueError("You do not teach this course for this academic year")
    today = _utc_today()
    if purpose == "preparation" and not (today < ev.event_date):
        raise ValueError("Preparation notices are only available before the exam date")
    if purpose == "graded_review" and not (today > ev.event_date):
        raise ValueError("Graded work review notices are only available after the exam date")

    ann_type = "preparation" if purpose == "preparation" else "graded_work_review"
    dup = int(
        await session.scalar(
            select(func.count())
            .select_from(ProfessorAnnouncement)
            .where(
                ProfessorAnnouncement.academic_event_id == academic_event_id,
                ProfessorAnnouncement.professor_id == professor.id,
                ProfessorAnnouncement.announcement_type == ann_type,
            )
        )
        or 0
    )
    if dup > 0:
        raise ValueError(
            "You already sent this notice for this exam. Students still have the earlier message and booking link."
        )

    course = await session.get(Course, ev.course_id)
    course_label = course.name if course else "your course"
    slot_label = f"{slot_date.isoformat()} {time_from.strftime('%H:%M')}–{time_to.strftime('%H:%M')}"
    default_title = (
        f"Exam preparation: {ev.name}"
        if purpose == "preparation"
        else f"Graded work review: {ev.name}"
    )
    default_message = (
        f"I will hold an exam preparation session for «{ev.name}» ({course_label}) on {slot_label}. "
        f"Please book a consultation slot if you wish to attend."
        if purpose == "preparation"
        else f"I have graded work for «{ev.name}» ({course_label}). "
        f"Review session: {slot_label}. Please book a consultation slot if you wish to attend."
    )
    if purpose == "preparation":
        cs = ConsultationSession(
            professor_id=professor.id,
            course_id=ev.course_id,
            consultation_type=ConsultationType.preparation,
            session_date=slot_date,
            time_from=time_from,
            time_to=time_to,
            format=SessionFormat.in_person,
            status=SessionStatus.confirmed,
            capacity=30,
            announced_by_professor=True,
            event_id=academic_event_id,
        )
    else:
        cs = ConsultationSession(
            professor_id=professor.id,
            course_id=ev.course_id,
            consultation_type=ConsultationType.graded_work_review,
            session_date=slot_date,
            time_from=time_from,
            time_to=time_to,
            format=SessionFormat.in_person,
            status=SessionStatus.confirmed,
            capacity=20,
            announced_by_professor=True,
            event_id=academic_event_id,
        )
    session.add(cs)
    await session.flush()

    ann = ProfessorAnnouncement(
        professor_id=professor.id,
        course_id=ev.course_id,
        academic_event_id=academic_event_id,
        announcement_type=ann_type,
        title=(title or default_title)[:255],
        message=message or default_message,
        expires_at=None,
    )
    session.add(ann)
    await session.flush()

    students = list(
        (
            await session.scalars(
                select(User)
                .join(CourseStudent, CourseStudent.student_id == User.id)
                .where(
                    CourseStudent.course_id == ev.course_id,
                    CourseStudent.academic_year == ev.academic_year,
                    CourseStudent.status == CourseStudentStatus.active,
                    User.role == UserRole.student,
                )
            )
        ).all()
    )
    if purpose == "preparation":
        link = (
            f"/student?prepFlow=1&courseId={ev.course_id}&professorId={professor.id}"
            f"&eventId={academic_event_id}&sessionId={cs.id}"
        )
        notif_type = "preparation"
    else:
        link = (
            f"/student?gradedReviewFlow=1&courseId={ev.course_id}&professorId={professor.id}"
            f"&eventId={academic_event_id}&sessionId={cs.id}"
        )
        notif_type = "graded_review"
    for stu in students:
        await notification_service.notify_user(
            session,
            stu.id,
            f"New announcement from {professor.first_name} {professor.last_name}: {ann.title}",
            notification_type=notif_type,
            link=link,
        )
    return ann
