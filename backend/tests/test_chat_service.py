"""Tests for chat state transitions and context clearing."""

from sqlalchemy import select

from backend.db.models import Conversation
from backend.services import chat_service

from .conftest import add_windows_all_days


class TestChatState:
    async def test_terminal_response_clears_context_for_next_request(self, db, student, professor, course, enrolled):
        first = await chat_service.process(
            "I want to review my grade",
            student.id,
            db,
        )

        assert "No graded work review session has been announced yet." in first["message"]

        conv = await db.scalar(select(Conversation).where(Conversation.student_id == student.id))
        assert conv is not None
        assert conv.state == {}

        await add_windows_all_days(db, professor.id)

        second = await chat_service.process(
            "I need help about SQL joins",
            student.id,
            db,
        )

        assert second["message"] != first["message"]
        assert second["phase"] == "pick_slot"
        assert len(second["slots"]) > 0

        await db.refresh(conv)
        assert conv.state.get("consultation_type") == "GENERAL"

    async def test_general_booking_flow_no_longer_asks_about_group_size(
        self,
        db,
        student,
        professor,
        course,
        enrolled,
    ):
        await add_windows_all_days(db, professor.id)

        reply = await chat_service.process(
            "I need help about SQL joins",
            student.id,
            db,
        )

        assert "group of you" not in reply["message"]
        assert reply["phase"] == "pick_slot"
        assert len(reply["slots"]) > 0


class TestPreparationPreferredTimes:
    async def test_preparation_vote_includes_preferred_times(self, db, student, professor, course, enrolled):
        """Test that preparation is disabled in Phase 1 — user gets 'not available yet' message."""
        from backend.db.models import AcademicEvent, AcademicEventType
        from datetime import date, timedelta

        # Create an upcoming exam
        exam = AcademicEvent(
            course_id=course.id,
            event_type=AcademicEventType.exam,
            event_date=date.today() + timedelta(days=10),
            name="Test Exam",
        )
        db.add(exam)
        await db.flush()

        # Start preparation conversation — should be rejected in Phase 1
        reply1 = await chat_service.process(
            f"I want to book preparation with {professor.first_name} {professor.last_name}",
            student.id,
            db,
        )
        # Phase 1: preparation keywords removed, so chatbot asks for consultation type
        assert "What is the consultation about?" in reply1["message"]

        # Manually provide "preparation" via structured input (simulating if user somehow specifies it)
        # This should trigger the Phase 1 rejection
        reply2 = await chat_service.process(
            "PREPARATION",
            student.id,
            db,
            structured={
                "professor_id": professor.id,
                "course_id": course.id,
                "consultation_type": "PREPARATION",
            },
        )
        assert "not available yet" in reply2["message"].lower()


class TestThesisBugFix:
    async def test_thesis_booking_with_active_thesis_shows_proper_message(self, db, student, professor, course, enrolled):
        """Test that booking thesis with active thesis shows correct message."""
        from backend.db.models import ThesisApplication, ThesisApplicationStatus

        # Create active thesis application
        app = ThesisApplication(
            student_id=student.id,
            professor_id=professor.id,
            topic_description="Test thesis",
            status=ThesisApplicationStatus.active,
        )
        db.add(app)
        await db.flush()

        # Try to book thesis consultation
        reply1 = await chat_service.process(
            f"I want to book a consultation with {professor.first_name} {professor.last_name}",
            student.id,
            db,
        )
        reply2 = await chat_service.process("thesis", student.id, db)

        assert "You have an active thesis with this professor" in reply2["message"]
        assert "thesis page" in reply2["message"]
