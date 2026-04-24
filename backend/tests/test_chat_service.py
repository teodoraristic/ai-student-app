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

    async def test_topic_answer_accepted_directly_without_about_keyword(
        self, db, student, professor, course, enrolled
    ):
        """Regression: bot asked for topic, student answered 'recursion' — must accept, not loop."""
        await add_windows_all_days(db, professor.id)

        # Bot asks for topic (student has professor + course + general type but no task)
        reply1 = await chat_service.process(
            f"I need help with {professor.first_name} {professor.last_name} for {course.name}",
            student.id,
            db,
        )
        assert "topic or task" in reply1["message"].lower()
        assert reply1["phase"] == "collect"

        # Student replies with bare topic name — no "about" keyword
        reply2 = await chat_service.process("recursion", student.id, db)

        # Should NOT repeat the topic question
        assert "topic or task" not in reply2["message"].lower()
        # Should proceed to slot selection
        assert reply2["phase"] == "pick_slot"
        assert len(reply2.get("slots", [])) > 0


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
    async def test_thesis_booking_with_active_thesis_no_slots(self, db, student, professor, course, enrolled):
        """Test that booking thesis consultation without available slots shows proper message."""
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

        # Try to book thesis consultation (no windows set, so no slots)
        reply = await chat_service.process(
            f"I need thesis consultation with {professor.first_name} {professor.last_name}",
            student.id,
            db,
        )

        # Should show message about no slots available
        assert "no thesis consultation slots" in reply["message"].lower()
        assert reply["phase"] == "done"

    async def test_general_intent_overrides_thesis_state(self, db, student, professor, course, enrolled):
        """Regression: general consultation keywords should override stale thesis state."""
        from backend.services.chat_service import get_or_create_conversation
        from backend.db.models import ThesisApplication, ThesisApplicationStatus

        await add_windows_all_days(db, professor.id)

        # Create pending thesis application
        app = ThesisApplication(
            student_id=student.id,
            professor_id=professor.id,
            topic_description="Test thesis",
            status=ThesisApplicationStatus.pending,
        )
        db.add(app)
        await db.flush()

        # Simulate student having old conversation state with thesis type
        conv = await get_or_create_conversation(db, student.id)
        conv.state = {
            "professor": f"{professor.first_name} {professor.last_name}",
            "professor_id": professor.id,
            "consultation_type": "THESIS",
            "phase": "collect",
            "failed_parse_count": 0,
        }
        await db.flush()

        # Student clicks "General consultation" suggestion and sends message
        reply = await chat_service.process(
            "I need help with a course topic",
            student.id,
            db,
        )

        # Should show general consultation options, not thesis waiting message
        assert "waiting for the professor's decision" not in reply["message"].lower()

    async def test_general_intent_does_not_show_thesis_status_for_active_thesis(self, db, student, professor, course, enrolled):
        """Student with ACTIVE thesis should not see 'waiting' message when requesting general consultation."""
        from backend.services.chat_service import get_or_create_conversation
        from backend.db.models import ThesisApplication, ThesisApplicationStatus

        await add_windows_all_days(db, professor.id)

        # Create ACTIVE (approved) thesis application
        app = ThesisApplication(
            student_id=student.id,
            professor_id=professor.id,
            topic_description="Test thesis",
            status=ThesisApplicationStatus.active,
        )
        db.add(app)
        await db.flush()

        # Student has stale state without professor info
        conv = await get_or_create_conversation(db, student.id)
        conv.state = {}
        await db.flush()

        # Student sends general request mentioning this professor and course
        reply = await chat_service.process(
            f"I need help with a course topic with {professor.first_name} {professor.last_name} for {course.name}",
            student.id,
            db,
        )

        # Should NOT show "waiting" message since thesis is active, not pending
        assert "waiting for the professor's decision" not in reply["message"].lower()

    async def test_bug_general_button_classified_as_thesis(self, db, student, professor, course, enrolled):
        """Bug: clicking 'General consultation' button but bot replies with thesis message."""
        from backend.services.chat_service import get_or_create_conversation
        from backend.db.models import ThesisApplication, ThesisApplicationStatus

        await add_windows_all_days(db, professor.id)

        # Student already has active thesis (approved)
        app = ThesisApplication(
            student_id=student.id,
            professor_id=professor.id,
            topic_description="My approved thesis",
            status=ThesisApplicationStatus.active,
        )
        db.add(app)
        await db.flush()

        # Student also has PENDING thesis application with same professor (somehow)
        # This might be edge case or from previous attempt
        pending = ThesisApplication(
            student_id=student.id,
            professor_id=professor.id,
            topic_description="Old pending application",
            status=ThesisApplicationStatus.pending,
        )
        db.add(pending)
        await db.flush()

        # Student clicks "General consultation" suggestion → "I need help with a course topic"
        reply = await chat_service.process(
            f"I need help with a course topic for {course.name}",
            student.id,
            db,
        )

        # BUG: bot should NOT show "waiting" message for general request
        # even though pending thesis exists
        print(f"\nReply message: {reply['message']}")
        assert "waiting for the professor's decision" not in reply["message"].lower()

    async def test_thesis_supervision_not_allowed_through_chatbot(self, db, student, professor):
        """Thesis supervision申请 must go through Thesis page, not chatbot."""
        # Student tries to request thesis supervision through chatbot
        reply = await chat_service.process(
            f"I want thesis supervision with {professor.first_name} {professor.last_name}",
            student.id,
            db,
        )

        # Should reject thesis supervision申请
        msg = reply["message"].lower()
        assert "thesis" in msg and ("thesis page" in msg or "thesis supervision申请" in msg.lower())
        assert reply["phase"] == "done"

    async def test_thesis_consultation_rejected_without_active_thesis(self, db, student, professor):
        """Cannot request thesis consultation without active thesis."""
        # Try to request thesis consultation without having active thesis
        reply = await chat_service.process(
            f"I need thesis consultation with {professor.first_name} {professor.last_name}",
            student.id,
            db,
        )

        # Should be rejected with message about needing active thesis
        msg = reply["message"].lower()
        assert "thesis" in msg and "page" in msg
        assert reply["phase"] == "done"
