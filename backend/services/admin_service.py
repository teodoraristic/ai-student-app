"""Admin operations: users, content, sessions."""

import logging
import secrets
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    Announcement,
    AcademicEvent,
    Course,
    ExamPeriod,
    KnowledgeBase,
    Notification,
    ProfessorProfile,
    SystemConfig,
    User,
    UserRole,
)
from backend.services import auth_service

logger = logging.getLogger(__name__)


async def create_user(
    session: AsyncSession,
    *,
    email: str,
    first_name: str,
    last_name: str,
    role: UserRole,
    student_number: Optional[str],
    study_year: Optional[int],
    created_by: User,
) -> tuple[User, str]:
    exists = await session.scalar(select(User).where(User.email == email))
    if exists:
        raise ValueError("Email already registered")

    otp = auth_service.generate_otp()
    otp_hash = auth_service.hash_password(otp)
    dummy_password = auth_service.hash_password(secrets.token_urlsafe(32))

    final_year = False
    stored_year: Optional[int] = None
    if role == UserRole.student:
        stored_year = study_year
        if stored_year is None:
            raise ValueError("study_year is required for students")
        # Year 4+ treated as final-year for thesis-related rules (bachelor IV / master).
        final_year = stored_year >= 4

    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role,
        student_number=student_number if role == UserRole.student else None,
        study_year=stored_year,
        is_final_year=final_year,
        password_hash=dummy_password,
        one_time_password_hash=otp_hash,
        password_change_required=True,
        is_active=True,
        created_by_id=created_by.id,
    )
    session.add(user)
    await session.flush()

    if role == UserRole.professor:
        session.add(
            ProfessorProfile(
                user_id=user.id,
                department="",
                office_location="",
                default_room="",
                max_thesis_students=0,
            )
        )
    return user, otp


async def deactivate_user(session: AsyncSession, target: User) -> None:
    target.is_active = False
    await session.flush()


async def reset_user_password(session: AsyncSession, target: User) -> str:
    otp = auth_service.generate_otp()
    target.one_time_password_hash = auth_service.hash_password(otp)
    target.password_change_required = True
    target.password_hash = auth_service.hash_password(secrets.token_urlsafe(32))
    await session.flush()
    return otp


async def upsert_system_config(
    session: AsyncSession, key: str, value: str, description: Optional[str] = None
) -> SystemConfig:
    row = await session.scalar(select(SystemConfig).where(SystemConfig.key == key))
    if not row:
        row = SystemConfig(key=key, value=value, description=description or "")
        session.add(row)
    else:
        row.value = value
        if description:
            row.description = description
        row.updated_at = datetime.now(UTC)
    await session.flush()
    return row


async def notify_all_students(session: AsyncSession, title: str, body: str, admin: User) -> Announcement:
    ann = Announcement(title=title, body=body, created_by_id=admin.id)
    session.add(ann)
    await session.flush()
    students = (await session.scalars(select(User).where(User.role == UserRole.student))).all()
    for s in students:
        session.add(
            Notification(
                user_id=s.id,
                text=f"Announcement: {title}",
                notification_type="announcement",
            )
        )
    await session.flush()
    return ann
