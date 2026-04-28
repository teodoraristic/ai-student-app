"""Waitlist-related slot queries."""

from datetime import date, time, timedelta

import pytest

from backend.db.models import (
    ConsultationSession,
    ConsultationType,
    SessionFormat,
    SessionStatus,
)

from backend.services import slot_service

from .conftest import active_booking, future_session


@pytest.mark.asyncio
async def test_get_full_sessions_includes_unannounced_general(db, student, professor, course, enrolled):
    """General sessions from windows can be full without announced_by_professor."""
    cs = future_session(professor.id, course.id, ConsultationType.general, days_ahead=4, capacity=2)
    cs.announced_by_professor = False
    db.add(cs)
    await db.flush()
    db.add(active_booking(student.id, cs.id, group_size=2))
    await db.flush()

    full = await slot_service.get_full_sessions(
        db,
        professor_id=professor.id,
        course_id=course.id,
        ctype=ConsultationType.general,
        next_weeks=3,
        student_id=student.id,
    )
    assert len(full) == 1
    assert full[0].id == cs.id


@pytest.mark.asyncio
async def test_get_full_sessions_on_date_filter(db, student, professor, course, enrolled):
    d0 = date.today() + timedelta(days=5)
    d1 = date.today() + timedelta(days=6)
    cs0 = ConsultationSession(
        professor_id=professor.id,
        course_id=course.id,
        consultation_type=ConsultationType.general,
        session_date=d0,
        time_from=time(10, 0),
        time_to=time(10, 15),
        format=SessionFormat.in_person,
        status=SessionStatus.confirmed,
        capacity=1,
        announced_by_professor=False,
    )
    cs1 = ConsultationSession(
        professor_id=professor.id,
        course_id=course.id,
        consultation_type=ConsultationType.general,
        session_date=d1,
        time_from=time(11, 0),
        time_to=time(11, 15),
        format=SessionFormat.in_person,
        status=SessionStatus.confirmed,
        capacity=1,
        announced_by_professor=False,
    )
    db.add(cs0)
    db.add(cs1)
    await db.flush()
    db.add(active_booking(student.id, cs0.id))
    db.add(active_booking(student.id, cs1.id))
    await db.flush()

    only_d0 = await slot_service.get_full_sessions(
        db,
        professor_id=professor.id,
        course_id=course.id,
        ctype=ConsultationType.general,
        next_weeks=3,
        on_date=d0,
        student_id=student.id,
    )
    assert len(only_d0) == 1
    assert only_d0[0].session_date == d0
