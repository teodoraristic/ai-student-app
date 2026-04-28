"""Tests for slot_service — slot generation, filtering, exam period rules."""

from datetime import date, time, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    BlockedDate,
    Booking,
    BookingStatus,
    ConsultationSession,
    ConsultationType,
    ConsultationWindow,
    ExamPeriod,
    SessionFormat,
    SessionStatus,
    SystemConfig,
    ThesisApplication,
    ThesisApplicationStatus,
    User,
    WindowType,
)
from backend.services import slot_service

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

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

    async def test_general_slots_not_blocked_by_exam_period(self, db, student, professor, course, enrolled):
        """GENERAL consultations are listed even when an academic exam period includes today."""
        from backend.dates import utc_today

        today = utc_today()
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

        assert len(slots) > 0

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
        row = await db.scalar(
            select(SystemConfig).where(SystemConfig.key == "general_consultation_slot_capacity")
        )
        if row:
            row.value = "1"
        else:
            db.add(
                SystemConfig(
                    key="general_consultation_slot_capacity",
                    value="1",
                    description="test",
                )
            )
        await db.flush()

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
        """GRADED_WORK_REVIEW announced sessions are split into 15-min sub-slots."""
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

        # Phase 1: 1-hour announced session (10:00-11:00) is split into 4 x 15-min sub-slots
        assert len(slots) == 4
        assert all(s.consultation_type == ConsultationType.graded_work_review for s in slots)

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

    async def test_duplicate_active_thesis_rows_still_return_slots(
        self, db, student, professor, course, enrolled
    ):
        """Multiple active ThesisApplication rows must not crash get_free_slots (no scalar())."""
        db.add(
            ThesisApplication(
                student_id=student.id,
                professor_id=professor.id,
                topic_description="first",
                status=ThesisApplicationStatus.active,
            )
        )
        db.add(
            ThesisApplication(
                student_id=student.id,
                professor_id=professor.id,
                topic_description="second",
                status=ThesisApplicationStatus.active,
            )
        )
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


class TestAvailableTypes:
    def test_always_includes_general_review_thesis(self):
        """Phase 1: preparation disabled; general is offered regardless of calendar."""
        today = date.today()
        types = slot_service.get_available_types(today)
        assert ConsultationType.preparation not in types
        assert ConsultationType.general in types
        assert ConsultationType.thesis in types
        assert ConsultationType.graded_work_review in types


