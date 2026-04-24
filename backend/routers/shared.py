"""Shared endpoints (feedback, privacy)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import get_db
from backend.db.models import Booking, BookingStatus, Feedback, User
from backend.middleware.auth_middleware import get_current_user

router = APIRouter(tags=["shared"])


class FeedbackBody(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=4000)


@router.post("/feedback/{booking_id}")
async def post_feedback(
    booking_id: int,
    body: FeedbackBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    b = await db.get(Booking, booking_id)
    if not b or b.student_id != user.id:
        raise HTTPException(status_code=404)
    if b.status != BookingStatus.attended:
        raise HTTPException(status_code=400, detail="Feedback is only available for attended consultations.")
    existing = await db.scalar(select(Feedback).where(Feedback.booking_id == booking_id))
    if existing:
        raise HTTPException(status_code=400, detail="Already submitted")
    db.add(Feedback(booking_id=booking_id, rating=body.rating, comment=body.comment))
    await db.commit()
    return {"ok": True}


@router.get("/privacy")
async def privacy() -> dict[str, str]:
    return {
        "title": "Privacy policy",
        "body": (
            "This demo application processes consultation bookings, course enrollment, and "
            "anonymous questions for educational scheduling. Data is stored in a PostgreSQL "
            "database. Contact your university DPO for GDPR-related requests."
        ),
    }
