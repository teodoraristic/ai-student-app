"""Consultation windows and available session slots."""

import logging
import math
from datetime import UTC, date, datetime, time, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    BlockedDate,
    Booking,
    BookingStatus,
    ConsultationSession,
    ConsultationType,
    ConsultationWindow,
    CourseStudent,
    ExtraSlot,
    SessionFormat,
    SessionStatus,
    ThesisApplication,
    ThesisApplicationStatus,
    WindowType,
)
from backend.dates import utc_today
from backend.services import config_service
from backend.services.thesis_service import first_shared_course_id

logger = logging.getLogger(__name__)

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

# Thesis consultations are always one-hour blocks (not window-configurable at 15 min).
THESIS_SLOT_DURATION_MINUTES = 60


def get_available_types(on: date) -> list[ConsultationType]:
    """
    Return consultation types offered in booking/chat flows for the given date.

    General consultations are not suppressed during academic exam periods.
    Preparation is deferred (Phase 2).
    """
    del on
    return [
        ConsultationType.graded_work_review,
        ConsultationType.thesis,
        ConsultationType.general,
    ]


async def preparation_vote_threshold_needed(session: AsyncSession, course_id: int) -> int:
    """
    Minimum preparation votes before strong professor nudge.
    Uses preparation_vote_threshold_percent of enrolled students when > 0,
    otherwise auto_schedule_vote_threshold (absolute count).
    """
    pct = await config_service.get_config_int(session, "preparation_vote_threshold_percent", 10)
    enrolled = int(
        await session.scalar(
            select(func.count()).select_from(CourseStudent).where(CourseStudent.course_id == course_id)
        )
        or 0
    )
    if pct > 0 and enrolled > 0:
        return max(1, math.ceil(enrolled * pct / 100))
    return await config_service.get_config_int(session, "auto_schedule_vote_threshold", 5)


def determine_format(attendee_count: int, ctype: ConsultationType) -> SessionFormat:
    if ctype in (ConsultationType.graded_work_review, ConsultationType.thesis):
        return SessionFormat.in_person
    if attendee_count > 15:
        return SessionFormat.online
    return SessionFormat.in_person


def _window_type_for_consultation(ctype: ConsultationType) -> WindowType:
    if ctype == ConsultationType.thesis:
        return WindowType.thesis
    return WindowType.regular


async def _blocked_dates(session: AsyncSession, professor_id: int) -> set[date]:
    rows = (
        await session.scalars(select(BlockedDate).where(BlockedDate.professor_id == professor_id))
    ).all()
    return {r.blocked_date for r in rows}


async def _used_capacity(session: AsyncSession, session_id: int) -> int:
    q = select(func.coalesce(func.sum(Booking.group_size), 0)).where(
        Booking.session_id == session_id,
        Booking.status == BookingStatus.active,
    )
    return int(await session.scalar(q) or 0)


async def ensure_session_for_window_slot(
    session: AsyncSession,
    *,
    professor_id: int,
    course_id: Optional[int],
    ctype: ConsultationType,
    slot_date: date,
    time_from,
    time_to,
    capacity: int = 20,
) -> ConsultationSession:
    """
    Ensure a ConsultationSession exists for the given slot.
    For GENERAL, existing rows may be upgraded to ``general_consultation_slot_capacity`` when below that cap.
    """
    existing = (
        await session.scalars(
            select(ConsultationSession)
            .where(
                ConsultationSession.professor_id == professor_id,
                ConsultationSession.course_id == course_id,
                ConsultationSession.consultation_type == ctype,
                ConsultationSession.session_date == slot_date,
                ConsultationSession.time_from == time_from,
                ConsultationSession.time_to == time_to,
            )
            .order_by(ConsultationSession.id.asc())
            .limit(1)
        )
    ).first()
    if existing:
        if ctype == ConsultationType.general:
            cap = await config_service.get_config_int(
                session, "general_consultation_slot_capacity", 8
            )
            if existing.capacity < cap:
                existing.capacity = cap
                await session.flush()
        return existing

    used = 0
    fmt = determine_format(used + 1, ctype)
    cs = ConsultationSession(
        professor_id=professor_id,
        course_id=course_id,
        consultation_type=ctype,
        session_date=slot_date,
        time_from=time_from,
        time_to=time_to,
        format=fmt,
        status=SessionStatus.confirmed,
        capacity=capacity,
    )
    session.add(cs)
    await session.flush()
    return cs


