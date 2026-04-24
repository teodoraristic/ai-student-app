"""Read system configuration from database."""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import SystemConfig

logger = logging.getLogger(__name__)


async def get_config_value(session: AsyncSession, key: str, default: Optional[str] = None) -> str:
    row = await session.scalar(select(SystemConfig).where(SystemConfig.key == key))
    if row:
        return row.value
    if default is not None:
        return default
    raise KeyError(f"Missing system_config key: {key}")


async def get_config_int(session: AsyncSession, key: str, default: int) -> int:
    raw = await get_config_value(session, key, str(default))
    return int(raw)
