"""Authentication: passwords, OTP, JWT."""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.db.models import User, UserRole

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_otp() -> str:
    return "STU-" + secrets.token_urlsafe(8).upper()


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, role: UserRole, extra: Optional[dict[str, Any]] = None) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role.value,
        "exp": expire,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> Optional[User]:
    user = await session.scalar(select(User).where(User.email == email))
    if not user or not user.is_active:
        return None

    if user.password_change_required and user.one_time_password_hash:
        if verify_password(password, user.one_time_password_hash):
            return user
        return None

    if verify_password(password, user.password_hash):
        return user
    return None


async def change_password(
    session: AsyncSession,
    user: User,
    new_password: str,
    current_password: str,
) -> None:
    if user.password_change_required and user.one_time_password_hash:
        if not verify_password(current_password, user.one_time_password_hash):
            raise ValueError("Invalid current password or OTP")
    else:
        if not verify_password(current_password, user.password_hash):
            raise ValueError("Invalid current password")

    user.password_hash = hash_password(new_password)
    user.password_change_required = False
    user.one_time_password_hash = None
    await session.flush()


async def set_user_consent(session: AsyncSession, user: User) -> None:
    user.consent_accepted_at = datetime.now(UTC)
    await session.flush()