async def get_free_slots(
    session: AsyncSession,
    *,
    professor_id: int,
    course_id: Optional[int],
    ctype: ConsultationType,
    group_size: int,
    student_id: int,
    next_weeks: int = 3,
    academic_event_id: Optional[int] = None,
) -> list[ConsultationSession]:
    """
    Returns 15-min sub-slots for GENERAL and GRADED_WORK_REVIEW, 60-min sub-slots for THESIS.
    General slots use ``general_consultation_slot_capacity`` from system_config (default 8);
    other types use per-call ``capacity`` (typically 1).
    """
    if ctype == ConsultationType.thesis:
        active = (
            await session.scalars(
                select(ThesisApplication)
                .where(
                    ThesisApplication.student_id == student_id,
                    ThesisApplication.professor_id == professor_id,
                    ThesisApplication.status == ThesisApplicationStatus.active,
                )
                .order_by(ThesisApplication.id.desc())
                .limit(1)
            )
        ).first()
        if not active:
            raise ValueError("No active thesis supervision with this professor — book after your application is accepted")

    # Thesis chat often has no course in context; DB may require course_id NOT NULL (PostgreSQL).
    # Use any course the student shares with this professor so session rows can be created.
    session_course_id = course_id
    if ctype == ConsultationType.thesis and session_course_id is None:
        session_course_id = await first_shared_course_id(session, student_id, professor_id)
        if session_course_id is None:
            raise ValueError(
                "Cannot list thesis slots: you have no enrolled course in common with this professor."
            )

    today = utc_today()
    now_time = datetime.now().time()
    end = today + timedelta(weeks=next_weeks)

    # PREPARATION: only show professor-announced sessions (kept for Phase 2, should not be called in Phase 1)
    if ctype == ConsultationType.preparation:
        prep_conds = [
            ConsultationSession.professor_id == professor_id,
            ConsultationSession.course_id == course_id,
            ConsultationSession.consultation_type == ConsultationType.preparation,
            ConsultationSession.announced_by_professor == True,  # noqa: E712
            ConsultationSession.session_date >= today,
            ConsultationSession.session_date <= end,
            ConsultationSession.status != SessionStatus.cancelled,
        ]
        if academic_event_id is not None:
            if academic_event_id == 0:
                prep_conds.append(ConsultationSession.event_id.is_(None))
            else:
                prep_conds.append(ConsultationSession.event_id == academic_event_id)
        announced = (
            await session.scalars(
                select(ConsultationSession).where(*prep_conds)
            )
        ).all()
        results = []
        for cs in announced:
            if cs.session_date == today and cs.time_to <= now_time:
                continue
            used = await _used_capacity(session, cs.id)
            if used + group_size <= cs.capacity:
                results.append(cs)
        results.sort(key=lambda s: (s.session_date, s.time_from))
        return results

    # GRADED_WORK_REVIEW: professor-announced sessions split into 15-min sub-slots
    if ctype == ConsultationType.graded_work_review:
        announced = (
            await session.scalars(
                select(ConsultationSession).where(
                    ConsultationSession.professor_id == professor_id,
                    ConsultationSession.course_id == course_id,
                    ConsultationSession.consultation_type == ConsultationType.graded_work_review,
                    ConsultationSession.announced_by_professor == True,  # noqa: E712
                    ConsultationSession.session_date >= today,
                    ConsultationSession.session_date <= end,
                    ConsultationSession.status != SessionStatus.cancelled,
                )
            )
        ).all()
        results = []
        for cs in announced:
            if cs.session_date == today and cs.time_to <= now_time:
                continue
            # Generate 15-min sub-slots from announced session
            sub_slots = generate_sub_slots(cs.time_from, cs.time_to, 15)
            for sub_from, sub_to in sub_slots:
                # Skip past sub-slots on today
                if cs.session_date == today and sub_to <= now_time:
                    continue
                sub_session = await ensure_session_for_window_slot(
                    session,
                    professor_id=professor_id,
                    course_id=course_id,
                    ctype=ctype,
                    slot_date=cs.session_date,
                    time_from=sub_from,
                    time_to=sub_to,
                    capacity=1,
                )
                used = await _used_capacity(session, sub_session.id)
                if used + group_size <= sub_session.capacity:
                    results.append(sub_session)
        results.sort(key=lambda s: (s.session_date, s.time_from))
        return results

    # Enrollment check for non-thesis types
    if ctype != ConsultationType.thesis:
        enrolled = (
            await session.scalars(
                select(CourseStudent)
                .where(
                    CourseStudent.student_id == student_id,
                    CourseStudent.course_id == course_id,
                )
                .limit(1)
            )
        ).first()
        if not enrolled:
            raise ValueError("Not enrolled in this course")

    # GENERAL and THESIS: derive sub-slots from weekly windows + extra slots
    wtype = _window_type_for_consultation(ctype)
    windows = (
        await session.scalars(
            select(ConsultationWindow).where(
                ConsultationWindow.professor_id == professor_id,
                ConsultationWindow.window_type == wtype,
                ConsultationWindow.is_active.is_(True),
            )
        )
    ).all()

    blocked = await _blocked_dates(session, professor_id)
    results: list[ConsultationSession] = []
    general_capacity: Optional[int] = None
    if ctype == ConsultationType.general:
        general_capacity = await config_service.get_config_int(
            session, "general_consultation_slot_capacity", 8
        )

    for d in iter_days(today, end):
        if d in blocked:
            continue
        wd = WEEKDAYS[d.weekday()]
        for w in windows:
            if w.day_of_week.lower() != wd:
                continue
            slot_mins = (
                THESIS_SLOT_DURATION_MINUTES
                if ctype == ConsultationType.thesis
                else w.slot_duration_minutes
            )
            sub_slots = generate_sub_slots(w.time_from, w.time_to, slot_mins)
            for sub_from, sub_to in sub_slots:
                # Skip past sub-slots on today
                if d == today and sub_to <= now_time:
                    continue
                cs = await ensure_session_for_window_slot(
                    session,
                    professor_id=professor_id,
                    course_id=session_course_id,
                    ctype=ctype,
                    slot_date=d,
                    time_from=sub_from,
                    time_to=sub_to,
                    capacity=general_capacity if general_capacity is not None else 1,
                )
                used = await _used_capacity(session, cs.id)
                if used + group_size <= cs.capacity:
                    if cs not in results:
                        results.append(cs)

    # Extra slots: also split into sub-slots
    extras = (
        await session.scalars(
            select(ExtraSlot).where(
                ExtraSlot.professor_id == professor_id,
                ExtraSlot.slot_type == wtype,
                ExtraSlot.slot_date >= today,
                ExtraSlot.slot_date <= end,
            )
        )
    ).all()
    for ex in extras:
        if ex.slot_date in blocked:
            continue
        slot_mins = (
            THESIS_SLOT_DURATION_MINUTES
            if ctype == ConsultationType.thesis
            else ex.slot_duration_minutes
        )
        sub_slots = generate_sub_slots(ex.time_from, ex.time_to, slot_mins)
        for sub_from, sub_to in sub_slots:
            if ex.slot_date == today and sub_to <= now_time:
                continue
            cs = await ensure_session_for_window_slot(
                session,
                professor_id=professor_id,
                course_id=session_course_id,
                ctype=ctype,
                slot_date=ex.slot_date,
                time_from=sub_from,
                time_to=sub_to,
                capacity=general_capacity if general_capacity is not None else 1,
            )
            used = await _used_capacity(session, cs.id)
            if used + group_size <= cs.capacity and cs not in results:
                results.append(cs)

    results.sort(key=lambda s: (s.session_date, s.time_from))
    return results


