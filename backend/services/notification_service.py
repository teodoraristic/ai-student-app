"""In-app notifications."""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import CourseStudent, Notification

logger = logging.getLogger(__name__)


async def notify_user(
    session: AsyncSession,
    user_id: int,
    text: str,
    *,
    notification_type: str = "info",
    link: Optional[str] = None,
) -> Notification:
    n = Notification(user_id=user_id, text=text, notification_type=notification_type, link=link)
    session.add(n)
    await session.flush()
    return n


async def notify_course_students_except(
    session: AsyncSession,
    course_id: int,
    exclude_student_id: int,
    text: str,
    *,
    notification_type: str = "info",
) -> None:
    """Notify all students enrolled in a course except one (e.g. after a preparation vote)."""
    rows = list(
        (
            await session.scalars(
                select(CourseStudent.student_id).where(CourseStudent.course_id == course_id)
            )
        ).all()
    )
    for sid in rows:
        if sid != exclude_student_id:
            await notify_user(session, sid, text, notification_type=notification_type)
