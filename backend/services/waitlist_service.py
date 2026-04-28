"""Waitlist joins — used by chat and student router."""

import logging
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import ConsultationSession, ConsultationType, User, Waitlist

logger = logging.getLogger(__name__)


async def add_session_waitlist(
    session: AsyncSession,
    *,
    student_id: int,
    session_id: int,
) -> tuple[str, int]:
    """
    Join waitlist for a specific consultation session. Returns (message, position).
    Raises ValueError on invalid state.
    """
    cs = await session.get(ConsultationSession, session_id)
    if not cs:
        raise ValueError("Session not found")

    existing = (
        await session.scalars(
            select(Waitlist)
            .where(
                Waitlist.student_id == student_id,
                Waitlist.session_id == session_id,
                Waitlist.notified.is_(False),
            )
            .order_by(Waitlist.id.asc())
            .limit(1)
        )
    ).first()
    if existing:
        raise ValueError("Already on waitlist for this session")

    pos = int(
        await session.scalar(select(func.count()).select_from(Waitlist).where(Waitlist.session_id == session_id))
        or 0
    ) + 1
    session.add(
        Waitlist(
            student_id=student_id,
            professor_id=cs.professor_id,
            session_id=session_id,
            preferred_date=cs.session_date,
            consultation_type=cs.consultation_type,
            course_id=cs.course_id,
            position_hint=pos,
            any_slot_on_day=False,
        )
    )
    await session.flush()
    return (f"You've joined the waitlist at position #{pos}. We'll notify you if a spot opens.", pos)


async def add_day_waitlist(
    session: AsyncSession,
    *,
    student_id: int,
    professor_id: int,
    course_id: int | None,
    consultation_type: ConsultationType,
    preferred_date: date,
    any_slot_on_day: bool = True,
) -> tuple[str, int]:
    """
    Join waitlist for a calendar day without binding to a session yet
    (e.g. no free slots in the booking horizon).
    """
    dup_stmt = (
        select(Waitlist)
        .where(
            Waitlist.student_id == student_id,
            Waitlist.professor_id == professor_id,
            Waitlist.consultation_type == consultation_type,
            Waitlist.preferred_date == preferred_date,
            Waitlist.session_id.is_(None),
            Waitlist.notified.is_(False),
        )
    )
    if course_id is not None:
        dup_stmt = dup_stmt.where(Waitlist.course_id == course_id)
    else:
        dup_stmt = dup_stmt.where(Waitlist.course_id.is_(None))
    existing = (await session.scalars(dup_stmt.limit(1))).first()
    if existing:
        raise ValueError("Already on waitlist for this professor, day, and consultation type")

    cnt_stmt = select(func.count()).select_from(Waitlist).where(
        Waitlist.professor_id == professor_id,
        Waitlist.consultation_type == consultation_type,
        Waitlist.preferred_date == preferred_date,
        Waitlist.session_id.is_(None),
    )
    if course_id is not None:
        cnt_stmt = cnt_stmt.where(Waitlist.course_id == course_id)
    else:
        cnt_stmt = cnt_stmt.where(Waitlist.course_id.is_(None))
    pos = int(await session.scalar(cnt_stmt) or 0) + 1
    session.add(
        Waitlist(
            student_id=student_id,
            professor_id=professor_id,
            session_id=None,
            window_id=None,
            preferred_date=preferred_date,
            consultation_type=consultation_type,
            course_id=course_id,
            position_hint=pos,
            any_slot_on_day=any_slot_on_day,
        )
    )
    await session.flush()
    scope = "any time that day" if any_slot_on_day else "that day"
    return (
        f"You've joined the waitlist for {preferred_date.isoformat()} ({scope}) at position #{pos}. "
        "We'll notify you if a slot opens.",
        pos,
    )
