"""Thesis supervision capacity and post-accept booking helpers."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    ConsultationType,
    CourseProfessor,
    CourseStudent,
    ProfessorProfile,
    ThesisApplication,
    ThesisApplicationStatus,
    User,
)

logger = logging.getLogger(__name__)


async def count_active_thesis_for_professor(session: AsyncSession, professor_id: int) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(ThesisApplication)
            .where(
                ThesisApplication.professor_id == professor_id,
                ThesisApplication.status == ThesisApplicationStatus.active,
            )
        )
        or 0
    )


async def get_max_thesis_students(session: AsyncSession, professor_id: int) -> int:
    profile = await session.scalar(
        select(ProfessorProfile).where(ProfessorProfile.user_id == professor_id)
    )
    return int(profile.max_thesis_students) if profile else 0


async def professor_has_open_thesis_spot(session: AsyncSession, professor_id: int) -> bool:
    cap = await get_max_thesis_students(session, professor_id)
    if cap <= 0:
        return False
    used = await count_active_thesis_for_professor(session, professor_id)
    return used < cap


async def first_shared_course_id(
    session: AsyncSession, student_id: int, professor_id: int
) -> Optional[int]:
    return await session.scalar(
        select(CourseStudent.course_id)
        .join(CourseProfessor, CourseProfessor.course_id == CourseStudent.course_id)
        .where(
            CourseStudent.student_id == student_id,
            CourseProfessor.professor_id == professor_id,
        )
        .limit(1)
    )


async def try_auto_book_thesis_intro_session(
    session: AsyncSession,
    *,
    student: User,
    professor_id: int,
    topic_description: str,
) -> None:
    """If enabled in system_config, book the earliest free thesis slot after acceptance."""
    from backend.services import booking_service, config_service, notification_service, slot_service

    enabled = await config_service.get_config_int(session, "thesis_auto_book_on_accept", 1)
    if not enabled:
        return
    course_id = await first_shared_course_id(session, student.id, professor_id)
    try:
        slots = await slot_service.get_free_slots(
            session,
            professor_id=professor_id,
            course_id=course_id,
            ctype=ConsultationType.thesis,
            group_size=1,
            student_id=student.id,
            next_weeks=3,
        )
    except ValueError as e:
        logger.info("thesis auto-book skipped: %s", e)
        return
    if not slots:
        return
    preview = (topic_description or "").strip()[:500] or None
    b = await booking_service.create_booking(
        session,
        student=student,
        session_id=slots[0].id,
        task="Thesis consultation",
        anonymous_question=preview,
        is_urgent=False,
        group_size=1,
    )
    cs = slots[0]
    await notification_service.notify_user(
        session,
        student.id,
        f"A thesis consultation was scheduled for you on {cs.session_date} "
        f"({cs.time_from.strftime('%H:%M')}–{cs.time_to.strftime('%H:%M')}). Booking #{b.id}.",
        notification_type="booking",
    )
