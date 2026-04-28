"""Student-facing endpoints."""

from datetime import UTC, date, datetime, time
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import get_db
from backend.db.models import (
    AcademicEvent,
    Announcement,
    Booking,
    BookingStatus,
    ConsultationSession,
    ConsultationType,
    ConsultationWindow,
    Course,
    CourseProfessor,
    CourseStudent,
    Feedback,
    PreparationVote,
    ProfessorProfile,
    SessionStatus,
    ThesisApplication,
    ThesisApplicationStatus,
    User,
    UserRole,
    Waitlist,
    WindowType,
)
from backend.middleware.auth_middleware import require_role
from backend.services import booking_service, exam_service, slot_service, thesis_service, waitlist_service

router = APIRouter(prefix="", tags=["student"])

_WEEKDAY_ORDER = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def _window_sort_key(w: ConsultationWindow) -> tuple[int, time]:
    try:
        di = _WEEKDAY_ORDER.index(w.day_of_week.lower())
    except ValueError:
        di = 99
    return (di, w.time_from)


def _format_consultation_window_line(w: ConsultationWindow) -> str:
    raw = (w.day_of_week or "").lower()
    day = raw[0].upper() + raw[1:] if raw else ""
    tf = w.time_from.strftime("%H:%M")
    tt = w.time_to.strftime("%H:%M")
    return f"{day} {tf}–{tt}"


def _serialize_student_professor_directory(profs: dict[int, dict], user: User) -> list[dict]:
    """Shared JSON shape for course-based professor lists (directory + thesis page)."""
    return [
        {
            "professor_id": prof["professor_id"],
            "name": prof["name"],
            "courses": prof["courses"],
            "department": prof.get("department", ""),
            "open_thesis_spots": prof["open_thesis_spots"],
            "pinned_note": prof.get("pinned_note"),
            "hall": prof.get("hall") or "",
            "consultation_regular_hours": prof.get("consultation_regular_hours", []),
            "consultation_thesis_hours": prof.get("consultation_thesis_hours", []),
            "is_my_thesis_professor": prof["professor_id"] == user.thesis_professor_id,
        }
        for prof in profs.values()
    ]


async def _attach_consultation_hours(db: AsyncSession, professors: dict[int, dict]) -> None:
    """Fill consultation_regular_hours / consultation_thesis_hours for each professor dict."""
    if not professors:
        return
    ids = list(professors.keys())
    wins = list(
        (
            await db.scalars(
                select(ConsultationWindow).where(
                    ConsultationWindow.professor_id.in_(ids),
                    ConsultationWindow.is_active.is_(True),
                )
            )
        ).all()
    )
    by_pid: dict[int, list[ConsultationWindow]] = {}
    for w in wins:
        by_pid.setdefault(w.professor_id, []).append(w)
    for pid, entry in professors.items():
        lst = by_pid.get(pid, [])
        reg = sorted((x for x in lst if x.window_type == WindowType.regular), key=_window_sort_key)
        thes = sorted((x for x in lst if x.window_type == WindowType.thesis), key=_window_sort_key)
        entry["consultation_regular_hours"] = [_format_consultation_window_line(w) for w in reg]
        entry["consultation_thesis_hours"] = [_format_consultation_window_line(w) for w in thes]


async def _student_consultation_professors(
    db: AsyncSession,
    student_id: int,
) -> dict[int, dict]:
    q = (
        select(User, Course)
        .join(CourseProfessor, CourseProfessor.professor_id == User.id)
        .join(CourseStudent, CourseStudent.course_id == CourseProfessor.course_id)
        .join(Course, Course.id == CourseStudent.course_id)
        .where(CourseStudent.student_id == student_id, User.role == UserRole.professor)
        .distinct()
    )
    rows = list((await db.execute(q)).unique().all())
    out: dict[int, dict] = {}
    for prof, course in rows:
        profile = await db.scalar(select(ProfessorProfile).where(ProfessorProfile.user_id == prof.id))
        active_thesis_count = len(
            list(
                (
                    await db.scalars(
                        select(ThesisApplication).where(
                            ThesisApplication.professor_id == prof.id,
                            ThesisApplication.status == ThesisApplicationStatus.active,
                        )
                    )
                ).all()
            )
        )
        max_thesis_students = profile.max_thesis_students if profile else 0
        entry = out.setdefault(
            prof.id,
            {
                "professor_id": prof.id,
                "name": f"{prof.first_name} {prof.last_name}",
                "courses": [],
                "department": (profile.department if profile else "") or "",
                "pinned_note": profile.pinned_note if profile else None,
                "hall": profile.hall if profile else "",
                "open_thesis_spots": max(0, max_thesis_students - active_thesis_count),
            },
        )
        entry["courses"].append({"id": course.id, "name": course.name, "code": course.code})
    return out


