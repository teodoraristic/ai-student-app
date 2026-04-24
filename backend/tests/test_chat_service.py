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
        """Natural-language preparation intent is recognized and deferred in Phase 1."""
        from backend.db.models import AcademicEvent, AcademicEventType
        from datetime import date, timedelta

        exam = AcademicEvent(
            course_id=course.id,
            event_type=AcademicEventType.exam,
            event_date=date.today() + timedelta(days=10),
            name="Test Exam",
        )
        db.add(exam)
        await db.flush()

        reply1 = await chat_service.process(
            f"I want to book preparation with {professor.first_name} {professor.last_name}",
            student.id,
            db,
        )
        assert "not available yet" in reply1["message"].lower()

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


class TestPreparationGuardRegression:
    async def test_question_keyword_never_emits_preparation_deferral(
        self, db, student, professor, course, enrolled
    ):
        """Regression: 'question' must map to GENERAL, not stale PREPARATION state."""
        from backend.services.chat_service import get_or_create_conversation

        await add_windows_all_days(db, professor.id)
        conv = await get_or_create_conversation(db, student.id)
        conv.state = {
            "professor": f"{professor.first_name} {professor.last_name}",
            "professor_id": professor.id,
            "consultation_type": "PREPARATION",
            "phase": "collect",
            "failed_parse_count": 0,
        }
        await db.flush()

        reply = await chat_service.process(
            "I want to book profesor Markovic for question number 3",
            student.id,
            db,
        )
        assert "not available yet" not in reply["message"].lower()
        msg = reply["message"].lower()
        assert "which course" in msg or "topic or task" in msg

    async def test_exam_prep_keywords_emit_preparation_deferral(self, db, student, professor, course, enrolled):
        reply = await chat_service.process(
            f"I need exam prep with {professor.first_name} {professor.last_name} for {course.name}",
            student.id,
            db,
        )
        assert "not available yet" in reply["message"].lower()

    async def test_prepare_alone_first_message_emits_preparation_deferral(self, db, student, professor, course, enrolled):
        """Bare 'prepare' / prep phrasing should classify as preparation and hit the deferral once complete."""
        reply = await chat_service.process(
            f"prepare for the exam with {professor.first_name} {professor.last_name} {course.name}",
            student.id,
            db,
        )
        assert "not available yet" in reply["message"].lower()


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
