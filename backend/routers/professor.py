"""Professor endpoints."""

from datetime import UTC, date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
    ExtraSlot,
    ProfessorAnnouncement,
    ProfessorProfile,
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
from backend.services import config_service, notification_service, thesis_service

router = APIRouter(prefix="/professor", tags=["professor"])


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
    # Verify professor teaches the course
    cp = await db.scalar(
        select(CourseProfessor).where(
            CourseProfessor.professor_id == user.id,
            CourseProfessor.course_id == body.course_id,
        )
    )
    if not cp:
        raise HTTPException(status_code=403, detail="You don't teach this course")

    if body.academic_event_id:
        event = await db.get(AcademicEvent, body.academic_event_id)
        if not event or event.course_id != body.course_id:
            raise HTTPException(status_code=400, detail="Invalid academic event")

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

    # Notify students in the course
    students = await db.scalars(
        select(User).join(CourseStudent, CourseStudent.student_id == User.id).where(
            CourseStudent.course_id == body.course_id,
            User.role == UserRole.student,
        )
    )
    for student in students:
        await notification_service.notify_user(
            db,
            student.id,
            f"New announcement from {user.first_name} {user.last_name}: {body.title}",
            notification_type="announcement",
            link=f"/student/announcements",  # or something
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
    w = ConsultationWindow(
        professor_id=user.id,
        day_of_week=body.day_of_week.lower(),
        time_from=body.time_from,
        time_to=body.time_to,
        window_type=body.type,
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
    e = ExtraSlot(
        professor_id=user.id,
        slot_date=body.date,
        time_from=body.time_from,
        time_to=body.time_to,
        slot_type=body.type,
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
    return [{"id": r.id, "course_id": r.course_id, "vote_count": r.vote_count, "status": r.status.value} for r in rows]


class RequestRespond(BaseModel):
    accept: bool
    session_id: Optional[int] = None


@router.post("/requests/{request_id}/respond")
async def respond_request(
    request_id: int,
    body: RequestRespond,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    r = await db.get(SchedulingRequest, request_id)
    if not r or r.professor_id != user.id:
        raise HTTPException(status_code=404)
    r.status = SchedulingRequestStatus.accepted if body.accept else SchedulingRequestStatus.declined
    r.session_id = body.session_id
    await db.commit()
    return {"ok": True}


@router.get("/thesis-applications")
async def thesis_inbox(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.professor)),
):
    rows = list(
        (
            await db.scalars(
                select(ThesisApplication).where(
                    ThesisApplication.professor_id == user.id,
                    ThesisApplication.status == ThesisApplicationStatus.pending,
                )
            )
        ).all()
    )
    out = []
    for t in rows:
        st = await db.get(User, t.student_id)
        out.append(
            {
                "id": t.id,
                "student_name": f"{st.first_name} {st.last_name}" if st else "",
                "topic_description": t.topic_description,
            }
        )
    return out


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
        q = q.where(ConsultationSession.session_date >= date.today())
    sessions = list((await db.scalars(q)).all())
    sid = [s.id for s in sessions]
    session_map = {s.id: s for s in sessions}
    if not sid:
        return {"grouped": {}}
    bookings = list(
        (await db.scalars(select(Booking).where(Booking.session_id.in_(tuple(sid))))).all()
    )
    grouped: dict[str, list] = {}
    for b in bookings:
        cs = session_map.get(b.session_id)
        ctype = cs.consultation_type if cs else None
        show_name = ctype in (ConsultationType.graded_work_review, ConsultationType.thesis)
        student_name = None
        if show_name:
            st = await db.get(User, b.student_id)
            student_name = f"{st.first_name} {st.last_name}" if st else None
        key = f"{cs.session_date} {cs.time_from} ({ctype.value if ctype else ''})" if cs else "Unknown"
        grouped.setdefault(key, []).append(
            {
                "id": b.id,
                "student_name": student_name,
                "anonymous_question": b.anonymous_question,
                "group_size": b.group_size,
                "is_urgent": b.is_urgent,
                "status": b.status.value,
                "task": b.task,
            }
        )
    return {"grouped": grouped}


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
    students = (
        await db.scalars(select(User).join(CourseStudent, CourseStudent.student_id == User.id).where(CourseStudent.course_id == body.course_id))
    ).all()
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
    students = (
        await db.scalars(select(User).join(CourseStudent, CourseStudent.student_id == User.id).where(CourseStudent.course_id == body.course_id))
    ).all()
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
    cutoff = date.today() + timedelta(days=days_ahead)
    upcoming_events = (
        await db.scalars(
            select(AcademicEvent)
            .join(CourseProfessor, CourseProfessor.course_id == AcademicEvent.course_id)
            .where(
                CourseProfessor.professor_id == user.id,
                AcademicEvent.event_date >= date.today(),
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
                ConsultationSession.session_date >= date.today(),
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