async def get_full_sessions(
    session: AsyncSession,
    *,
    professor_id: int,
    course_id: Optional[int],
    ctype: ConsultationType,
    next_weeks: int = 3,
    on_date: Optional[date] = None,
    student_id: Optional[int] = None,
) -> list[ConsultationSession]:
    """
    Return consultation sessions at full capacity (for waitlist offers).

    GENERAL and THESIS include window-derived sessions (``announced_by_professor`` not required).
    GRADED_WORK_REVIEW and PREPARATION only include professor-announced sessions.
    When ``course_id`` is None and ``ctype`` is THESIS, ``student_id`` is used to resolve a shared course.
    """
    today = utc_today()
    end = today + timedelta(weeks=next_weeks)
    session_course_id = course_id
    if ctype == ConsultationType.thesis and session_course_id is None and student_id is not None:
        session_course_id = await first_shared_course_id(session, student_id, professor_id)

    stmt = select(ConsultationSession).where(
        ConsultationSession.professor_id == professor_id,
        ConsultationSession.consultation_type == ctype,
        ConsultationSession.session_date >= today,
        ConsultationSession.session_date <= end,
        ConsultationSession.status != SessionStatus.cancelled,
    )
    if ctype in (ConsultationType.graded_work_review, ConsultationType.preparation):
        stmt = stmt.where(ConsultationSession.announced_by_professor.is_(True))
    if session_course_id is not None:
        stmt = stmt.where(ConsultationSession.course_id == session_course_id)
    else:
        stmt = stmt.where(ConsultationSession.course_id.is_(None))
    if on_date is not None:
        stmt = stmt.where(ConsultationSession.session_date == on_date)

    rows = list((await session.scalars(stmt)).all())
    full: list[ConsultationSession] = []
    for cs in rows:
        used = await _used_capacity(session, cs.id)
        if used >= cs.capacity:
            full.append(cs)
    full.sort(key=lambda s: (s.session_date, s.time_from, s.time_to, s.id))
    return full