@router.get("/announcements")
async def student_announcements(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    _ = user
    now = datetime.now(UTC)
    rows = list((await db.scalars(select(Announcement).order_by(Announcement.published_at.desc()))).all())
    out = []
    for a in rows:
        if a.expires_at and a.expires_at < now:
            continue
        out.append({"id": a.id, "title": a.title, "body": a.body, "published_at": a.published_at.isoformat()})
    return out


class BookingCreate(BaseModel):
    session_id: int
    task: Optional[str] = None
    anonymous_question: Optional[str] = None


class ThesisApplyBody(BaseModel):
    professor_id: int
    topic_description: str = Field(max_length=2000)


@router.get("/professors/mine")
async def my_professors(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    """Professors who teach at least one course the student is enrolled in."""
    profs = await _student_consultation_professors(db, user.id)
    await _attach_consultation_hours(db, profs)
    return _serialize_student_professor_directory(profs, user)


@router.get("/courses/mine")
async def my_courses(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    q = select(Course).join(CourseStudent).where(CourseStudent.student_id == user.id)
    rows = list((await db.scalars(q)).all())
    return [{"id": c.id, "name": c.name, "code": c.code} for c in rows]


@router.get("/courses/with-professors")
async def my_courses_with_professors(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    """Enrolled courses, each with the professor(s) assigned to that course."""
    q = (
        select(Course, User)
        .join(CourseStudent, CourseStudent.course_id == Course.id)
        .join(CourseProfessor, CourseProfessor.course_id == Course.id)
        .join(User, User.id == CourseProfessor.professor_id)
        .where(
            CourseStudent.student_id == user.id,
            User.role == UserRole.professor,
            User.is_active.is_(True),
        )
    )
    rows = list((await db.execute(q)).unique().all())
    by_cid: dict[int, dict[str, Any]] = {}
    for course, prof in rows:
        bucket = by_cid.setdefault(
            course.id,
            {
                "id": course.id,
                "name": course.name,
                "code": course.code,
                "professors": [],
            },
        )
        plist: list[dict[str, Any]] = bucket["professors"]
        pname = f"{prof.first_name} {prof.last_name}"
        if not any(p["id"] == prof.id for p in plist):
            plist.append({"id": prof.id, "name": pname})
    out = list(by_cid.values())
    out.sort(key=lambda x: (x["code"] or "").lower())
    for item in out:
        item["professors"].sort(key=lambda p: p["name"].lower())
    return out


@router.get("/sessions/available")
async def available_sessions(
    professor_id: int = Query(...),
    course_id: int = Query(...),
    consultation_type: ConsultationType = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    try:
        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor_id,
            course_id=course_id,
            ctype=consultation_type,
            group_size=1,
            student_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return [
        {
            "id": s.id,
            "date": s.session_date.isoformat(),
            "time_from": s.time_from.isoformat(),
            "time_to": s.time_to.isoformat(),
            "format": s.format.value,
            "capacity": s.capacity,
        }
        for s in slots
    ]


@router.post("/bookings")
async def create_booking(
    body: BookingCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    try:
        b = await booking_service.create_booking(
            db,
            student=user,
            session_id=body.session_id,
            task=body.task,
            anonymous_question=body.anonymous_question,
            group_size=1,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"id": b.id, "status": b.status.value}


@router.delete("/bookings/{booking_id}")
async def delete_booking(
    booking_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    try:
        await booking_service.cancel_booking(db, student=user, booking_id=booking_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True}


@router.get("/bookings/mine")
async def my_bookings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    rows = list(
        (
            await db.scalars(
                select(Booking)
                .join(ConsultationSession, ConsultationSession.id == Booking.session_id)
                .where(Booking.student_id == user.id)
                .order_by(
                    ConsultationSession.session_date.desc(),
                    ConsultationSession.time_from.desc(),
                    Booking.id.desc(),
                )
            )
        ).all()
    )
    result = []
    for b in rows:
        cs = await db.get(ConsultationSession, b.session_id)
        prof = await db.get(User, cs.professor_id) if cs else None
        course = await db.get(Course, cs.course_id) if cs and cs.course_id else None
        profile = (
            await db.scalar(select(ProfessorProfile).where(ProfessorProfile.user_id == prof.id))
            if prof
            else None
        )
        hall = ""
        if profile:
            hall = (profile.hall or "").strip() or (profile.default_room or "").strip()
        has_feedback = (
            await db.scalar(select(Feedback.id).where(Feedback.booking_id == b.id).limit(1))
        ) is not None
        general_group_attendees, general_group_capacity = await booking_service.general_group_session_counts(
            db, cs
        )
        result.append(
            {
                "id": b.id,
                "session_id": b.session_id,
                "status": b.status.value,
                "priority": b.priority.value,
                "session_date": cs.session_date.isoformat() if cs else None,
                "time_from": cs.time_from.strftime("%H:%M") if cs else None,
                "time_to": cs.time_to.strftime("%H:%M") if cs else None,
                "consultation_type": cs.consultation_type.value if cs else None,
                "professor_name": f"{prof.first_name} {prof.last_name}" if prof else None,
                "course_code": course.code if course else None,
                "course_name": course.name if course else None,
                "hall": hall or None,
                "task": b.task,
                "anonymous_question": b.anonymous_question,
                "has_feedback": has_feedback,
                "general_group_attendees": general_group_attendees,
                "general_group_capacity": general_group_capacity,
            }
        )
    return result


@router.get("/bookings/calendar")
async def bookings_calendar(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    try:
        return await booking_service.list_calendar_bookings(db, user, year=year, month=month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/thesis/professors")
async def thesis_professors(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    profs = await _student_consultation_professors(db, user.id)
    if user.thesis_professor_id and user.thesis_professor_id not in profs:
        prof = await db.get(User, user.thesis_professor_id)
        profile = await db.scalar(
            select(ProfessorProfile).where(ProfessorProfile.user_id == user.thesis_professor_id)
        )
        if prof and profile:
            active_thesis_count = len(
                list(
                    (
                        await db.scalars(
                            select(ThesisApplication).where(
                                ThesisApplication.professor_id == prof.id,
                                ThesisApplication.status == ThesisApplicationStatus.active,
                            )
                        )
                    ).all()
                )
            )
            profs[prof.id] = {
                "professor_id": prof.id,
                "name": f"{prof.first_name} {prof.last_name}",
                "courses": [],
                "department": (profile.department or "") if profile else "",
                "pinned_note": profile.pinned_note,
                "hall": profile.hall,
                "open_thesis_spots": max(0, profile.max_thesis_students - active_thesis_count),
            }
    await _attach_consultation_hours(db, profs)
    return _serialize_student_professor_directory(profs, user)


@router.post("/thesis/apply")
async def thesis_apply(
    body: ThesisApplyBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    if not user.is_final_year:
        raise HTTPException(
            status_code=400,
            detail="Thesis applications are only available to final-year students.",
        )

    if user.thesis_professor_id:
        prof = await db.get(User, user.thesis_professor_id)
        prof_name = f"{prof.first_name} {prof.last_name}" if prof else "your approved professor"
        raise HTTPException(
            status_code=400,
            detail=f"You already have approved thesis supervision with {prof_name}.",
        )

    available_professors = await _student_consultation_professors(db, user.id)
    if body.professor_id not in available_professors:
        raise HTTPException(
            status_code=400,
            detail="You can only apply to professors who teach one of your courses.",
        )

    pending_app = await db.scalar(
        select(ThesisApplication)
        .where(
            ThesisApplication.student_id == user.id,
            ThesisApplication.status == ThesisApplicationStatus.pending,
        )
        .order_by(ThesisApplication.applied_at.desc())
        .limit(1)
    )
    if pending_app:
        if pending_app.professor_id == body.professor_id:
            raise HTTPException(status_code=400, detail="You already have a pending application with this professor.")
        raise HTTPException(
            status_code=400,
            detail="Cancel your current pending thesis application before applying to another professor.",
        )

    active_app = await db.scalar(
        select(ThesisApplication)
        .where(
            ThesisApplication.student_id == user.id,
            ThesisApplication.status == ThesisApplicationStatus.active,
        )
        .limit(1)
    )
    if active_app:
        prof = await db.get(User, active_app.professor_id)
        prof_name = f"{prof.first_name} {prof.last_name}" if prof else "your approved professor"
        raise HTTPException(
            status_code=400,
            detail=f"You already have approved thesis supervision with {prof_name}.",
        )

    if not await thesis_service.professor_has_open_thesis_spot(db, body.professor_id):
        raise HTTPException(
            status_code=400,
            detail="This professor has no open thesis supervision spots.",
        )

    app = ThesisApplication(
        student_id=user.id,
        professor_id=body.professor_id,
        topic_description=body.topic_description,
        status=ThesisApplicationStatus.pending,
    )
    db.add(app)
    await db.flush()
    prof = await db.get(User, body.professor_id)
    if prof:
        from backend.services import notification_service

        await notification_service.notify_user(
            db,
            prof.id,
            f"New thesis application from {user.first_name} {user.last_name}.",
            notification_type="thesis",
        )
    await db.commit()
    return {"id": app.id, "status": app.status.value}


@router.post("/thesis/my-application/cancel")
async def thesis_cancel(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    pending = await db.scalar(
        select(ThesisApplication)
        .where(
            ThesisApplication.student_id == user.id,
            ThesisApplication.status == ThesisApplicationStatus.pending,
        )
        .order_by(ThesisApplication.applied_at.desc())
        .limit(1)
    )
    if not pending:
        raise HTTPException(status_code=400, detail="You do not have a pending thesis application to cancel.")

    prof = await db.get(User, pending.professor_id)
    await db.delete(pending)
    if prof:
        from backend.services import notification_service

        await notification_service.notify_user(
            db,
            prof.id,
            f"{user.first_name} {user.last_name} cancelled their pending thesis application.",
            notification_type="thesis",
        )
    await db.commit()
    return {"ok": True}


@router.get("/thesis/my-application")
async def thesis_my(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    row = await db.scalar(
        select(ThesisApplication)
        .where(
            ThesisApplication.student_id == user.id,
            ThesisApplication.status == ThesisApplicationStatus.active,
        )
        .order_by(ThesisApplication.responded_at.desc(), ThesisApplication.applied_at.desc())
        .limit(1)
    )
    if not row:
        row = await db.scalar(
            select(ThesisApplication)
            .where(
                ThesisApplication.student_id == user.id,
                ThesisApplication.status == ThesisApplicationStatus.pending,
            )
            .order_by(ThesisApplication.applied_at.desc())
            .limit(1)
        )
    if not row:
        row = await db.scalar(
            select(ThesisApplication)
            .where(ThesisApplication.student_id == user.id)
            .order_by(ThesisApplication.applied_at.desc())
            .limit(1)
        )
    if not row:
        return None
    prof = await db.get(User, row.professor_id)
    return {
        "id": row.id,
        "professor_id": row.professor_id,
        "professor_name": f"{prof.first_name} {prof.last_name}" if prof else None,
        "status": row.status.value,
        "topic_description": row.topic_description,
        "applied_at": row.applied_at.isoformat(),
    }


@router.get("/thesis/consultation-history")
async def thesis_consultation_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    """Thesis-type bookings with the approved mentor (empty if no active supervision)."""
    return await thesis_service.list_thesis_consultation_history(db, user)


@router.get("/thesis/slots/{professor_id}")
async def thesis_slots(
    professor_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    if user.thesis_professor_id and user.thesis_professor_id != professor_id:
        raise HTTPException(
            status_code=403,
            detail="Thesis consultations are only available with your approved thesis professor.",
        )

    # Check thesis application status — rejected blocks booking
    app = await db.scalar(
        select(ThesisApplication)
        .where(ThesisApplication.student_id == user.id, ThesisApplication.professor_id == professor_id)
        .order_by(ThesisApplication.applied_at.desc())
        .limit(1)
    )
    if app and app.status == ThesisApplicationStatus.rejected:
        raise HTTPException(status_code=403, detail="This professor has declined your thesis supervision.")

    cid = await db.scalar(
        select(CourseStudent.course_id)
        .join(CourseProfessor, CourseProfessor.course_id == CourseStudent.course_id)
        .where(
            CourseStudent.student_id == user.id,
            CourseProfessor.professor_id == professor_id,
        )
        .limit(1)
    )
    if not cid and user.thesis_professor_id != professor_id:
        raise HTTPException(status_code=400, detail="No shared course with professor")
    try:
        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor_id,
            course_id=cid,
            ctype=ConsultationType.thesis,
            group_size=1,
            student_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    return [
        {
            "id": s.id,
            "date": s.session_date.isoformat(),
            "time_from": s.time_from.isoformat(),
            "time_to": s.time_to.isoformat(),
        }
        for s in slots
    ]


@router.get("/preparation-sessions")
async def preparation_sessions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    from datetime import date as date_type
    today = date_type.today()
    enrolled_course_ids = [
        r for r in (await db.scalars(select(CourseStudent.course_id).where(CourseStudent.student_id == user.id))).all()
    ]
    if not enrolled_course_ids:
        return []
    sessions = list(
        (await db.scalars(
            select(ConsultationSession).where(
                ConsultationSession.consultation_type == ConsultationType.preparation,
                ConsultationSession.announced_by_professor == True,  # noqa: E712
                ConsultationSession.course_id.in_(enrolled_course_ids),
                ConsultationSession.session_date >= today,
                ConsultationSession.status != SessionStatus.cancelled,
            ).order_by(ConsultationSession.session_date, ConsultationSession.time_from)
        )).all()
    )
    allowed_event_ids = await exam_service.student_academic_event_ids_for_preparation_panel(db, user.id)
    sessions = [s for s in sessions if s.event_id is None or s.event_id in allowed_event_ids]

    ev_ids = [int(s.event_id) for s in sessions if s.event_id is not None]
    ev_map: dict[int, AcademicEvent] = {}
    if ev_ids:
        ev_rows = (await db.scalars(select(AcademicEvent).where(AcademicEvent.id.in_(ev_ids)))).all()
        ev_map = {e.id: e for e in ev_rows}

    c_ids = list({int(s.course_id) for s in sessions if s.course_id is not None})
    course_map: dict[int, Course] = {}
    if c_ids:
        for c in (await db.scalars(select(Course).where(Course.id.in_(c_ids)))).all():
            course_map[c.id] = c

    prof_ids = list({int(s.professor_id) for s in sessions})
    prof_map: dict[int, User] = {}
    if prof_ids:
        for u in (await db.scalars(select(User).where(User.id.in_(prof_ids)))).all():
            prof_map[u.id] = u

    sid_list = [int(s.id) for s in sessions]
    booked_sids: set[int] = set()
    if sid_list:
        booked_rows = (
            await db.scalars(
                select(Booking.session_id).where(
                    Booking.student_id == user.id,
                    Booking.session_id.in_(sid_list),
                    Booking.status == BookingStatus.active,
                )
            )
        ).all()
        booked_sids = {int(r) for r in booked_rows}

    result: list[dict[str, Any]] = []
    for s in sessions:
        prof = prof_map.get(int(s.professor_id))
        c = course_map.get(int(s.course_id)) if s.course_id is not None else None
        ev = ev_map.get(int(s.event_id)) if s.event_id is not None else None
        result.append(
            {
                "id": s.id,
                "professor_id": s.professor_id,
                "date": s.session_date.isoformat(),
                "time_from": s.time_from.isoformat(),
                "time_to": s.time_to.isoformat(),
                "professor_name": f"{prof.first_name} {prof.last_name}" if prof else "",
                "course_id": s.course_id,
                "course_code": c.code if c else None,
                "course_name": c.name if c else None,
                "academic_event_id": s.event_id,
                "event_type": ev.event_type.value if ev else None,
                "event_name": ev.name if ev else None,
                "event_date": ev.event_date.isoformat() if ev else None,
                "already_booked": int(s.id) in booked_sids,
            }
        )
    return result


class WaitlistJoin(BaseModel):
    session_id: int


class WaitlistDayJoinIn(BaseModel):
    professor_id: int
    course_id: Optional[int] = None
    consultation_type: ConsultationType
    preferred_date: date
    any_slot_on_day: bool = True


@router.post("/waitlist")
async def waitlist_join(
    body: WaitlistJoin,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    try:
        _msg, pos = await waitlist_service.add_session_waitlist(
            db, student_id=user.id, session_id=body.session_id
        )
    except ValueError as e:
        detail = str(e)
        if "not found" in detail.lower():
            raise HTTPException(status_code=404, detail=detail) from e
        raise HTTPException(status_code=400, detail=detail) from e
    await db.commit()
    return {"ok": True, "position": pos}


@router.post("/waitlist/day")
async def waitlist_day_join(
    body: WaitlistDayJoinIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    if body.consultation_type not in (ConsultationType.general, ConsultationType.thesis):
        raise HTTPException(
            status_code=400,
            detail="Day waitlist is only available for general or thesis consultations",
        )
    try:
        _msg, pos = await waitlist_service.add_day_waitlist(
            db,
            student_id=user.id,
            professor_id=body.professor_id,
            course_id=body.course_id,
            consultation_type=body.consultation_type,
            preferred_date=body.preferred_date,
            any_slot_on_day=body.any_slot_on_day,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    await db.commit()
    return {"ok": True, "position": pos}


@router.get("/waitlist/mine")
async def waitlist_mine(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    rows = list((await db.scalars(select(Waitlist).where(Waitlist.student_id == user.id).order_by(Waitlist.created_at))).all())
    result = []
    for w in rows:
        cs = await db.get(ConsultationSession, w.session_id) if w.session_id else None
        prof = await db.get(User, w.professor_id)
        result.append({
            "id": w.id,
            "session_id": w.session_id,
            "kind": "session" if w.session_id else "day",
            "any_slot_on_day": w.any_slot_on_day,
            "professor_name": f"{prof.first_name} {prof.last_name}" if prof else "",
            "preferred_date": w.preferred_date.isoformat(),
            "time_from": cs.time_from.isoformat() if cs else None,
            "time_to": cs.time_to.isoformat() if cs else None,
            "consultation_type": w.consultation_type.value,
            "position": w.position_hint,
        })
    return result


@router.delete("/waitlist/{waitlist_id}")
async def waitlist_leave(
    waitlist_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    res = await db.execute(
        delete(Waitlist).where(Waitlist.id == waitlist_id, Waitlist.student_id == user.id)
    )
    if res.rowcount == 0:
        raise HTTPException(status_code=404)
    await db.commit()
    return {"ok": True}


class VoteBody(BaseModel):
    academic_event_id: int


@router.post("/preparation-votes")
async def preparation_vote(
    body: VoteBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    from backend.db.models import AcademicEvent

    ev = await db.get(AcademicEvent, body.academic_event_id)
    if not ev:
        raise HTTPException(status_code=404)
    existing = await db.scalar(
        select(PreparationVote).where(
            PreparationVote.student_id == user.id,
            PreparationVote.academic_event_id == body.academic_event_id,
        )
    )
    if existing:
        return {"ok": True, "duplicate": True}
    db.add(
        PreparationVote(
            student_id=user.id,
            course_id=ev.course_id,
            academic_event_id=body.academic_event_id,
        )
    )
    await db.commit()
    return {"ok": True}


class AppealBody(BaseModel):
    course_id: int
    message: str = Field(max_length=4000)


@router.post("/appeals")
async def create_appeal(
    body: AppealBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    from backend.db.models import Appeal

    db.add(Appeal(student_id=user.id, course_id=body.course_id, message=body.message))
    admins = list((await db.scalars(select(User).where(User.role == UserRole.admin))).all())
    from backend.services import notification_service

    for a in admins:
        await notification_service.notify_user(
            db,
            a.id,
            f"Waitlist priority appeal from student {user.email}",
            notification_type="appeal",
        )
    await db.commit()
    return {"ok": True}


# --- Exams ---


@router.get("/exams/eligible")
async def student_exams_eligible(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    return await exam_service.list_student_eligible_exams(db, user.id)


@router.get("/exams/registrations")
async def student_exams_registrations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    return await exam_service.list_student_registrations(db, user.id)


class ExamRegisterBody(BaseModel):
    academic_event_id: int


@router.post("/exams/registrations")
async def student_exams_register(
    body: ExamRegisterBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    try:
        reg = await exam_service.register_for_exam(db, user.id, body.academic_event_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"id": reg.id, "status": reg.status.value}


@router.delete("/exams/registrations/{registration_id}")
async def student_exams_cancel_registration(
    registration_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    try:
        await exam_service.cancel_registration(db, user.id, registration_id)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True}


@router.get("/exams/calendar")
async def student_exams_calendar(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
):
    try:
        return await exam_service.list_student_exams_calendar(db, user.id, year=year, month=month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
