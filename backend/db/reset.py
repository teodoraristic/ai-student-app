"""Drop and recreate public schema, then re-seed."""

import asyncio
import logging

from sqlalchemy import text

from backend.db.base import engine
from backend.db.seed import seed
from backend.db.base import async_session_maker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    async with engine.begin() as conn:
        logger.info("Dropping public schema...")
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        logger.info("Schema recreated.")

    # Re-run alembic migrations via SQLAlchemy create_all (uses Base metadata)
    from backend.db.models import Base  # noqa: PLC0415
    async with engine.begin() as conn:
        logger.info("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        logger.info("Seeding...")
        await seed(session)

    logger.info("Reset complete.")


if __name__ == "__main__":
    asyncio.run(main())
