"""FastAPI application entry."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.middleware.audit_middleware import AuditMiddleware
from backend.routers import admin as admin_router
from backend.routers import auth as auth_router
from backend.routers import chat as chat_router
from backend.routers import notifications as notifications_router
from backend.routers import professor as professor_router
from backend.routers import shared as shared_router
from backend.routers import student as student_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    def _run_migrations() -> None:
        from alembic.config import Config as AlembicConfig
        from alembic import command as alembic_command

        cfg = AlembicConfig(str(Path(__file__).parent / "alembic.ini"))
        cfg.set_main_option("script_location", str(Path(__file__).parent / "alembic"))
        alembic_command.upgrade(cfg, "head")

    try:
        await asyncio.to_thread(_run_migrations)
        logger.info("Migrations applied.")
    except Exception as e:
        logger.warning("Migration failed (DB may not be ready): %s", e)

    try:
        from backend.db.base import async_session_maker
        from backend.db.seed import seed

        async with async_session_maker() as session:
            await seed(session)
        logger.info("Seed complete.")
    except Exception as e:
        logger.warning("Seed failed: %s", e)

    yield


app = FastAPI(title="Student Consultation API", version="0.1.0", lifespan=lifespan)

app.add_middleware(AuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(chat_router.router)
app.include_router(student_router.router)
app.include_router(professor_router.router)
app.include_router(admin_router.router)
app.include_router(notifications_router.router)
app.include_router(shared_router.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
