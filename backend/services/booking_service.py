"""Student bookings and cancellations."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    Booking,
    BookingPriority,
    BookingStatus,
    ConsultationSession,
    ConsultationType,
    ThesisApplication,
    ThesisApplicationStatus,
    User,
    UserRole,
    Waitlist,
)
from backend.services import config_service, notification_service, slot_service

logger = logging.getLogger(__name__)


async def create_booking(
    session: AsyncSession,
    *,
    student: User,
    session_id: int,
    task: str | None,
    anonymous_question: str | None,
    is_urgent: bool,
    group_size: int,
) -> Booking:
    cs = await session.get(ConsultationSession, session_id)
    if not cs:
        raise ValueError("Session not found")

    if cs.consultation_type == ConsultationType.graded_work_review and group_size > 1:
        raise ValueError("Graded work review is 1-on-1 only")

    if cs.consultation_type == ConsultationType.thesis:
        thesis_ok = await session.scalar(
            select(ThesisApplication).where(
                ThesisApplication.student_id == student.id,
                ThesisApplication.professor_id == cs.professor_id,
                ThesisApplication.status == ThesisApplicationStatus.active,
            )
        )
        if not thesis_ok:
            raise ValueError("Thesis bookings require approved supervision with this professor")

    existing = await session.scalar(
        select(Booking).where(
            Booking.student_id == student.id,
            Booking.session_id == session_id,
            Booking.status == BookingStatus.active,
        )
    )
    if existing:
        raise ValueError("Already booked this session")

    used = await slot_service._used_capacity(session, session_id)
    if used + group_size > cs.capacity:
        raise ValueError("Session is full")

    booking = Booking(
        student_id=student.id,
        session_id=session_id,
        task=task,
        anonymous_question=anonymous_question,
        is_urgent=is_urgent,
        group_size=group_size,
        status=BookingStatus.active,
        priority=BookingPriority.normal,
    )
    session.add(booking)
    await session.flush()

    prof = await session.get(User, cs.professor_id)
    if prof:
        await notification_service.notify_user(
            session,
            prof.id,
            f"New booking for session on {cs.session_date} ({cs.consultation_type.value}).",
            notification_type="booking",
        )
    if is_urgent and prof:
        await notification_service.notify_user(
            session,
            prof.id,
            f"Urgent student question (anonymous): {anonymous_question or '—'}",
            notification_type="urgent",
        )
    return booking


async def cancel_booking(
    session: AsyncSession,
    *,
    student: User,
    booking_id: int,
    reason: str | None = None,
) -> Booking:
    b = await session.get(Booking, booking_id)
    if not b or b.student_id != student.id:
        raise ValueError("Booking not found")
    if b.status != BookingStatus.active:
        raise ValueError("Booking cannot be cancelled")

    cs = await session.get(ConsultationSession, b.session_id)
    window_hours = await config_service.get_config_int(
        session, "no_notice_cancel_window_hours", 1
    )
    if cs:
        start_dt = datetime.combine(cs.session_date, cs.time_from, tzinfo=UTC)
        if datetime.now(UTC) > start_dt - timedelta(hours=window_hours):
            limit = await config_service.get_config_int(session, "penalty_cancellations_limit", 2)
            # Count recent no-notice cancellations (simplified: mark priority low if over limit)
            b.priority = BookingPriority.low

    b.status = BookingStatus.cancelled
    b.cancelled_at = datetime.now(UTC)
    b.cancellation_reason = reason
    await session.flush()

    if cs and cs.consultation_type != ConsultationType.thesis:
        await drain_waitlist_for_session(session, b.session_id, cs)

    return b


async def try_promote_one_waitlist_entry(
    session: AsyncSession, session_id: int, cs: ConsultationSession
) -> bool:
    """Promote the next waitlisted student if within the cutoff window and capacity allows."""
    start_dt = datetime.combine(cs.session_date, cs.time_from, tzinfo=UTC)
    cutoff = await config_service.get_config_int(session, "waitlist_cutoff_hours", 2)
    if datetime.now(UTC) >= start_dt - timedelta(hours=cutoff):
        return False
    used = await slot_service._used_capacity(session, session_id)
    if used >= cs.capacity:
        return False
    first = await session.scalar(
        select(Waitlist)
        .where(Waitlist.session_id == session_id, Waitlist.notified == False)  # noqa: E712
        .order_by(Waitlist.position_hint, Waitlist.created_at)
        .limit(1)
    )
    if not first:
        return False
    booking = Booking(
        student_id=first.student_id,
        session_id=session_id,
        status=BookingStatus.active,
        priority=BookingPriority.normal,
        group_size=1,
    )
    session.add(booking)
    await session.delete(first)
    await session.flush()
    await notification_service.notify_user(
        session,
        first.student_id,
        f"A spot opened up! You've been automatically booked for {cs.session_date} at {cs.time_from}.",
        notification_type="waitlist",
    )
    return True


async def drain_waitlist_for_session(
    session: AsyncSession, session_id: int, cs: ConsultationSession
) -> int:
    """Fill empty seats from the waitlist in order. Returns how many students were promoted."""
    n = 0
    while await try_promote_one_waitlist_entry(session, session_id, cs):
        n += 1
    return n


async def flag_urgent(session: AsyncSession, student: User, booking_id: int) -> Booking:
    b = await session.get(Booking, booking_id)
    if not b or b.student_id != student.id:
        raise ValueError("Booking not found")
    b.is_urgent = True
    await session.flush()
    cs = await session.get(ConsultationSession, b.session_id)
    if cs:
        prof = await session.get(User, cs.professor_id)
        if prof:
            await notification_service.notify_user(
                session,
                prof.id,
                "A student flagged their booking as urgent.",
                notification_type="urgent",
            )
    return b
