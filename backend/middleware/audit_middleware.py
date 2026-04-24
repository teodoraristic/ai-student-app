"""Record audit log entries for mutating HTTP methods."""

import logging
from typing import Callable

from fastapi import Request, Response
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from backend.config import get_settings
from backend.db.base import async_session_maker
from backend.db.models import AuditLog

logger = logging.getLogger(__name__)

SKIP_PREFIXES = ("/health", "/docs", "/openapi.json", "/redoc")


class AuditMiddleware(BaseHTTPMiddleware):
    """Persist audit rows for POST / PATCH / DELETE."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        if request.method not in ("POST", "PATCH", "DELETE"):
            return response
        path = request.url.path
        if any(path.startswith(p) for p in SKIP_PREFIXES):
            return response
        if path.startswith("/auth/login"):
            return response

        user_id = None
        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
            try:
                settings = get_settings()
                payload = jwt.decode(
                    token,
                    settings.jwt_secret,
                    algorithms=[settings.jwt_algorithm],
                )
                user_id = int(payload.get("sub", 0)) or None
            except (JWTError, ValueError, TypeError):
                user_id = None

        try:
            async with async_session_maker() as session:
                session.add(
                    AuditLog(
                        user_id=user_id,
                        action=request.method,
                        entity_type="http",
                        entity_id=None,
                        detail={"path": path},
                    )
                )
                await session.commit()
        except Exception as e:
            logger.warning("audit log failed: %s", e)

        return response
