"""Shared fixtures for all tests. Uses SQLite in-memory via aiosqlite."""

# Patch PostgreSQL-specific JSONB → JSON before any backend modules are imported.
# This must stay at the very top of the file so models.py picks up the patch.
import sqlalchemy.dialects.postgresql as _pg
from sqlalchemy import JSON as _JSON
_pg.JSONB = _JSON  # type: ignore[attr-defined]

import random
from datetime import date, time, timedelta

import pytest_asyncio
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import backend.db.models  # noqa: F401 — registers all models on Base
from backend.db.base import Base
from backend.db.models import (
    AcademicEvent,
    AcademicEventType,
    Booking,
    BookingPriority,
    BookingStatus,
    ConsultationSession,
    ConsultationType,
    ConsultationWindow,
    Course,
    CourseProfessor,
    CourseStudent,
    CourseStudentStatus,
    ExamPeriod,
    ProfessorProfile,
    Semester,
    SessionFormat,
    SessionStatus,
    SystemConfig,
    ThesisApplication,
    ThesisApplicationStatus,
    User,
    UserRole,
    Waitlist,
    WindowType,
)

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


# ---------------------------------------------------------------------------
# Session fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with maker() as session:
        yield session
        await session.rollback()
    await engine.dispose()


# ---------------------------------------------------------------------------
# Object factories
# ---------------------------------------------------------------------------

def _user(role: UserRole, first_name: str = "Test", last_name: str = "User", **kw) -> User:
    return User(
        email=f"test{random.randint(10_000, 99_999)}@x.com",
        first_name=first_name,
        last_name=last_name,
        role=role,
        password_hash=_pwd.hash("pw"),
        is_active=True,
        password_change_required=False,
        **kw,
    )


@pytest_asyncio.fixture
async def student(db: AsyncSession) -> User:
    u = _user(UserRole.student, "Ana", "Student", is_final_year=True)
    db.add(u)
    await db.flush()
    return u


@pytest_asyncio.fixture
async def professor(db: AsyncSession) -> User:
    u = _user(UserRole.professor, "Nikola", "Markovic")
    db.add(u)
    await db.flush()
    db.add(ProfessorProfile(user_id=u.id, max_thesis_students=5))
    await db.flush()
    return u


@pytest_asyncio.fixture
async def admin_user(db: AsyncSession) -> User:
    u = _user(UserRole.admin, "Admin", "User")
    db.add(u)
    await db.flush()
    return u


@pytest_asyncio.fixture
async def course(db: AsyncSession) -> Course:
    c = Course(name="Databases", code=f"DB{random.randint(100,999)}", semester=Semester.winter, year_of_study=1, department="CS")
    db.add(c)
    await db.flush()
    return c


@pytest_asyncio.fixture
async def enrolled(db: AsyncSession, student: User, professor: User, course: Course):
    """Enroll student in course and assign professor to course."""
    db.add(CourseProfessor(professor_id=professor.id, course_id=course.id, academic_year="2025/2026"))
    db.add(CourseStudent(student_id=student.id, course_id=course.id, academic_year="2025/2026", status=CourseStudentStatus.active))
    await db.flush()


async def add_windows_all_days(
    db: AsyncSession,
    professor_id: int,
    wtype: WindowType = WindowType.regular,
    t_from: time = time(9, 0),
    t_to: time = time(10, 0),
) -> None:
    """Add ConsultationWindows for every day of the week."""
    for wd in WEEKDAYS:
        db.add(ConsultationWindow(
            professor_id=professor_id,
            day_of_week=wd,
            time_from=t_from,
            time_to=t_to,
            window_type=wtype,
            is_active=True,
        ))
    await db.flush()


def future_session(
    professor_id: int,
    course_id: int,
    ctype: ConsultationType,
    days_ahead: int = 2,
    capacity: int = 20,
    announced: bool = False,
) -> ConsultationSession:
    d = date.today() + timedelta(days=days_ahead)
    return ConsultationSession(
        professor_id=professor_id,
        course_id=course_id,
        consultation_type=ctype,
        session_date=d,
        time_from=time(10, 0),
        time_to=time(11, 0),
        format=SessionFormat.in_person,
        status=SessionStatus.confirmed,
        capacity=capacity,
        announced_by_professor=announced,
    )


def active_booking(student_id: int, session_id: int, group_size: int = 1) -> Booking:
    return Booking(
        student_id=student_id,
        session_id=session_id,
        group_size=group_size,
        status=BookingStatus.active,
        priority=BookingPriority.normal,
        is_urgent=False,
    )
