"""Tests for preparation scheduling request accept/decline."""

from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import select

from backend.db.models import (
    AcademicEvent,
    AcademicEventType,
    ConsultationSession,
    ConsultationType,
    Course,
    CourseProfessor,
    CourseStudent,
    CourseStudentStatus,
    Notification,
    PreparationVote,
    SchedulingRequest,
    SchedulingRequestStatus,
    Semester,
    SessionFormat,
    SessionStatus,
    UserRole,
)
from backend.services import scheduling_service

from .conftest import _user


@pytest.mark.asyncio
async def test_collect_vote_time_hints_dedupes(db):
    u1 = _user(UserRole.student)
    db.add(u1)
    await db.flush()
    c = Course(name="X", code="X101", semester=Semester.winter, year_of_study=1, department="CS")
    db.add(c)
    await db.flush()
    ev = AcademicEvent(
        course_id=c.id,
        event_type=AcademicEventType.exam,
        event_date=date.today() + timedelta(days=3),
        name="T",
    )
    db.add(ev)
    await db.flush()
    v1 = PreparationVote(
        student_id=u1.id,
        course_id=c.id,
        academic_event_id=ev.id,
        preferred_times=["Mon 10h", "Mon 10h", " Tue "],
    )
    db.add(v1)
    await db.flush()
    hints = scheduling_service.collect_vote_time_hints([v1])
    assert hints == ["Mon 10h", "Tue"]


@pytest.mark.asyncio
async def test_accept_creates_preparation_session_and_notifies(db, student, professor, course):
    db.add(CourseProfessor(professor_id=professor.id, course_id=course.id, academic_year="2025/2026"))
    db.add(
        CourseStudent(
            student_id=student.id,
            course_id=course.id,
            academic_year="2025/2026",
            status=CourseStudentStatus.active,
        )
    )
    event_date = date.today() + timedelta(days=5)
    ev = AcademicEvent(
        course_id=course.id,
        event_type=AcademicEventType.exam,
        event_date=event_date,
        name="Final",
    )
    db.add(ev)
    await db.flush()
    db.add(PreparationVote(student_id=student.id, course_id=course.id, academic_event_id=ev.id))
    await db.flush()
    deadline = datetime.now(UTC) + timedelta(days=1)
    sr = SchedulingRequest(
        professor_id=professor.id,
        course_id=course.id,
        academic_event_id=ev.id,
        vote_count=1,
        status=SchedulingRequestStatus.pending,
        deadline_at=deadline,
    )
    db.add(sr)
    await db.flush()

    slot = date.today() + timedelta(days=2)
    _, cs = await scheduling_service.respond_preparation_request(
        db,
        professor=professor,
        request_id=sr.id,
        accept=True,
        slot_date=slot,
        time_from=time(14, 0),
        time_to=time(15, 30),
    )
    await db.commit()

    assert cs is not None
    assert cs.consultation_type == ConsultationType.preparation
    assert cs.event_id == ev.id
    reloaded = await db.get(SchedulingRequest, sr.id)
    assert reloaded is not None
    assert reloaded.status == SchedulingRequestStatus.accepted
    assert reloaded.session_id == cs.id

    n = await db.scalar(select(Notification).where(Notification.user_id == student.id))
    assert n is not None
    assert "preparation" in (n.text or "").lower() or "scheduled" in (n.text or "").lower()


@pytest.mark.asyncio
async def test_decline_notifies_voters(db, student, professor, course):
    db.add(CourseProfessor(professor_id=professor.id, course_id=course.id, academic_year="2025/2026"))
    event_date = date.today() + timedelta(days=5)
    ev = AcademicEvent(
        course_id=course.id,
        event_type=AcademicEventType.exam,
        event_date=event_date,
        name="Mid",
    )
    db.add(ev)
    await db.flush()
    db.add(PreparationVote(student_id=student.id, course_id=course.id, academic_event_id=ev.id))
    await db.flush()
    deadline = datetime.now(UTC) + timedelta(days=1)
    sr = SchedulingRequest(
        professor_id=professor.id,
        course_id=course.id,
        academic_event_id=ev.id,
        vote_count=1,
        status=SchedulingRequestStatus.pending,
        deadline_at=deadline,
    )
    db.add(sr)
    await db.flush()

    await scheduling_service.respond_preparation_request(
        db, professor=professor, request_id=sr.id, accept=False
    )
    await db.commit()

    reloaded = await db.get(SchedulingRequest, sr.id)
    assert reloaded is not None
    assert reloaded.status == SchedulingRequestStatus.declined
    n = await db.scalar(select(Notification).where(Notification.user_id == student.id))
    assert n is not None


@pytest.mark.asyncio
async def test_accept_link_existing_session(db, student, professor, course):
    db.add(CourseProfessor(professor_id=professor.id, course_id=course.id, academic_year="2025/2026"))
    db.add(
        CourseStudent(
            student_id=student.id,
            course_id=course.id,
            academic_year="2025/2026",
            status=CourseStudentStatus.active,
        )
    )
    event_date = date.today() + timedelta(days=5)
    ev = AcademicEvent(
        course_id=course.id,
        event_type=AcademicEventType.exam,
        event_date=event_date,
        name="E",
    )
    db.add(ev)
    await db.flush()
    db.add(PreparationVote(student_id=student.id, course_id=course.id, academic_event_id=ev.id))
    await db.flush()
    deadline = datetime.now(UTC) + timedelta(days=1)
    sr = SchedulingRequest(
        professor_id=professor.id,
        course_id=course.id,
        academic_event_id=ev.id,
        vote_count=1,
        status=SchedulingRequestStatus.pending,
        deadline_at=deadline,
    )
    db.add(sr)
    await db.flush()
    existing = ConsultationSession(
        professor_id=professor.id,
        course_id=course.id,
        consultation_type=ConsultationType.preparation,
        session_date=date.today() + timedelta(days=1),
        time_from=time(9, 0),
        time_to=time(10, 0),
        format=SessionFormat.in_person,
        status=SessionStatus.confirmed,
        capacity=20,
        announced_by_professor=True,
        event_id=ev.id,
    )
    db.add(existing)
    await db.flush()

    _, cs = await scheduling_service.respond_preparation_request(
        db,
        professor=professor,
        request_id=sr.id,
        accept=True,
        session_id=existing.id,
    )
    await db.commit()

    assert cs is not None
    assert cs.id == existing.id
    reloaded = await db.get(SchedulingRequest, sr.id)
    assert reloaded is not None
    assert reloaded.session_id == existing.id
