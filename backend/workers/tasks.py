"""APScheduler task implementations — each run logs to scheduler_logs."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import async_session_maker
from sqlalchemy import func

from backend.db.models import (
    AcademicEvent,
    Booking,
    BookingStatus,
    ConsultationSession,
    ConsultationType,
    CourseProfessor,
    CourseStudent,
    PreparationVote,
    SchedulerLog,
    SchedulerLogStatus,
    SchedulingRequest,
    SchedulingRequestStatus,
    SessionStatus,
    User,
    UserRole,
    Waitlist,
)
from backend.dates import utc_today
from backend.services import booking_service, config_service, notification_service, slot_service

logger = logging.getLogger(__name__)


async def _log(session: AsyncSession, task_name: str, status: SchedulerLogStatus, detail: str | None) -> None:
    session.add(SchedulerLog(task_name=task_name, status=status, detail=detail))
    await session.flush()


async def run_task_by_name(session: AsyncSession, task_name: str) -> None:
    """Invoke a named task (used by APScheduler and admin manual trigger)."""
    try:
        if task_name == "reminder_check":
            await reminder_check(session)
        elif task_name == "daily_check":
            await daily_check(session)
        elif task_name == "waitlist_check":
            await waitlist_check(session)
        elif task_name == "feedback_check":
            await feedback_check(session)
        elif task_name == "penalty_check":
            await penalty_check(session)
        else:
            await _log(session, task_name, SchedulerLogStatus.error, "Unknown task")
            return
        await _log(session, task_name, SchedulerLogStatus.ok, None)
    except Exception as e:
        logger.exception("scheduler task %s", task_name)
        await _log(session, task_name, SchedulerLogStatus.error, str(e)[:2000])


async def reminder_check(session: AsyncSession) -> None:
    tomorrow = utc_today() + timedelta(days=1)
    sessions = list(
        (await session.scalars(select(ConsultationSession).where(ConsultationSession.session_date == tomorrow))).all()
    )
    for cs in sessions:
        bookings = list(
            (
                await session.scalars(
                    select(Booking).where(Booking.session_id == cs.id, Booking.status == BookingStatus.active)
                )
            ).all()
        )
        for b in bookings:
            await notification_service.notify_user(
                session,
                b.student_id,
                f"Reminder: consultation tomorrow at {cs.time_from}",
                notification_type="reminder",
            )
        prof = await session.get(User, cs.professor_id)
        if prof:
            await notification_service.notify_user(
                session,
                prof.id,
                f"Reminder: {len(bookings)} booking(s) tomorrow at {cs.time_from}",
                notification_type="reminder",
            )


async def daily_check(session: AsyncSession) -> None:
    today = utc_today()
    days = await config_service.get_config_int(session, "days_before_exam_trigger", 7)
    target = today + timedelta(days=days)

    # Find events within the trigger window
    events = list(
        (
            await session.scalars(
                select(AcademicEvent).where(
                    AcademicEvent.event_date >= today,
                    AcademicEvent.event_date <= target,
                )
            )
        ).all()
    )

    for ev in events:
        vote_count = int(
            await session.scalar(
                select(func.count()).select_from(PreparationVote).where(
                    PreparationVote.academic_event_id == ev.id
                )
            ) or 0
        )
        if vote_count == 0:
            continue

        # Find professors for this course
        profs = list(
            (
                await session.scalars(
                    select(CourseProfessor).where(CourseProfessor.course_id == ev.course_id)
                )
            ).all()
        )
        threshold = await slot_service.preparation_vote_threshold_needed(session, ev.course_id)
        for cp in profs:
            sr = await session.scalar(
                select(SchedulingRequest).where(
                    SchedulingRequest.professor_id == cp.professor_id,
                    SchedulingRequest.course_id == ev.course_id,
                    SchedulingRequest.academic_event_id == ev.id,
                    SchedulingRequest.status == SchedulingRequestStatus.pending,
                )
            )
            if not sr:
                deadline = datetime.combine(ev.event_date, datetime.min.time()).replace(tzinfo=UTC) - timedelta(hours=48)
                sr = SchedulingRequest(
                    professor_id=cp.professor_id,
                    course_id=ev.course_id,
                    academic_event_id=ev.id,
                    vote_count=vote_count,
                    status=SchedulingRequestStatus.pending,
                    deadline_at=deadline,
                )
                session.add(sr)
            else:
                sr.vote_count = vote_count
            await session.flush()

            if vote_count >= threshold:
                await notification_service.notify_user(
                    session,
                    cp.professor_id,
                    f"{vote_count} students requested a preparation session for '{ev.name}' ({ev.event_date}). "
                    "Please schedule one before the deadline.",
                    notification_type="scheduling_request",
                )

    # Expire overdue scheduling requests and notify students
    now = datetime.now(UTC)
    overdue = list(
        (
            await session.scalars(
                select(SchedulingRequest).where(
                    SchedulingRequest.status == SchedulingRequestStatus.pending,
                    SchedulingRequest.deadline_at <= now,
                )
            )
        ).all()
    )
    for sr in overdue:
        sr.status = SchedulingRequestStatus.expired
        # Notify students who voted
        voters = list(
            (
                await session.scalars(
                    select(PreparationVote).where(
                        PreparationVote.academic_event_id == sr.academic_event_id
                    )
                )
            ).all()
        )
        for v in voters:
            await notification_service.notify_user(
                session,
                v.student_id,
                "The preparation session you requested was not confirmed in time.",
                notification_type="scheduler",
            )
    await session.flush()


async def waitlist_check(session: AsyncSession) -> None:
    """Remove stale waitlist rows; promote students when seats open (same rules as cancellation)."""
    today = utc_today()
    stale = list(
        (
            await session.scalars(
                select(Waitlist).where(Waitlist.session_id.isnot(None), Waitlist.notified.is_(False))  # noqa: E712
            )
        ).all()
    )
    for wl in stale:
        cs = await session.get(ConsultationSession, wl.session_id)  # type: ignore[arg-type]
        if not cs or cs.session_date < today or cs.status == SessionStatus.cancelled:
            sid = wl.student_id
            await session.delete(wl)
            await session.flush()
            await notification_service.notify_user(
                session,
                sid,
                "You were removed from a consultation waitlist because the session ended or was cancelled.",
                notification_type="waitlist",
            )
            continue
        await booking_service.drain_waitlist_for_session(session, cs.id, cs)
    await session.flush()

    past_day = list(
        (
            await session.scalars(
                select(Waitlist).where(Waitlist.session_id.is_(None), Waitlist.preferred_date < today)
            )
        ).all()
    )
    for wl in past_day:
        sid = wl.student_id
        await session.delete(wl)
        await session.flush()
        await notification_service.notify_user(
            session,
            sid,
            "Your day-based consultation waitlist entry expired because the date has passed.",
            notification_type="waitlist",
        )
    await session.flush()

    active_day = list(
        (
            await session.scalars(
                select(Waitlist).where(
                    Waitlist.session_id.is_(None),
                    Waitlist.notified.is_(False),
                    Waitlist.preferred_date >= today,
                )
            )
        ).all()
    )
    for wl in active_day:
        try:
            freed = await slot_service.get_free_slots(
                session,
                professor_id=wl.professor_id,
                course_id=wl.course_id,
                ctype=wl.consultation_type,
                group_size=1,
                student_id=wl.student_id,
                next_weeks=5,
            )
        except ValueError:
            continue
        if not any(s.session_date == wl.preferred_date for s in freed):
            continue
        await notification_service.notify_user(
            session,
            wl.student_id,
            f"A booking slot opened on {wl.preferred_date.isoformat()} with your professor. "
            "Open the booking chat or My Bookings to reserve it.",
            notification_type="waitlist",
            link="/student/chat",
        )
        await session.delete(wl)
        await session.flush()


async def feedback_check(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    sessions = list((await session.scalars(select(ConsultationSession))).all())
    for cs in sessions[:50]:
        end = datetime.combine(cs.session_date, cs.time_to, tzinfo=UTC)
        if timedelta(hours=2) <= now - end < timedelta(hours=3):
            for b in (
                await session.scalars(
                    select(Booking).where(Booking.session_id == cs.id, Booking.status == BookingStatus.attended)
                )
            ).all():
                await notification_service.notify_user(
                    session,
                    b.student_id,
                    "Please leave feedback for your recent consultation.",
                    notification_type="feedback",
                )


async def penalty_check(session: AsyncSession) -> None:
    logger.info("penalty_check ran")
