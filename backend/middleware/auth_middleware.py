"""JWT authentication and role-based access."""

import logging
from typing import Annotated, Callable, TypeVar

from jose import JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import User, UserRole
from backend.db.base import get_db
from backend.services import auth_service

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

F = TypeVar("F", bound=Callable[..., object])


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = auth_service.decode_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError) as e:
        logger.debug("JWT invalid: %s", e)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e

    user = await db.scalar(select(User).where(User.id == user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or missing")
    return user


def require_role(*allowed: UserRole) -> Callable[..., User]:
    """Return a FastAPI dependency that enforces role membership."""

    allowed_values = {r.value for r in allowed}

    async def _dep(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role.value not in allowed_values:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _dep
