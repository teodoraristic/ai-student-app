"""Tests for exam_service — registrations, validation, suggestions."""

from datetime import UTC, date, datetime, timedelta, time

import pytest

from backend.db.models import (
    AcademicEvent,
    AcademicEventType,
    ConsultationWindow,
    ExamPeriod,
    ExamRegistration,
    ExamRegistrationStatus,
    WindowType,
)
from backend.services import exam_service


@pytest.mark.asyncio
async def test_validate_midterm_rejects_exam_period(db, course):
    ep = ExamPeriod(date_from=date.today(), date_to=date.today() + timedelta(days=30), name="P")
    db.add(ep)
    await db.flush()
    with pytest.raises(ValueError, match="Midterm"):
        await exam_service.validate_academic_event_fields(
            db,
            event_type=AcademicEventType.midterm,
            event_date=date.today() + timedelta(days=5),
            exam_period_id=ep.id,
        )


@pytest.mark.asyncio
async def test_validate_exam_date_outside_period(db, course):
    ep = ExamPeriod(date_from=date.today() + timedelta(days=20), date_to=date.today() + timedelta(days=25), name="P")
    db.add(ep)
    await db.flush()
    with pytest.raises(ValueError, match="within"):
        await exam_service.validate_academic_event_fields(
            db,
            event_type=AcademicEventType.exam,
            event_date=date.today() + timedelta(days=5),
            exam_period_id=ep.id,
        )


@pytest.mark.asyncio
async def test_register_and_cancel(db, student, course, enrolled):
    ev = AcademicEvent(
        course_id=course.id,
        event_type=AcademicEventType.midterm,
        event_date=date.today() + timedelta(days=7),
        name="Mid",
        academic_year="2025/2026",
    )
    db.add(ev)
    await db.flush()
    reg = await exam_service.register_for_exam(db, student.id, ev.id)
    assert reg.status == ExamRegistrationStatus.registered
    await exam_service.cancel_registration(db, student.id, reg.id)
    await db.refresh(reg)
    assert reg.status == ExamRegistrationStatus.cancelled
    reg2 = await exam_service.register_for_exam(db, student.id, ev.id)
    assert reg2.id == reg.id
    assert reg2.status == ExamRegistrationStatus.registered


@pytest.mark.asyncio
async def test_list_student_registrations_omits_past_exams(db, student, course, enrolled):
    today = datetime.now(UTC).date()
    past_ev = AcademicEvent(
        course_id=course.id,
        event_type=AcademicEventType.exam,
        event_date=today - timedelta(days=5),
        name="Past final",
        academic_year="2025/2026",
    )
    future_ev = AcademicEvent(
        course_id=course.id,
        event_type=AcademicEventType.exam,
        event_date=today + timedelta(days=8),
        name="Upcoming final",
        academic_year="2025/2026",
    )
    db.add(past_ev)
    db.add(future_ev)
    await db.flush()
    db.add(
        ExamRegistration(
            student_id=student.id,
            academic_event_id=past_ev.id,
            status=ExamRegistrationStatus.registered,
        )
    )
    db.add(
        ExamRegistration(
            student_id=student.id,
            academic_event_id=future_ev.id,
            status=ExamRegistrationStatus.registered,
        )
    )
    await db.flush()
    rows = await exam_service.list_student_registrations(db, student.id)
    ids = {r["academic_event_id"] for r in rows}
    assert past_ev.id not in ids
    assert future_ev.id in ids


@pytest.mark.asyncio
async def test_register_past_exam_fails(db, student, course, enrolled):
    ev = AcademicEvent(
        course_id=course.id,
        event_type=AcademicEventType.midterm,
        event_date=date.today() - timedelta(days=1),
        name="Past",
        academic_year="2025/2026",
    )
    db.add(ev)
    await db.flush()
    with pytest.raises(ValueError, match="past|closed|Registration"):
        await exam_service.register_for_exam(db, student.id, ev.id)


@pytest.mark.asyncio
async def test_register_not_enrolled_fails(db, student, course):
    ev = AcademicEvent(
        course_id=course.id,
        event_type=AcademicEventType.midterm,
        event_date=date.today() + timedelta(days=10),
        name="X",
        academic_year="2025/2026",
    )
    db.add(ev)
    await db.flush()
    with pytest.raises(ValueError, match="not enrolled"):
        await exam_service.register_for_exam(db, student.id, ev.id)


@pytest.mark.asyncio
async def test_suggest_preparation_before_event(db, professor, course, enrolled):
    d_exam = date.today() + timedelta(days=14)
    ev = AcademicEvent(
        course_id=course.id,
        event_type=AcademicEventType.exam,
        event_date=d_exam,
        name="Final",
        academic_year="2025/2026",
    )
    db.add(ev)
    db.add(
        ConsultationWindow(
            professor_id=professor.id,
            day_of_week="monday",
            time_from=time(10, 0),
            time_to=time(11, 0),
            window_type=WindowType.regular,
            is_active=True,
        )
    )
    await db.flush()
    out = await exam_service.suggest_consultation_slot(db, professor.id, event_date=d_exam, purpose="preparation")
    assert out["date"] is not None
    assert out["time_from"] is not None
    sug = date.fromisoformat(out["date"])
    assert sug < d_exam


@pytest.mark.asyncio
async def test_patch_midterm_clears_period(db, course):
    ep = ExamPeriod(date_from=date.today() - timedelta(days=1), date_to=date.today() + timedelta(days=60), name="P")
    db.add(ep)
    await db.flush()
    ev = AcademicEvent(
        course_id=course.id,
        event_type=AcademicEventType.exam,
        event_date=date.today() + timedelta(days=10),
        name="E",
        academic_year="2025/2026",
        exam_period_id=ep.id,
    )
    db.add(ev)
    await db.flush()
    await exam_service.patch_academic_event(db, ev.id, {"type": AcademicEventType.midterm})
    await db.refresh(ev)
    assert ev.exam_period_id is None
    assert ev.event_type == AcademicEventType.midterm
