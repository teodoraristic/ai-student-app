"""Authentication endpoints."""

import logging
from datetime import UTC, datetime
from time import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import get_db
from backend.db.models import User
from backend.middleware.auth_middleware import get_current_user
from backend.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    TokenResponse,
    UserPublic,
)
from backend.services import auth_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

_LOGIN_FAIL_WINDOW_SEC = 300.0
_LOGIN_FAIL_MAX = 15
_login_fail_times: dict[str, list[float]] = {}


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _prune_login_failures(ip: str) -> list[float]:
    now = time()
    buf = _login_fail_times.setdefault(ip, [])
    buf[:] = [t for t in buf if now - t < _LOGIN_FAIL_WINDOW_SEC]
    return buf


def _enforce_login_rate_limit(request: Request) -> None:
    ip = _client_ip(request)
    if len(_prune_login_failures(ip)) >= _LOGIN_FAIL_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
        )


def _record_login_failure(request: Request) -> None:
    _prune_login_failures(_client_ip(request)).append(time())


def _clear_login_failures(request: Request) -> None:
    _login_fail_times.pop(_client_ip(request), None)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    _enforce_login_rate_limit(request)
    user = await auth_service.authenticate_user(db, body.email, body.password)
    if not user:
        _record_login_failure(request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    _clear_login_failures(request)
    user.last_login = datetime.now(UTC)
    await db.commit()
    await db.refresh(user)

    token = auth_service.create_access_token(user.id, user.role)
    return TokenResponse(
        access_token=token,
        user=UserPublic.model_validate(user),
    )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageResponse:
    try:
        await auth_service.change_password(db, user, body.new_password, body.current_password)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return MessageResponse(message="Password updated")


@router.get("/me", response_model=UserPublic)
async def me(
    user: User = Depends(get_current_user),
) -> UserPublic:
    return UserPublic.model_validate(user)


@router.post("/accept-consent", response_model=MessageResponse)
async def accept_consent(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageResponse:
    await auth_service.set_user_consent(db, user)
    await db.commit()
    return MessageResponse(message="Consent recorded")
