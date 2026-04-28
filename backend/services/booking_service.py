"""Student bookings and cancellations."""

import logging
from calendar import monthrange
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    AcademicEvent,
    Booking,
    BookingPriority,
    BookingStatus,
    ConsultationSession,
    ConsultationType,
    Course,
    ProfessorProfile,
    SessionStatus,
    ThesisApplication,
    ThesisApplicationStatus,
    User,
    UserRole,
    Waitlist,
)
from backend.dates import utc_today
from backend.services import config_service, notification_service, slot_service

logger = logging.getLogger(__name__)


async def active_attendee_headcount(sess: AsyncSession, session_id: int) -> int:
    """Seats taken: sum of ``group_size`` for active bookings on this session."""
    return await slot_service._used_capacity(sess, session_id)


async def general_group_session_counts(
    session: AsyncSession, cs: ConsultationSession | None
) -> tuple[int | None, int | None]:
    """For multi-seat general sessions, return (active attendee seats, max capacity); else (None, None)."""
    if cs is None or cs.consultation_type != ConsultationType.general or cs.capacity <= 1:
        return (None, None)
    n = await active_attendee_headcount(session, cs.id)
    return (n, cs.capacity)


async def _notify_peers_group_session_grew(
    session: AsyncSession,
    *,
    cs: ConsultationSession,
    new_student_id: int,
    new_group_size: int,
) -> None:
    """
    When another student joins a multi-seat general session, notify everyone
    who was already booked so they can cancel and pick another slot if they prefer.
    """
    if cs.consultation_type != ConsultationType.general or cs.capacity <= 1:
        return
    peers = list(
        (
            await session.scalars(
                select(Booking).where(
                    Booking.session_id == cs.id,
                    Booking.status == BookingStatus.active,
                    Booking.student_id != new_student_id,
                )
            )
        ).all()
    )
    if not peers:
        return
    date_s = cs.session_date.isoformat()
    tf = cs.time_from.strftime("%H:%M")
    tt = cs.time_to.strftime("%H:%M")
    if new_group_size <= 1:
        lead = "One more person will attend this group consultation"
    else:
        lead = f"A new booking added {new_group_size} people to this group consultation"
    text = (
        f"{lead} on {date_s} ({tf}–{tt}). "
        "If you would rather meet with fewer people or at another time, you can cancel this booking "
        "from My Bookings or the booking assistant and choose a different slot."
    )
    for peer in peers:
        await notification_service.notify_user(
            session,
            peer.student_id,
            text,
            notification_type="group_session",
            link="/student/bookings",
        )


