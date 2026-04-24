"""Chatbot endpoint — thin router."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import get_db
from backend.db.models import User, UserRole
from backend.middleware.auth_middleware import require_role
from backend.schemas.chat import ChatMessage, ChatResponse
from backend.services import chat_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    msg: ChatMessage,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.student)),
) -> ChatResponse:
    payload = await chat_service.process(
        msg.text,
        user.id,
        db,
        structured=msg.structured,
    )
    await db.commit()
    return ChatResponse.model_validate(payload)
