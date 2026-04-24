"""Consultation windows, exam periods, and available session slots."""

import logging
import math
from datetime import UTC, date, datetime, timedelta
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
    ExamPeriod,
    ExtraSlot,
    SessionFormat,
    SessionStatus,
    ThesisApplication,
    ThesisApplicationStatus,
    WindowType,
)
from backend.services import config_service

logger = logging.getLogger(__name__)

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


async def is_exam_period(session: AsyncSession, on: date) -> bool:
    rows = (await session.scalars(select(ExamPeriod))).all()
    for ep in rows:
        if ep.date_from <= on <= ep.date_to:
            return True
    return False


def get_available_types(on: date, exam_period: bool) -> list[ConsultationType]:
    """
    Return active consultation types for the given date.
    NOTE: preparation removed from Phase 1 (deferred to Phase 2).
    """
    del on
    types = [ConsultationType.graded_work_review, ConsultationType.thesis]
    if exam_period:
        # During exam period: only review and thesis (preparation disabled for Phase 1)
        pass
    else:
        # Regular period: add general (preparation disabled for Phase 1)
        types.append(ConsultationType.general)
    return types


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
    existing = await session.scalar(
        select(ConsultationSession).where(
            ConsultationSession.professor_id == professor_id,
            ConsultationSession.course_id == course_id,
            ConsultationSession.consultation_type == ctype,
            ConsultationSession.session_date == slot_date,
            ConsultationSession.time_from == time_from,
            ConsultationSession.time_to == time_to,
        )
    )
    if existing:
        return existing

    cap = 1 if ctype == ConsultationType.thesis else capacity
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
        capacity=cap,
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
) -> list[ConsultationSession]:
    if ctype == ConsultationType.thesis:
        active = await session.scalar(
            select(ThesisApplication).where(
                ThesisApplication.student_id == student_id,
                ThesisApplication.professor_id == professor_id,
                ThesisApplication.status == ThesisApplicationStatus.active,
            )
        )
        if not active:
            raise ValueError("No active thesis supervision with this professor — book after your application is accepted")

    today = date.today()
    now_time = datetime.now().time()
    end = today + timedelta(weeks=next_weeks)

    # PREPARATION: only show professor-announced sessions
    if ctype == ConsultationType.preparation:
        in_exam = await is_exam_period(session, today)
        announced = (
            await session.scalars(
                select(ConsultationSession).where(
                    ConsultationSession.professor_id == professor_id,
                    ConsultationSession.course_id == course_id,
                    ConsultationSession.consultation_type == ConsultationType.preparation,
                    ConsultationSession.announced_by_professor == True,  # noqa: E712
                    ConsultationSession.session_date >= today,
                    ConsultationSession.session_date <= end,
                    ConsultationSession.status != SessionStatus.cancelled,
                )
            )
        ).all()
        results = []
        for cs in announced:
            # During exam period, only professor-announced sessions are allowed (already filtered)
            if cs.session_date == today and cs.time_to <= now_time:
                continue
            used = await _used_capacity(session, cs.id)
            if used + group_size <= cs.capacity:
                results.append(cs)
        results.sort(key=lambda s: (s.session_date, s.time_from))
        return results

    # GRADED_WORK_REVIEW: only show professor-announced sessions
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
            used = await _used_capacity(session, cs.id)
            if used + group_size <= cs.capacity:
                results.append(cs)
        results.sort(key=lambda s: (s.session_date, s.time_from))
        return results

    # GENERAL: blocked entirely during exam period
    if ctype == ConsultationType.general:
        if await is_exam_period(session, today):
            return []

    if ctype != ConsultationType.thesis:
        enrolled = await session.scalar(
            select(CourseStudent).where(
                CourseStudent.student_id == student_id,
                CourseStudent.course_id == course_id,
            )
        )
        if not enrolled:
            raise ValueError("Not enrolled in this course")

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

    for d in iter_days(today, end):
        if d in blocked:
            continue
        wd = WEEKDAYS[d.weekday()]
        for w in windows:
            if w.day_of_week.lower() != wd:
                continue
            # Skip past time slots on today
            if d == today and w.time_to <= now_time:
                continue
            cs = await ensure_session_for_window_slot(
                session,
                professor_id=professor_id,
                course_id=course_id,
                ctype=ctype,
                slot_date=d,
                time_from=w.time_from,
                time_to=w.time_to,
                capacity=20,
            )
            used = await _used_capacity(session, cs.id)
            if used + group_size <= cs.capacity:
                if cs not in results:
                    results.append(cs)

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
        if ex.slot_date == today and ex.time_to <= now_time:
            continue
        cs = await ensure_session_for_window_slot(
            session,
            professor_id=professor_id,
            course_id=course_id,
            ctype=ctype,
            slot_date=ex.slot_date,
            time_from=ex.time_from,
            time_to=ex.time_to,
            capacity=20,
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
) -> list[ConsultationSession]:
    """Return announced sessions that are at full capacity (for waitlist offer)."""
    today = date.today()
    end = today + timedelta(weeks=next_weeks)
    announced = (
        await session.scalars(
            select(ConsultationSession).where(
                ConsultationSession.professor_id == professor_id,
                ConsultationSession.course_id == course_id,
                ConsultationSession.consultation_type == ctype,
                ConsultationSession.announced_by_professor == True,  # noqa: E712
                ConsultationSession.session_date >= today,
                ConsultationSession.session_date <= end,
                ConsultationSession.status != SessionStatus.cancelled,
            )
        )
    ).all()
    full = []
    for cs in announced:
        used = await _used_capacity(session, cs.id)
        if used >= cs.capacity:
            full.append(cs)
    return full


def iter_days(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)
