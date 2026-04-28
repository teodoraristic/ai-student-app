"""Professor endpoints."""

import logging
from collections import defaultdict
from datetime import UTC, date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import delete, func, select
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dates import utc_today
from backend.db.base import get_db
from backend.db.models import (
    AcademicEvent,
    Booking,
    BookingStatus,
    BlockedDate,
    ConsultationSession,
    ConsultationWindow,
    ConsultationType,
    Course,
    CourseProfessor,
    CourseStudent,
    CourseStudentStatus,
    ExtraSlot,
    ProfessorAnnouncement,
    ProfessorProfile,
    PreparationVote,
    SchedulingRequest,
    SchedulingRequestStatus,
    SessionFormat,
    SessionStatus,
    ThesisApplication,
    ThesisApplicationStatus,
    User,
    UserRole,
    WindowType,
)
from backend.middleware.auth_middleware import require_role
from backend.services import (
    booking_service,
    config_service,
    exam_service,
    notification_service,
    scheduling_service,
    thesis_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/professor", tags=["professor"])

_PROFESSOR_BOOKING_STATUS_EDGES: dict[BookingStatus, frozenset[BookingStatus]] = {
    BookingStatus.active: frozenset(
        {BookingStatus.attended, BookingStatus.no_show, BookingStatus.cancelled}
    ),
}


async def _students_for_professor_course_notification(
    db: AsyncSession,
    *,
    professor_id: int,
    course_id: int,
) -> list[User]:
    """Students actively enrolled in ``course_id`` for an academic year this professor teaches; 403 if none."""
    cps = list(
        (
            await db.scalars(
                select(CourseProfessor).where(
                    CourseProfessor.professor_id == professor_id,
                    CourseProfessor.course_id == course_id,
                )
            )
        ).all()
    )
    if not cps:
        raise HTTPException(status_code=403, detail="You don't teach this course")
    years = {cp.academic_year for cp in cps}
    student_ids = list(
        (
            await db.scalars(
                select(CourseStudent.student_id).where(
                    CourseStudent.course_id == course_id,
                    CourseStudent.academic_year.in_(years),
                    CourseStudent.status == CourseStudentStatus.active,
                ).distinct()
            )
        ).all()
    )
    if not student_ids:
        return []
    return list(
        (
            await db.scalars(
                select(User).where(User.id.in_(student_ids), User.role == UserRole.student)
            )
        ).all()
    )


class ProfilePatch(BaseModel):
    department: Optional[str] = None
    office_location: Optional[str] = None
    default_room: Optional[str] = None
    hall: Optional[str] = None
    pinned_note: Optional[str] = None
    max_thesis_students: Optional[int] = Field(default=None, ge=0, le=100)
    photo_url: Optional[str] = None


class AnnouncementCreate(BaseModel):
    course_id: int
    academic_event_id: Optional[int] = None
    announcement_type: str = Field(..., pattern=r"^(preparation|graded_work_review|general)$")
    title: str = Field(..., max_length=255)
    message: str
    expires_at: Optional[datetime] = None


@router.get("/profile")
async def get_profile(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    p = await db.scalar(select(ProfessorProfile).where(ProfessorProfile.user_id == user.id))
    if not p:
        raise HTTPException(status_code=404)
    return {
        "department": p.department,
        "office_location": p.office_location,
        "default_room": p.default_room,
        "pinned_note": p.pinned_note,
        "max_thesis_students": p.max_thesis_students,
        "photo_url": p.photo_url,
    }


@router.patch("/profile")
async def patch_profile(
    body: ProfilePatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    p = await db.scalar(select(ProfessorProfile).where(ProfessorProfile.user_id == user.id))
    if not p:
        raise HTTPException(status_code=404)
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(p, k, v)
    await db.commit()
    return {"ok": True}


@router.post("/announcements")
async def create_announcement(
    body: AnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    if body.academic_event_id:
        event = await db.get(AcademicEvent, body.academic_event_id)
        if not event or event.course_id != body.course_id:
            raise HTTPException(status_code=400, detail="Invalid academic event")

    students = await _students_for_professor_course_notification(
        db, professor_id=user.id, course_id=body.course_id
    )

    ann = ProfessorAnnouncement(
        professor_id=user.id,
        course_id=body.course_id,
        academic_event_id=body.academic_event_id,
        announcement_type=body.announcement_type,
        title=body.title,
        message=body.message,
        expires_at=body.expires_at,
    )
    db.add(ann)
    await db.flush()

    for student in students:
        await notification_service.notify_user(
            db,
            student.id,
            f"New announcement from {user.first_name} {user.last_name}: {body.title}",
            notification_type="announcement",
            link="/student/exams",
        )

    await db.commit()
    return {"id": ann.id}


class WindowBody(BaseModel):
    day_of_week: str
    time_from: time
    time_to: time
    type: WindowType


@router.get("/windows")
async def list_windows(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    rows = list(
        (await db.scalars(select(ConsultationWindow).where(ConsultationWindow.professor_id == user.id))).all()
    )
    return [
        {
            "id": w.id,
            "day_of_week": w.day_of_week,
            "time_from": w.time_from.isoformat(),
            "time_to": w.time_to.isoformat(),
            "type": w.window_type.value,
        }
        for w in rows
    ]


@router.post("/windows")
async def add_window(
    body: WindowBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    slot_duration = 60 if body.type == WindowType.thesis else 15
    w = ConsultationWindow(
        professor_id=user.id,
        day_of_week=body.day_of_week.lower(),
        time_from=body.time_from,
        time_to=body.time_to,
        window_type=body.type,
        slot_duration_minutes=slot_duration,
    )
    db.add(w)
    await db.commit()
    return {"id": w.id}


@router.delete("/windows/{window_id}")
async def del_window(
    window_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    res = await db.execute(
        delete(ConsultationWindow).where(
            ConsultationWindow.id == window_id, ConsultationWindow.professor_id == user.id
        )
    )
    if res.rowcount == 0:
        raise HTTPException(status_code=404)
    await db.commit()
    return {"ok": True}


class BlockBody(BaseModel):
    date: date
    reason: Optional[str] = None


@router.get("/blocked-dates")
async def list_blocked(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    rows = list((await db.scalars(select(BlockedDate).where(BlockedDate.professor_id == user.id))).all())
    return [{"id": r.id, "date": r.blocked_date.isoformat(), "reason": r.reason} for r in rows]


@router.post("/blocked-dates")
async def add_block(
    body: BlockBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    b = BlockedDate(professor_id=user.id, blocked_date=body.date, reason=body.reason)
    db.add(b)
    await db.flush()
    # Cancel any existing sessions on that date and notify students
    affected_sessions = list(
        (await db.scalars(
            select(ConsultationSession).where(
                ConsultationSession.professor_id == user.id,
                ConsultationSession.session_date == body.date,
                ConsultationSession.status != SessionStatus.cancelled,
            )
        )).all()
    )
    for cs in affected_sessions:
        cs.status = SessionStatus.cancelled
        active_bookings = list(
            (await db.scalars(
                select(Booking).where(Booking.session_id == cs.id, Booking.status == BookingStatus.active)
            )).all()
        )
        for bk in active_bookings:
            bk.status = BookingStatus.cancelled
            bk.cancelled_at = datetime.now(UTC)
            await notification_service.notify_user(
                db,
                bk.student_id,
                f"Your consultation on {body.date} was cancelled — professor marked that day as unavailable.",
                notification_type="cancel",
            )
    await db.commit()
    return {"id": b.id}


@router.delete("/blocked-dates/{block_id}")
async def del_block(
    block_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    res = await db.execute(
        delete(BlockedDate).where(BlockedDate.id == block_id, BlockedDate.professor_id == user.id)
    )
    if res.rowcount == 0:
        raise HTTPException(status_code=404)
    await db.commit()
    return {"ok": True}


class ExtraBody(BaseModel):
    date: date
    time_from: time
    time_to: time
    type: ConsultationType


@router.get("/extra-slots")
async def list_extra(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    rows = list((await db.scalars(select(ExtraSlot).where(ExtraSlot.professor_id == user.id))).all())
    return [
        {
            "id": r.id,
            "date": r.slot_date.isoformat(),
            "time_from": r.time_from.isoformat(),
            "time_to": r.time_to.isoformat(),
            "type": r.slot_type.value,
        }
        for r in rows
    ]


@router.post("/extra-slots")
async def add_extra(
    body: ExtraBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    extra_wtype = WindowType.thesis if body.type == ConsultationType.thesis else WindowType.regular
    extra_slot_mins = 60 if body.type == ConsultationType.thesis else 15
    e = ExtraSlot(
        professor_id=user.id,
        slot_date=body.date,
        time_from=body.time_from,
        time_to=body.time_to,
        slot_type=extra_wtype,
        slot_duration_minutes=extra_slot_mins,
    )
    db.add(e)
    await db.flush()

    if body.type == ConsultationType.graded_work_review:
        # Notify students in courses taught by this professor
        courses = await db.scalars(
            select(Course).join(CourseProfessor).where(CourseProfessor.professor_id == user.id)
        )
        for course in courses:
            students = await db.scalars(
                select(User).join(CourseStudent).where(
                    CourseStudent.course_id == course.id,
                    User.role == UserRole.student,
                )
            )
            for student in students:
                await notification_service.notify_user(
                    db,
                    student.id,
                    f"Graded work review session available for {course.name}. Book now!",
                    notification_type="booking",
                )

    await db.commit()
    return {"id": e.id}


@router.delete("/extra-slots/{slot_id}")
async def del_extra(
    slot_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    res = await db.execute(
        delete(ExtraSlot).where(ExtraSlot.id == slot_id, ExtraSlot.professor_id == user.id)
    )
    if res.rowcount == 0:
        raise HTTPException(status_code=404)
    await db.commit()
    return {"ok": True}


@router.get("/requests")
async def scheduling_requests(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    rows = list(
        (await db.scalars(select(SchedulingRequest).where(SchedulingRequest.professor_id == user.id))).all()
    )
    event_ids = [r.academic_event_id for r in rows]
    votes_by_event: defaultdict[int, list[PreparationVote]] = defaultdict(list)
    if event_ids:
        vote_rows = list(
            (
                await db.scalars(
                    select(PreparationVote).where(PreparationVote.academic_event_id.in_(event_ids))
                )
            ).all()
        )
        for v in vote_rows:
            votes_by_event[v.academic_event_id].append(v)

    out = []
    for r in rows:
        course = await db.get(Course, r.course_id)
        event = await db.get(AcademicEvent, r.academic_event_id)
        hints = scheduling_service.collect_vote_time_hints(votes_by_event.get(r.academic_event_id, []))
        out.append(
            {
                "id": r.id,
                "course_id": r.course_id,
                "course_code": course.code if course else None,
                "course_name": course.name if course else None,
                "academic_event_id": r.academic_event_id,
                "event_name": event.name if event else None,
                "event_date": event.event_date.isoformat() if event else None,
                "event_type": event.event_type.value if event else None,
                "vote_count": r.vote_count,
                "status": r.status.value,
                "deadline_at": r.deadline_at.isoformat(),
                "created_at": r.created_at.isoformat(),
                "student_time_preferences": hints,
            }
        )
    return out


class RequestRespond(BaseModel):
    accept: bool
    session_id: Optional[int] = None
    slot_date: Optional[date] = None
    time_from: Optional[time] = None
    time_to: Optional[time] = None

    @model_validator(mode="after")
    def accept_requires_slot_or_session(self):
        if self.accept and self.session_id is None:
            if self.slot_date is None or self.time_from is None or self.time_to is None:
                raise ValueError(
                    "When accepting, provide either session_id or slot_date, time_from, and time_to"
                )
        return self


@router.post("/requests/{request_id}/respond")
async def respond_request(
    request_id: int,
    body: RequestRespond,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    try:
        _r, cs = await scheduling_service.respond_preparation_request(
            db,
            professor=user,
            request_id=request_id,
            accept=body.accept,
            session_id=body.session_id,
            slot_date=body.slot_date,
            time_from=body.time_from,
            time_to=body.time_to,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        msg = str(e)
        code = 404 if msg == "Request not found" else 400
        raise HTTPException(status_code=code, detail=msg)
    return {"ok": True, "session_id": cs.id if cs else None}


@router.get("/thesis-applications")
async def thesis_inbox(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    pending_rows = list(
        (
            await db.scalars(
                select(ThesisApplication).where(
                    ThesisApplication.professor_id == user.id,
                    ThesisApplication.status == ThesisApplicationStatus.pending,
                )
            )
        ).all()
    )
    mentee_rows = list(
        (
            await db.scalars(
                select(ThesisApplication).where(
                    ThesisApplication.professor_id == user.id,
                    ThesisApplication.status == ThesisApplicationStatus.active,
                )
            )
        ).all()
    )
    pending_out = []
    for t in pending_rows:
        st = await db.get(User, t.student_id)
        pending_out.append(
            {
                "id": t.id,
                "student_name": f"{st.first_name} {st.last_name}" if st else "",
                "topic_description": t.topic_description,
            }
        )
    mentees_out = []
    for t in mentee_rows:
        st = await db.get(User, t.student_id)
        mentees_out.append(
            {
                "application_id": t.id,
                "student_name": f"{st.first_name} {st.last_name}" if st else "",
                "topic_description": t.topic_description,
            }
        )
    return {"pending": pending_out, "mentees": mentees_out}


class ThesisRespond(BaseModel):
    accept: bool


@router.post("/thesis-applications/{app_id}/respond")
async def thesis_respond(
    app_id: int,
    body: ThesisRespond,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    t = await db.get(ThesisApplication, app_id)
    if not t or t.professor_id != user.id:
        raise HTTPException(status_code=404)
    if t.status != ThesisApplicationStatus.pending:
        raise HTTPException(status_code=400, detail="This thesis application has already been processed.")

    now = datetime.now(UTC)
    st = await db.get(User, t.student_id)

    if body.accept:
        active_here = await thesis_service.count_active_thesis_for_professor(db, user.id)
        cap = await thesis_service.get_max_thesis_students(db, user.id)
        if cap <= 0 or active_here >= cap:
            raise HTTPException(
                status_code=400,
                detail="You have reached your maximum number of active thesis students (or capacity is not set).",
            )

    if body.accept and st and st.thesis_professor_id and st.thesis_professor_id != user.id:
        current_prof = await db.get(User, st.thesis_professor_id)
        current_prof_name = (
            f"{current_prof.first_name} {current_prof.last_name}" if current_prof else "another professor"
        )
        raise HTTPException(
            status_code=400,
            detail=f"This student already has approved thesis supervision with {current_prof_name}.",
        )

    t.status = ThesisApplicationStatus.active if body.accept else ThesisApplicationStatus.rejected
    t.responded_at = now
    if st:
        if body.accept:
            st.thesis_professor_id = user.id
            other_apps = list(
                (
                    await db.scalars(
                        select(ThesisApplication).where(
                            ThesisApplication.student_id == st.id,
                            ThesisApplication.id != t.id,
                            ThesisApplication.status.in_(
                                [ThesisApplicationStatus.pending, ThesisApplicationStatus.active]
                            ),
                        )
                    )
                ).all()
            )
            for other in other_apps:
                other.status = ThesisApplicationStatus.rejected
                other.responded_at = now
        await notification_service.notify_user(
            db,
            st.id,
            "Your thesis application was accepted."
            if body.accept
            else "Your thesis application was rejected.",
            notification_type="thesis",
        )
        if body.accept and st:
            await db.flush()
            await thesis_service.try_auto_book_thesis_intro_session(
                db,
                student=st,
                professor_id=user.id,
                topic_description=t.topic_description or "",
            )
    await db.commit()
    return {"ok": True}


@router.get("/bookings")
async def prof_bookings(
    upcoming: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    q = select(ConsultationSession).where(ConsultationSession.professor_id == user.id)
    if upcoming:
        q = q.where(ConsultationSession.session_date >= utc_today()).order_by(
            ConsultationSession.session_date,
            ConsultationSession.time_from,
            ConsultationSession.id,
        )
    else:
        q = q.where(ConsultationSession.session_date < utc_today()).order_by(
            ConsultationSession.session_date.desc(),
            ConsultationSession.time_from.desc(),
            ConsultationSession.id.desc(),
        )
    sessions = list((await db.scalars(q)).all())
    sid = [s.id for s in sessions]
    session_map = {s.id: s for s in sessions}
    if not sid:
        return {"sessions": []}
    profile = await db.scalar(select(ProfessorProfile).where(ProfessorProfile.user_id == user.id))
    hall = ""
    if profile:
        hall = (profile.hall or "").strip() or (profile.default_room or "").strip()
    course_ids = {s.course_id for s in sessions if s.course_id}
    course_by_id: dict[int, tuple[str, str]] = {}
    for cid in course_ids:
        co = await db.get(Course, cid)
        if co:
            course_by_id[cid] = (co.code, co.name)
    bookings = list(
        (await db.scalars(select(Booking).where(Booking.session_id.in_(tuple(sid))))).all()
    )
    by_session: dict[int, list[Booking]] = defaultdict(list)
    for b in bookings:
        by_session[b.session_id].append(b)

    out: list[dict] = []
    for session_id, blist in by_session.items():
        cs = session_map.get(session_id)
        if not cs:
            continue
        ctype = cs.consultation_type
        course_code = course_name = None
        if cs.course_id and cs.course_id in course_by_id:
            course_code, course_name = course_by_id[cs.course_id]
        booking_rows: list[dict] = []
        for b in blist:
            st = await db.get(User, b.student_id)
            student_name = f"{st.first_name} {st.last_name}" if st else None
            booking_rows.append(
                {
                    "id": b.id,
                    "student_name": student_name,
                    "group_size": b.group_size,
                    "status": b.status.value,
                    "task": b.task,
                }
            )
        total_party = sum(
            max(1, int(b.group_size or 1))
            for b in blist
            if b.status != BookingStatus.cancelled
        )
        out.append(
            {
                "session_id": cs.id,
                "session_date": cs.session_date.isoformat(),
                "time_from": cs.time_from.isoformat(),
                "time_to": cs.time_to.isoformat(),
                "consultation_type": ctype.value,
                "course_code": course_code,
                "course_name": course_name,
                "hall": hall or None,
                "session_party_total": total_party,
                "session_booking_count": len(blist),
                "bookings": booking_rows,
            }
        )
    out.sort(key=lambda x: (x["session_date"], x["time_from"]), reverse=not upcoming)
    out = booking_service.merge_professor_slot_cards_for_same_timeslot(out)
    return {"sessions": out}


@router.get("/announced-preparations")
async def professor_announced_preparations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    return await booking_service.list_professor_announced_preparation_overview(db, user.id)


@router.get("/bookings/calendar")
async def professor_bookings_calendar(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    try:
        return await booking_service.list_calendar_bookings(db, user, year=year, month=month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class BookingStatusPatch(BaseModel):
    status: BookingStatus


@router.patch("/bookings/{booking_id}/status")
async def patch_booking_status(
    booking_id: int,
    body: BookingStatusPatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    b = await db.get(Booking, booking_id)
    if not b:
        raise HTTPException(status_code=404)
    cs = await db.get(ConsultationSession, b.session_id)
    if not cs or cs.professor_id != user.id:
        raise HTTPException(status_code=403)
    if b.status != body.status:
        allowed = _PROFESSOR_BOOKING_STATUS_EDGES.get(b.status)
        if not allowed or body.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status transition from {b.status.value} to {body.status.value}",
            )
        b.status = body.status
    await db.commit()
    return {"ok": True}


class AnnouncePreparationBody(BaseModel):
    course_id: int
    date: date
    time_from: time
    time_to: time
    academic_event_id: Optional[int] = None


@router.post("/announce-preparation")
async def announce_preparation(
    body: AnnouncePreparationBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    students = await _students_for_professor_course_notification(
        db, professor_id=user.id, course_id=body.course_id
    )
    cs = ConsultationSession(
        professor_id=user.id,
        course_id=body.course_id,
        consultation_type=ConsultationType.preparation,
        session_date=body.date,
        time_from=body.time_from,
        time_to=body.time_to,
        format=SessionFormat.in_person,
        status=SessionStatus.confirmed,
        capacity=30,
        announced_by_professor=True,
        event_id=body.academic_event_id,
    )
    db.add(cs)
    await db.flush()
    for st in students:
        await notification_service.notify_user(
            db,
            st.id,
            f"Prof. {user.last_name} announced a preparation session on {body.date} {body.time_from}–{body.time_to}.",
            notification_type="preparation",
        )
    await db.commit()
    return {"id": cs.id}


class AnnounceGradedReviewBody(BaseModel):
    course_id: int
    date: date
    time_from: time
    time_to: time
    academic_event_id: Optional[int] = None


@router.post("/announce-graded-review")
async def announce_graded_review(
    body: AnnounceGradedReviewBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    students = await _students_for_professor_course_notification(
        db, professor_id=user.id, course_id=body.course_id
    )
    cs = ConsultationSession(
        professor_id=user.id,
        course_id=body.course_id,
        consultation_type=ConsultationType.graded_work_review,
        session_date=body.date,
        time_from=body.time_from,
        time_to=body.time_to,
        format=SessionFormat.in_person,
        status=SessionStatus.confirmed,
        capacity=20,
        announced_by_professor=True,
        event_id=body.academic_event_id,
    )
    db.add(cs)
    await db.flush()
    for st in students:
        await notification_service.notify_user(
            db,
            st.id,
            f"Prof. {user.last_name} has announced a graded work review on {body.date} {body.time_from}–{body.time_to}. Book your slot now.",
            notification_type="graded_review",
        )
    await db.commit()
    return {"id": cs.id}


@router.get("/dashboard")
async def prof_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    total = await db.scalar(
        select(func.count())
        .select_from(Booking)
        .join(ConsultationSession, ConsultationSession.id == Booking.session_id)
        .where(ConsultationSession.professor_id == user.id)
    )

    days_ahead = await config_service.get_config_int(db, "days_before_exam_trigger", 7)
    from datetime import timedelta
    today = utc_today()
    cutoff = today + timedelta(days=days_ahead)
    upcoming_events = (
        await db.scalars(
            select(AcademicEvent)
            .join(CourseProfessor, CourseProfessor.course_id == AcademicEvent.course_id)
            .where(
                CourseProfessor.professor_id == user.id,
                AcademicEvent.event_date >= today,
                AcademicEvent.event_date <= cutoff,
            )
        )
    ).all()

    reminders = []
    for ev in upcoming_events:
        course = await db.get(Course, ev.course_id)
        has_prep = await db.scalar(
            select(ConsultationSession).where(
                ConsultationSession.professor_id == user.id,
                ConsultationSession.course_id == ev.course_id,
                ConsultationSession.consultation_type == ConsultationType.preparation,
                ConsultationSession.announced_by_professor == True,  # noqa: E712
                ConsultationSession.session_date >= today,
            )
        )
        reminders.append({
            "event_id": ev.id,
            "event_name": ev.name,
            "event_date": ev.event_date.isoformat(),
            "event_type": ev.event_type.value,
            "course_id": ev.course_id,
            "course_name": course.name if course else "",
            "has_preparation_scheduled": has_prep is not None,
        })

    return {
        "total_bookings": int(total or 0),
        "upcoming_exam_reminders": reminders,
    }


@router.get("/exams")
async def professor_list_exams(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    return await exam_service.list_professor_exams(db, user.id)


@router.get("/exams/{event_id}/suggest-slot")
async def professor_exam_suggest_slot(
    event_id: int,
    purpose: str = Query(..., pattern=r"^(preparation|graded_review)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    if not await exam_service.professor_owns_event(db, user.id, event_id):
        raise HTTPException(status_code=404)
    ev = await db.get(AcademicEvent, event_id)
    if not ev:
        raise HTTPException(status_code=404)
    return await exam_service.suggest_consultation_slot(
        db, user.id, event_date=ev.event_date, purpose=purpose  # type: ignore[arg-type]
    )


class ExamNotifyBody(BaseModel):
    purpose: str = Field(..., pattern=r"^(preparation|graded_review)$")
    date: date
    time_from: time
    time_to: time
    title: Optional[str] = Field(default=None, max_length=255)
    message: Optional[str] = None


@router.post("/exams/{event_id}/notify")
async def professor_exam_notify(
    event_id: int,
    body: ExamNotifyBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    try:
        ann = await exam_service.notify_exam_session(
            db,
            user,
            event_id,
            purpose=body.purpose,  # type: ignore[arg-type]
            slot_date=body.date,
            time_from=body.time_from,
            time_to=body.time_to,
            title=body.title,
            message=body.message,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        msg = str(e)
        if "already sent this notice" in msg.lower():
            raise HTTPException(status_code=409, detail=msg) from e
        raise HTTPException(status_code=400, detail=msg) from e
    except (ProgrammingError, DBAPIError) as e:
        await db.rollback()
        logger.exception("professor_exam_notify DB error")
        raw = str(getattr(e, "orig", e))
        if "updated_at" in raw and "professor_announcements" in raw:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Database schema is missing professor_announcements.updated_at. "
                    "From the backend folder run: alembic upgrade head"
                ),
            ) from e
        raise HTTPException(
            status_code=503,
            detail="Database schema error while saving the announcement. Run alembic upgrade head and retry.",
        ) from e
    return {"announcement_id": ann.id}
