"""Chat request/response models."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    text: str = Field(default="", max_length=8000)
    structured: Optional[dict[str, Any]] = None


class ChatResponse(BaseModel):
    message: str = ""
    slots: list[dict[str, Any]] = Field(default_factory=list)
    chips: list[dict[str, Any]] = Field(default_factory=list)
    phase: str = "collect"
    manual_form: bool = False
    context: dict[str, Any] = Field(default_factory=dict)