class TestSubSlotSplitting:
    """Phase 1: Test 15-min and 60-min sub-slot generation."""

    async def test_general_window_yields_15min_subslots(self, db, student, professor, course, enrolled):
        """Test that a 2-hour GENERAL window generates 8 sub-slots of 15 minutes each."""
        from datetime import time
        
        window = ConsultationWindow(
            professor_id=professor.id,
            day_of_week="monday",
            time_from=time(12, 0),
            time_to=time(14, 0),
            window_type=WindowType.regular,
            slot_duration_minutes=15,
        )
        db.add(window)
        await db.flush()
        
        # Get the next Monday
        today = date.today()
        days_ahead = 0 - today.weekday()  # Monday is 0
        if days_ahead <= 0:
            days_ahead += 7
        next_monday = today + timedelta(days=days_ahead)
        
        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.general,
            group_size=1,
            student_id=student.id,
            next_weeks=2,
        )
        
        # Filter for just the next monday
        monday_slots = [s for s in slots if s.session_date == next_monday]
        
        assert len(monday_slots) == 8  # 2 hours = 8 x 15-min slots
        # Verify times: 12:00-12:15, 12:15-12:30, ..., 13:45-14:00
        assert monday_slots[0].time_from == time(12, 0)
        assert monday_slots[0].time_to == time(12, 15)
        assert monday_slots[7].time_from == time(13, 45)
        assert monday_slots[7].time_to == time(14, 0)

    async def test_thesis_window_yields_60min_subslots(self, db, student, professor, course, enrolled):
        """Test that a 2-hour THESIS window generates 2 sub-slots of 60 minutes each."""
        from datetime import time
        
        # First, create an active thesis application
        thesis = ThesisApplication(
            student_id=student.id,
            professor_id=professor.id,
            topic_description="Test thesis",
            status=ThesisApplicationStatus.active,
        )
        db.add(thesis)
        
        window = ConsultationWindow(
            professor_id=professor.id,
            day_of_week="tuesday",
            time_from=time(12, 0),
            time_to=time(14, 0),
            window_type=WindowType.thesis,
            slot_duration_minutes=60,
        )
        db.add(window)
        await db.flush()
        
        # Get the next Tuesday
        today = date.today()
        days_ahead = 1 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_tuesday = today + timedelta(days=days_ahead)
        
        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=None,
            ctype=ConsultationType.thesis,
            group_size=1,
            student_id=student.id,
            next_weeks=2,
        )
        
        tuesday_slots = [s for s in slots if s.session_date == next_tuesday]
        
        assert len(tuesday_slots) == 2  # 2 hours = 2 x 60-min slots
        assert tuesday_slots[0].time_from == time(12, 0)
        assert tuesday_slots[0].time_to == time(13, 0)
        assert tuesday_slots[1].time_from == time(13, 0)
        assert tuesday_slots[1].time_to == time(14, 0)

    async def test_past_subslots_today_skipped(self, db, student, professor, course, enrolled):
        """Test that past sub-slots on today are skipped but future ones are returned."""
        from datetime import datetime, time
        
        now = datetime.now()
        # Create window that spans past and future on today
        window_start = time(now.hour - 1 if now.hour > 0 else 0, 0)
        window_end = time(now.hour + 2 if now.hour < 22 else 23, 59)
        
        wd = WEEKDAYS[date.today().weekday()]
        
        window = ConsultationWindow(
            professor_id=professor.id,
            day_of_week=wd,
            time_from=window_start,
            time_to=window_end,
            window_type=WindowType.regular,
            slot_duration_minutes=15,
        )
        db.add(window)
        await db.flush()
        
        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.general,
            group_size=1,
            student_id=student.id,
            next_weeks=1,
        )
        
        today_slots = [s for s in slots if s.session_date == date.today()]
        
        # All returned slots should be in the future
        for s in today_slots:
            assert s.time_to > now.time(), f"Slot {s.time_from}-{s.time_to} should be after {now.time()}"

    async def test_booking_only_takes_one_subslot(self, db, student, professor, course, enrolled):
        """Test that booking one 15-min sub-slot leaves other sub-slots free."""
        from datetime import time

        row = await db.scalar(
            select(SystemConfig).where(SystemConfig.key == "general_consultation_slot_capacity")
        )
        if row:
            row.value = "1"
        else:
            db.add(
                SystemConfig(
                    key="general_consultation_slot_capacity",
                    value="1",
                    description="test",
                )
            )
        await db.flush()

        window = ConsultationWindow(
            professor_id=professor.id,
            day_of_week="wednesday",
            time_from=time(10, 0),
            time_to=time(11, 0),
            window_type=WindowType.regular,
            slot_duration_minutes=15,
        )
        db.add(window)
        await db.flush()
        
        # Get free slots
        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.general,
            group_size=1,
            student_id=student.id,
            next_weeks=2,
        )
        
        # Find the first Wednesday's slots
        wednesday_slots = [s for s in slots if s.session_date.weekday() == 2]
        first_wednesday = wednesday_slots[0].session_date if wednesday_slots else None
        assert first_wednesday is not None
        
        first_wednesday_slots = [s for s in wednesday_slots if s.session_date == first_wednesday]
        assert len(first_wednesday_slots) == 4  # 1 hour = 4 x 15-min
        
        # Book the first sub-slot
        first_slot = first_wednesday_slots[0]
        booking = Booking(
            student_id=student.id,
            session_id=first_slot.id,
            group_size=1,
            status=BookingStatus.active,
        )
        db.add(booking)
        await db.flush()
        
        # Get free slots again
        slots_after = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.general,
            group_size=1,
            student_id=student.id,
            next_weeks=2,
        )
        
        # Filter for the same Wednesday and time range
        wednesday_slots_after = [
            s for s in slots_after 
            if s.session_date == first_wednesday 
            and s.time_from >= time(10, 0) 
            and s.time_to <= time(11, 0)
        ]
        
        # Should have 3 free slots remaining
        assert len(wednesday_slots_after) == 3
        # First slot should not be in the list
        assert first_slot.id not in [s.id for s in wednesday_slots_after]

    async def test_blocked_date_skips_all_subslots(self, db, student, professor, course, enrolled):
        """Test that blocked dates exclude all sub-slots for that date."""
        from datetime import time
        
        today = date.today()
        days_ahead = 3 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        next_thursday = today + timedelta(days=days_ahead)
        
        window = ConsultationWindow(
            professor_id=professor.id,
            day_of_week="thursday",
            time_from=time(9, 0),
            time_to=time(12, 0),
            window_type=WindowType.regular,
            slot_duration_minutes=15,
        )
        db.add(window)
        
        # Block next Thursday
        blocked = BlockedDate(
            professor_id=professor.id,
            blocked_date=next_thursday,
            reason="Conference",
        )
        db.add(blocked)
        await db.flush()
        
        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.general,
            group_size=1,
            student_id=student.id,
            next_weeks=2,
        )
        
        # Should have no slots for next Thursday
        thursday_slots = [s for s in slots if s.session_date == next_thursday]
        assert len(thursday_slots) == 0

    async def test_general_slots_during_exam_period(self, db, student, professor, course, enrolled):
        """GENERAL slots are returned even when the horizon overlaps an exam period."""
        from datetime import time

        from backend.dates import utc_today

        window = ConsultationWindow(
            professor_id=professor.id,
            day_of_week="friday",
            time_from=time(10, 0),
            time_to=time(12, 0),
            window_type=WindowType.regular,
            slot_duration_minutes=15,
        )
        db.add(window)

        today = utc_today()
        exam = ExamPeriod(
            date_from=today,
            date_to=today + timedelta(weeks=2),
            name="Winter exam period",
        )
        db.add(exam)
        await db.flush()

        slots = await slot_service.get_free_slots(
            db,
            professor_id=professor.id,
            course_id=course.id,
            ctype=ConsultationType.general,
            group_size=1,
            student_id=student.id,
            next_weeks=2,
        )

        assert len(slots) > 0

    async def test_thesis_subslot_requires_active_application(self, db, student, professor, course, enrolled):
        """Test that thesis sub-slot generation requires active ThesisApplication."""
        from datetime import time
        
        window = ConsultationWindow(
            professor_id=professor.id,
            day_of_week="monday",
            time_from=time(14, 0),
            time_to=time(16, 0),
            window_type=WindowType.thesis,
            slot_duration_minutes=60,
        )
        db.add(window)
        await db.flush()
        
        # Try to get slots without an active thesis application
        with pytest.raises(ValueError, match="No active thesis supervision"):
            await slot_service.get_free_slots(
                db,
                professor_id=professor.id,
                course_id=None,
                ctype=ConsultationType.thesis,
                group_size=1,
                student_id=student.id,
                next_weeks=2,
            )
