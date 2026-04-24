"""Tests for slot_service — slot generation, filtering, exam period rules."""

from datetime import date, time, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    ConsultationSession,
    ConsultationType,
    ExamPeriod,
    SessionFormat,
    SessionStatus,
    ThesisApplication,
    ThesisApplicationStatus,
    User,
    WindowType,
)
from backend.services import slot_service

from .conftest import (
    add_windows_all_days,
    active_booking,
    future_session,
)


class TestGeneralSlots:
    async def test_generates_sessions_from_window(self, db, student, professor, course, enrolled):
        """GENERAL type: windows → auto-creates ConsultationSession rows."""
        await add_windows_all_days(db, professor.id)

        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.general,
            group_size=1,
            student_id=student.id,
        )

        assert len(slots) > 0
        assert all(s.consultation_type == ConsultationType.general for s in slots)

    async def test_blocked_during_exam_period(self, db, student, professor, course, enrolled):
        """GENERAL blocked when today falls inside an exam period."""
        today = date.today()
        db.add(ExamPeriod(date_from=today - timedelta(days=1), date_to=today + timedelta(days=5), name="Exam"))
        await db.flush()
        await add_windows_all_days(db, professor.id)

        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.general,
            group_size=1,
            student_id=student.id,
        )

        assert slots == []

    async def test_not_enrolled_raises(self, db, student, professor, course):
        """No CourseStudent row → ValueError."""
        await add_windows_all_days(db, professor.id)

        with pytest.raises(ValueError, match="Not enrolled"):
            await slot_service.get_free_slots(
                db,
                professor_id=professor.id,
                course_id=course.id,
                ctype=ConsultationType.general,
                group_size=1,
                student_id=student.id,
            )

    async def test_full_sessions_excluded(self, db, student, professor, course, enrolled):
        """Session at full capacity not returned."""
        await add_windows_all_days(db, professor.id)

        # First call creates the session row
        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.general,
            group_size=1,
            student_id=student.id,
        )
        assert slots

        # Fill the first slot
        first = slots[0]
        first.capacity = 1
        db.add(active_booking(student.id, first.id, group_size=1))
        await db.flush()

        slots2 = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.general,
            group_size=1,
            student_id=student.id,
        )

        assert first not in slots2


class TestPreparationSlots:
    async def test_only_announced_returned(self, db, student, professor, course, enrolled):
        """PREPARATION: windows don't generate slots; only announced sessions count."""
        await add_windows_all_days(db, professor.id)

        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.preparation,
            group_size=1,
            student_id=student.id,
        )
        assert slots == []

    async def test_announced_session_returned(self, db, student, professor, course, enrolled):
        """PREPARATION: professor-announced session is returned."""
        cs = future_session(professor.id, course.id, ConsultationType.preparation, announced=True)
        db.add(cs)
        await db.flush()

        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.preparation,
            group_size=1,
            student_id=student.id,
        )

        assert len(slots) == 1
        assert slots[0].id == cs.id

    async def test_not_announced_excluded(self, db, student, professor, course, enrolled):
        """PREPARATION: session with announced_by_professor=False is not returned."""
        cs = future_session(professor.id, course.id, ConsultationType.preparation, announced=False)
        db.add(cs)
        await db.flush()

        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.preparation,
            group_size=1,
            student_id=student.id,
        )

        assert slots == []

    async def test_full_announced_excluded(self, db, student, professor, course, enrolled):
        """PREPARATION: announced but full session not in free slots."""
        cs = future_session(professor.id, course.id, ConsultationType.preparation, announced=True, capacity=1)
        db.add(cs)
        await db.flush()
        db.add(active_booking(student.id, cs.id))
        await db.flush()

        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.preparation,
            group_size=1,
            student_id=student.id,
        )
        assert slots == []


class TestGradedWorkReviewSlots:
    async def test_only_announced_returned(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.graded_work_review, announced=True)
        db.add(cs)
        await db.flush()

        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.graded_work_review,
            group_size=1,
            student_id=student.id,
        )

        assert len(slots) == 1

    async def test_no_announced_empty(self, db, student, professor, course, enrolled):
        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.graded_work_review,
            group_size=1,
            student_id=student.id,
        )
        assert slots == []


class TestThesisSlots:
    async def test_no_application_raises(self, db, student, professor, course, enrolled):
        await add_windows_all_days(db, professor.id, wtype=WindowType.thesis)

        with pytest.raises(ValueError, match="No active thesis supervision"):
            await slot_service.get_free_slots(
                db,
                professor_id=professor.id,
                course_id=None,
                ctype=ConsultationType.thesis,
                group_size=1,
                student_id=student.id,
            )

    async def test_pending_application_does_not_return_slots(self, db, student, professor, course, enrolled):
        db.add(ThesisApplication(
            student_id=student.id,
            professor_id=professor.id,
            status=ThesisApplicationStatus.pending,
        ))
        await add_windows_all_days(db, professor.id, wtype=WindowType.thesis)
        await db.flush()

        with pytest.raises(ValueError, match="No active thesis supervision"):
            await slot_service.get_free_slots(
                db,
                professor_id=professor.id,
                course_id=None,
                ctype=ConsultationType.thesis,
                group_size=1,
                student_id=student.id,
            )

    async def test_active_application_returns_slots(self, db, student, professor, course, enrolled):
        db.add(ThesisApplication(
            student_id=student.id,
            professor_id=professor.id,
            status=ThesisApplicationStatus.active,
        ))
        await add_windows_all_days(db, professor.id, wtype=WindowType.thesis)
        await db.flush()

        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=None,
            ctype=ConsultationType.thesis,
            group_size=1,
            student_id=student.id,
        )

        assert len(slots) > 0


class TestGetFullSessions:
    async def test_returns_full_announced_sessions(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general, announced=True, capacity=1)
        db.add(cs)
        await db.flush()
        db.add(active_booking(student.id, cs.id))
        await db.flush()

        full = await slot_service.get_full_sessions(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.general,
        )

        assert len(full) == 1
        assert full[0].id == cs.id

    async def test_not_full_not_returned(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general, announced=True, capacity=5)
        db.add(cs)
        await db.flush()
        db.add(active_booking(student.id, cs.id))
        await db.flush()

        full = await slot_service.get_full_sessions(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.general,
        )

        assert full == []


class TestAvailableTypesExamPeriod:
    def test_exam_period_includes_preparation_not_general(self):
        """Phase 1: preparation disabled, only review and thesis during exam period."""
        today = date.today()
        types = slot_service.get_available_types(today, exam_period=True)
        assert ConsultationType.preparation not in types  # Phase 1: disabled
        assert ConsultationType.general not in types
        assert ConsultationType.thesis in types
        assert ConsultationType.graded_work_review in types

    def test_outside_exam_includes_general(self):
        """Phase 1: preparation disabled, general + review + thesis available."""
        today = date.today()
        types = slot_service.get_available_types(today, exam_period=False)
        assert ConsultationType.general in types
        assert ConsultationType.preparation not in types  # Phase 1: disabled