async def create_booking(
    session: AsyncSession,
    *,
    student: User,
    session_id: int,
    task: str | None,
    anonymous_question: str | None,
    group_size: int,
) -> Booking:
    cs = (
        await session.scalars(
            select(ConsultationSession).where(ConsultationSession.id == session_id).with_for_update()
        )
    ).first()
    if not cs:
        raise ValueError("Session not found")

    if cs.consultation_type == ConsultationType.graded_work_review and group_size > 1:
        raise ValueError("Graded work review is 1-on-1 only")

    if cs.consultation_type == ConsultationType.thesis:
        thesis_ok = (
            await session.scalars(
                select(ThesisApplication)
                .where(
                    ThesisApplication.student_id == student.id,
                    ThesisApplication.professor_id == cs.professor_id,
                    ThesisApplication.status == ThesisApplicationStatus.active,
                )
                .order_by(ThesisApplication.id.desc())
                .limit(1)
            )
        ).first()
        if not thesis_ok:
            raise ValueError("Thesis bookings require approved supervision with this professor")

    existing = (
        await session.scalars(
            select(Booking)
            .where(
                Booking.student_id == student.id,
                Booking.session_id == session_id,
                Booking.status == BookingStatus.active,
            )
            .limit(1)
        )
    ).first()
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
        group_size=group_size,
        status=BookingStatus.active,
        priority=BookingPriority.normal,
    )
    try:
        async with session.begin_nested():
            session.add(booking)
            await session.flush()
    except IntegrityError as e:
        logger.info("Booking insert conflict session=%s student=%s: %s", session_id, student.id, e)
        raise ValueError("Already booked this session") from None

    await _notify_peers_group_session_grew(
        session,
        cs=cs,
        new_student_id=student.id,
        new_group_size=group_size,
    )

    prof = await session.get(User, cs.professor_id)
    if prof:
        await notification_service.notify_user(
            session,
            prof.id,
            f"New booking for session on {cs.session_date} ({cs.consultation_type.value}).",
            notification_type="booking",
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

    if cs:
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
    first = (
        (
            await session.scalars(
                select(Waitlist)
                .where(Waitlist.session_id == session_id, Waitlist.notified.is_(False))
                .order_by(Waitlist.position_hint, Waitlist.created_at)
                .limit(1)
            )
        )
    ).first()
    if not first:
        return False
    stu = await session.get(User, first.student_id)
    if not stu:
        await session.delete(first)
        await session.flush()
        return False
    try:
        await create_booking(
            session,
            student=stu,
            session_id=session_id,
            task=None,
            anonymous_question=None,
            group_size=1,
        )
    except ValueError:
        logger.info("Waitlist promotion skipped for session %s", session_id)
        return False
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


async def list_calendar_bookings(
    session: AsyncSession,
    user: User,
    *,
    year: int,
    month: int,
) -> list[dict[str, Any]]:
    """Bookings whose session falls in the given calendar month (student or professor); cancelled omitted."""
    if not (1 <= month <= 12):
        raise ValueError("Invalid month")
    if not (2000 <= year <= 2100):
        raise ValueError("Invalid year")
    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])

    if user.role == UserRole.student:
        stmt = (
            select(Booking, ConsultationSession)
            .join(ConsultationSession, ConsultationSession.id == Booking.session_id)
            .where(
                Booking.student_id == user.id,
                Booking.status != BookingStatus.cancelled,
                ConsultationSession.session_date >= first,
                ConsultationSession.session_date <= last,
            )
            .order_by(ConsultationSession.session_date, ConsultationSession.time_from)
        )
    elif user.role == UserRole.professor:
        stmt = (
            select(Booking, ConsultationSession)
            .join(ConsultationSession, ConsultationSession.id == Booking.session_id)
            .where(
                ConsultationSession.professor_id == user.id,
                Booking.status != BookingStatus.cancelled,
                ConsultationSession.session_date >= first,
                ConsultationSession.session_date <= last,
            )
            .order_by(ConsultationSession.session_date, ConsultationSession.time_from)
        )
    else:
        raise ValueError("Calendar is only available for students and professors")

    pairs = list((await session.execute(stmt)).all())
    out: list[dict[str, Any]] = []
    for b, cs in pairs:
        prof = await session.get(User, cs.professor_id)
        course = await session.get(Course, cs.course_id) if cs.course_id else None
        profile = (
            await session.scalar(select(ProfessorProfile).where(ProfessorProfile.user_id == prof.id))
            if prof
            else None
        )
        hall = ""
        if profile:
            hall = (profile.hall or "").strip() or (profile.default_room or "").strip()

        student_name: str | None = None
        if user.role == UserRole.professor:
            show_student = cs.consultation_type in (
                ConsultationType.graded_work_review,
                ConsultationType.thesis,
            )
            stu = await session.get(User, b.student_id)
            if stu and show_student:
                student_name = f"{stu.first_name} {stu.last_name}"

        out.append(
            {
                "id": b.id,
                "session_id": b.session_id,
                "status": b.status.value,
                "session_date": cs.session_date.isoformat(),
                "time_from": cs.time_from.strftime("%H:%M"),
                "time_to": cs.time_to.strftime("%H:%M"),
                "consultation_type": cs.consultation_type.value,
                "professor_name": f"{prof.first_name} {prof.last_name}" if prof else None,
                "student_name": student_name,
                "course_code": course.code if course else None,
                "course_name": course.name if course else None,
                "hall": hall or None,
                "task": b.task,
            }
        )
    return out


_MERGEABLE_CONSULTATION_TYPES = frozenset({"PREPARATION", "GRADED_WORK_REVIEW"})


