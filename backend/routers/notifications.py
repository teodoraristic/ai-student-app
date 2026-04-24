"""In-app notifications."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import get_db
from backend.db.models import Notification, User
from backend.middleware.auth_middleware import get_current_user

router = APIRouter(prefix="", tags=["notifications"])


class NotificationOut(BaseModel):
    id: int
    text: str
    notification_type: str
    is_read: bool
    created_at: str
    link: str | None

    model_config = {"from_attributes": True}


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = list(
        (
            await db.scalars(
                select(Notification)
                .where(Notification.user_id == user.id)
                .order_by(Notification.created_at.desc())
                .limit(100)
            )
        ).all()
    )
    return [
        NotificationOut(
            id=n.id,
            text=n.text,
            notification_type=n.notification_type,
            is_read=n.is_read,
            created_at=n.created_at.isoformat(),
            link=n.link,
        )
        for n in rows
    ]


@router.patch("/notifications/{notif_id}/read")
async def read_one(
    notif_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    n = await db.get(Notification, notif_id)
    if not n or n.user_id != user.id:
        return {"ok": False}
    n.is_read = True
    await db.commit()
    return {"ok": True}


@router.patch("/notifications/read-all")
async def read_all(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await db.execute(update(Notification).where(Notification.user_id == user.id).values(is_read=True))
    await db.commit()
    return {"ok": True}
