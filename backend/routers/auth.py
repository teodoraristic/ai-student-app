"""Authentication endpoints."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
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


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await auth_service.authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

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