def merge_professor_slot_cards_for_same_timeslot(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Professor exam notices create one ConsultationSession per academic event even when date/time/course match.
    Merge those into a single card so bookings and headcounts appear once per physical slot.
    """
    if len(rows) < 2:
        return rows

    def group_key(r: dict[str, Any]) -> tuple[Any, ...]:
        ct = str(r.get("consultation_type") or "")
        if ct not in _MERGEABLE_CONSULTATION_TYPES:
            return ("__singleton__", int(r["session_id"]))
        return (
            ct,
            str(r.get("session_date") or ""),
            str(r.get("time_from") or ""),
            str(r.get("time_to") or ""),
            str(r.get("course_code") or ""),
            str(r.get("course_name") or ""),
        )

    buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    order_keys: list[tuple[Any, ...]] = []
    seen_k: set[tuple[Any, ...]] = set()
    for r in rows:
        k = group_key(r)
        buckets[k].append(r)
        if k not in seen_k:
            seen_k.add(k)
            order_keys.append(k)

    merged: list[dict[str, Any]] = []
    for k in order_keys:
        group = buckets[k]
        if len(group) == 1:
            merged.append(group[0])
            continue
        base = dict(group[0])
        seen_booking: set[int] = set()
        all_bookings: list[dict[str, Any]] = []
        for r in group:
            for b in r.get("bookings") or []:
                bid = int(b["id"])
                if bid not in seen_booking:
                    seen_booking.add(bid)
                    all_bookings.append(b)
        total_party = sum(
            max(1, int(b.get("group_size") or 1))
            for b in all_bookings
            if b.get("status") != BookingStatus.cancelled.value
        )
        base["session_id"] = min(int(r["session_id"]) for r in group)
        base["bookings"] = all_bookings
        base["session_party_total"] = total_party
        base["session_booking_count"] = len(all_bookings)
        merged.append(base)
    return merged


async def list_professor_announced_preparation_overview(
    session: AsyncSession, professor_id: int
) -> list[dict[str, Any]]:
    """Upcoming professor-announced preparation sessions, merged by course + date + time."""
    today = utc_today()
    sessions = list(
        (
            await session.scalars(
                select(ConsultationSession).where(
                    ConsultationSession.professor_id == professor_id,
                    ConsultationSession.consultation_type == ConsultationType.preparation,
                    ConsultationSession.announced_by_professor.is_(True),
                    ConsultationSession.session_date >= today,
                    ConsultationSession.status != SessionStatus.cancelled,
                ).order_by(
                    ConsultationSession.session_date,
                    ConsultationSession.time_from,
                    ConsultationSession.id,
                )
            )
        ).all()
    )
    if not sessions:
        return []

    by_slot: dict[tuple[int | None, date, Any, Any], list[ConsultationSession]] = defaultdict(list)
    for cs in sessions:
        key = (cs.course_id, cs.session_date, cs.time_from, cs.time_to)
        by_slot[key].append(cs)

    course_ids = {int(cs.course_id) for cs in sessions if cs.course_id is not None}
    course_by_id: dict[int, Course] = {}
    for cid in course_ids:
        c = await session.get(Course, cid)
        if c:
            course_by_id[cid] = c

    out: list[dict[str, Any]] = []
    for (_cid, slot_date, tf, tt), group in sorted(
        by_slot.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][3])
    ):
        sids = [cs.id for cs in group]
        event_ids = sorted({int(cs.event_id) for cs in group if cs.event_id is not None})
        exams_meta: list[dict[str, Any]] = []
        for eid in event_ids:
            ev = await session.get(AcademicEvent, eid)
            if ev:
                exams_meta.append(
                    {
                        "academic_event_id": ev.id,
                        "event_name": ev.name,
                        "event_type": ev.event_type.value,
                        "event_date": ev.event_date.isoformat(),
                    }
                )

        bookings = list(
            (
                await session.scalars(select(Booking).where(Booking.session_id.in_(tuple(sids))))
            ).all()
        )
        active_party = sum(
            max(1, int(b.group_size or 1))
            for b in bookings
            if b.status != BookingStatus.cancelled
        )
        active_bookings = sum(1 for b in bookings if b.status != BookingStatus.cancelled)

        cid = group[0].course_id
        c = course_by_id.get(int(cid)) if cid is not None else None
        out.append(
            {
                "course_id": int(cid) if cid is not None else None,
                "course_code": c.code if c else None,
                "course_name": c.name if c else None,
                "session_date": slot_date.isoformat(),
                "time_from": tf.isoformat(timespec="seconds") if hasattr(tf, "isoformat") else str(tf),
                "time_to": tt.isoformat(timespec="seconds") if hasattr(tt, "isoformat") else str(tt),
                "session_ids": sids,
                "expected_people": active_party,
                "active_booking_count": active_bookings,
                "exams": exams_meta,
            }
        )
    return out