async def iter_dates_for_professor_availability(
    session: AsyncSession,
    *,
    professor_id: int,
    course_id: Optional[int],
    ctype: ConsultationType,
    student_id: int,
    next_weeks: int = 3,
    max_dates: int = 12,
) -> list[date]:
    """
    Upcoming calendar dates (within ``next_weeks``) where the professor has an active weekly window
    and the day is not blocked. Used for day-level waitlist chips when no bookable slots exist.
    """
    _ = course_id  # reserved for future per-course window filtering
    today = utc_today()
    end = today + timedelta(weeks=next_weeks)
    wtype = _window_type_for_consultation(ctype)
    windows = list(
        (
            await session.scalars(
                select(ConsultationWindow).where(
                    ConsultationWindow.professor_id == professor_id,
                    ConsultationWindow.window_type == wtype,
                    ConsultationWindow.is_active.is_(True),
                )
            )
        ).all()
    )
    if not windows:
        return []
    blocked = await _blocked_dates(session, professor_id)
    out: list[date] = []
    seen: set[date] = set()
    for d in iter_days(today, end):
        if d in blocked:
            continue
        wd = WEEKDAYS[d.weekday()]
        if not any(w.day_of_week.lower() == wd for w in windows):
            continue
        if d not in seen:
            seen.add(d)
            out.append(d)
        if len(out) >= max_dates:
            break
    return out


def iter_days(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def generate_sub_slots(
    time_from: time, time_to: time, duration_minutes: int
) -> list[tuple[time, time]]:
    """
    Generate sub-slots of given duration between time_from and time_to.
    Returns list of (start_time, end_time) tuples.
    """
    anchor = date(2000, 1, 1)
    start_dt = datetime.combine(anchor, time_from)
    end_dt = datetime.combine(anchor, time_to)
    slots = []
    
    current = start_dt
    while current < end_dt:
        slot_end = current + timedelta(minutes=duration_minutes)
        if slot_end > end_dt:
            break
        slots.append((current.time(), slot_end.time()))
        current = slot_end
    
    return slots
