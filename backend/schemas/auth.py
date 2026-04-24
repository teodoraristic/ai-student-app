"""Auth-related Pydantic models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from backend.db.models import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserPublic(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    role: UserRole
    password_change_required: bool
    consent_accepted_at: Optional[datetime] = None
    is_final_year: bool = False

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class MessageResponse(BaseModel):
    message: str
