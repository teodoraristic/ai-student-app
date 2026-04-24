"""Email abstraction — console or SendGrid."""

import logging
from abc import ABC, abstractmethod
from typing import Literal

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)


class EmailProvider(ABC):
    """Abstract email sender."""

    @abstractmethod
    async def send(self, to: str, subject: str, body: str) -> None:
        """Send an email message."""


class ConsoleEmailProvider(EmailProvider):
    """Log-only provider for local development."""

    async def send(self, to: str, subject: str, body: str) -> None:
        logger.info(
            "[email:console] to=%s subject=%s body_len=%s",
            to,
            subject,
            len(body),
        )


class SendGridEmailProvider(EmailProvider):
    """SendGrid REST API (free tier friendly)."""

    def __init__(self, api_key: str, from_email: str) -> None:
        self._api_key = api_key
        self._from = from_email

    async def send(self, to: str, subject: str, body: str) -> None:
        url = "https://api.sendgrid.com/v3/mail/send"
        payload = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": self._from},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            r.raise_for_status()


def get_email_provider() -> EmailProvider:
    settings = get_settings()
    kind: Literal["console", "sendgrid"] = (
        "sendgrid" if settings.email_provider.lower() == "sendgrid" else "console"
    )
    if kind == "sendgrid" and settings.sendgrid_api_key:
        return SendGridEmailProvider(settings.sendgrid_api_key, settings.email_from)
    return ConsoleEmailProvider()
