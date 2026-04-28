"""Tests for chat state transitions and context clearing."""

from datetime import date, time, timedelta

from sqlalchemy import select

from backend.db.models import (
    Booking,
    BookingPriority,
    BookingStatus,
    ConsultationSession,
    ConsultationType,
    Conversation,
    Course,
    CourseProfessor,
    CourseStudent,
    CourseStudentStatus,
    ProfessorProfile,
    Semester,
    SessionFormat,
    SessionStatus,
    SystemConfig,
    UserRole,
)
from backend.services import chat_service
from backend.services.chat_service import _sanitize_state_dict, strip_professor_from_topic_text

from .conftest import _user, add_windows_all_days


class TestStripProfessorFromTopic:
    def test_strip_last_name_ascii_and_phrase(self):
        assert strip_professor_from_topic_text("recursion — markovic", "Ana", "Markovic") == "recursion"
        assert strip_professor_from_topic_text("recursion", "Ana", "Markovic") == "recursion"
        assert strip_professor_from_topic_text("markovic", "Ana", "Markovic") is None
        assert strip_professor_from_topic_text("Ana Markovic about trees", "Ana", "Markovic") == "about trees"

    def test_strip_diacritic_last_name_variant(self):
        assert strip_professor_from_topic_text("graphs — Markovic", "Ana", "Marković") == "graphs"

    async def test_sanitize_state_drops_professor_name_from_topic_fields(self, db, professor):
        """Persisted conversation state (and bookings) must not keep the booked professor's name in topic text."""
        state = {
            "professor_id": professor.id,
            "professor": f"{professor.first_name} {professor.last_name}",
            "task": "recursion",
            "anonymous_question": professor.last_name.lower(),
            "phase": "collect",
        }
        cleaned = await _sanitize_state_dict(db, state)
        assert cleaned["task"] == "recursion"
        assert cleaned.get("anonymous_question") is None


class TestGeneralGroupJoin:
    async def test_second_student_gets_group_join_offer_same_topic(
        self, db, student, professor, course, enrolled
    ):
        """When another student already booked the same prof/course/topic, offer joining that slot."""
        row = await db.scalar(
            select(SystemConfig).where(SystemConfig.key == "general_consultation_slot_capacity")
        )
        if row:
            row.value = "6"
        else:
            db.add(
                SystemConfig(
                    key="general_consultation_slot_capacity",
                    value="6",
                    description="test",
                )
            )
        await db.flush()

        d = date.today() + timedelta(days=5)
        cs = ConsultationSession(
            professor_id=professor.id,
            course_id=course.id,
            consultation_type=ConsultationType.general,
            session_date=d,
            time_from=time(10, 15),
            time_to=time(10, 30),
            format=SessionFormat.in_person,
            status=SessionStatus.confirmed,
            capacity=6,
        )
        db.add(cs)
        await db.flush()
        db.add(
            Booking(
                student_id=student.id,
                session_id=cs.id,
                task="sql joins",
                status=BookingStatus.active,
                group_size=1,
                priority=BookingPriority.normal,
            )
        )
        other = _user(UserRole.student, "Milica", "Simic", is_final_year=True)
        db.add(other)
        await db.flush()
        db.add(
            CourseStudent(
                student_id=other.id,
                course_id=course.id,
                academic_year="2025/2026",
                status=CourseStudentStatus.active,
            )
        )
        await db.flush()

        await add_windows_all_days(db, professor.id, t_from=time(9, 0), t_to=time(12, 0))

        r1 = await chat_service.process(
            f"I need help with {professor.first_name} {professor.last_name} for {course.name}",
            other.id,
            db,
        )
        assert "topic or task" in r1["message"].lower()
        r2 = await chat_service.process("sql joins", other.id, db)
        assert r2.get("phase") == "group_join_offer"
        assert "another student" in r2["message"].lower()
        assert any(
            (c.get("action") or "").startswith("join_group_session:")
            for c in (r2.get("chips") or [])
        )


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
            f"I need help about SQL joins with {professor.first_name} {professor.last_name} for {course.name}",
            student.id,
            db,
        )

        assert second["message"] != first["message"]
        assert second["phase"] == "pick_date"
        assert len(second["slots"]) > 0
        pick = second["slots"][0]["action"]
        assert pick.startswith("pick_date:")
        third = await chat_service.process(pick, student.id, db)
        assert third["phase"] == "pick_time"
        assert len(third["slots"]) > 0
        slot_act = third["slots"][0]["action"]
        assert slot_act.startswith("select_slot:")
        fourth = await chat_service.process(slot_act, student.id, db)
        assert fourth["phase"] == "confirm_booking"
        fifth = await chat_service.process("confirm_booking:yes", student.id, db)
        assert fifth["phase"] == "done"
        assert "Confirmed" in fifth["message"]

        await db.refresh(conv)
        assert conv.state == {}

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
            f"I need help about SQL joins with {professor.first_name} {professor.last_name} for {course.name}",
            student.id,
            db,
        )

        assert "group of you" not in reply["message"]
        assert reply["phase"] == "pick_date"
        assert len(reply["slots"]) > 0

    async def test_general_boilerplate_two_professors_must_ask_which_professor(
        self, db, student, professor, course, enrolled
    ):
        """Regression: 'topic' must not fuzzy-match 'Petrovic' and skip professor choice."""
        other = _user(UserRole.professor, "Petar", "Petrovic")
        db.add(other)
        await db.flush()
        db.add(ProfessorProfile(user_id=other.id, max_thesis_students=5))
        course2 = Course(
            name="Algorithms",
            code="CS202",
            semester=Semester.winter,
            year_of_study=2,
            department="CS",
        )
        db.add(course2)
        await db.flush()
        db.add(
            CourseProfessor(
                professor_id=other.id,
                course_id=course2.id,
                academic_year="2025/2026",
            )
        )
        db.add(
            CourseStudent(
                student_id=student.id,
                course_id=course2.id,
                academic_year="2025/2026",
                status=CourseStudentStatus.active,
            )
        )
        await db.flush()

        reply = await chat_service.process(
            "I need help with a course topic",
            student.id,
            db,
        )
        assert "which professor" in reply["message"].lower()
        assert "topic or task" not in reply["message"].lower()
        assert reply["phase"] == "collect"

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
        assert reply2["phase"] == "pick_date"
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
        assert "no preparation session has been announced" in reply1["message"].lower()

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
        assert "no preparation session has been announced" in reply2["message"].lower()


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
        assert "no preparation session has been announced" not in reply["message"].lower()
        msg = reply["message"].lower()
        assert "which course" in msg or "topic or task" in msg

    async def test_exam_prep_keywords_emit_preparation_deferral(self, db, student, professor, course, enrolled):
        reply = await chat_service.process(
            f"I need exam prep with {professor.first_name} {professor.last_name} for {course.name}",
            student.id,
            db,
        )
        assert "no preparation session has been announced" in reply["message"].lower()

    async def test_prepare_alone_first_message_emits_preparation_deferral(self, db, student, professor, course, enrolled):
        """Bare 'prepare' / prep phrasing should classify as preparation and hit the deferral once complete."""
        reply = await chat_service.process(
            f"prepare for the exam with {professor.first_name} {professor.last_name} {course.name}",
            student.id,
            db,
        )
        assert "no preparation session has been announced" in reply["message"].lower()


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

        # Should show message about no slots available (no weekly windows → no day waitlist chips)
        assert "no thesis consultation slots" in reply["message"].lower()
        assert reply["phase"] == "done"

    async def test_thesis_consultation_skips_professor_when_mentor_approved(
        self, db, student, professor, course, enrolled
    ):
        """Approved thesis mentor is implied — do not prompt among all professors."""
        from backend.db.models import ThesisApplication, ThesisApplicationStatus, WindowType

        db.add(
            ThesisApplication(
                student_id=student.id,
                professor_id=professor.id,
                topic_description="Test thesis",
                status=ThesisApplicationStatus.active,
            )
        )
        student.thesis_professor_id = professor.id
        await db.flush()

        await add_windows_all_days(db, professor.id, wtype=WindowType.thesis)

        reply = await chat_service.process(
            "I need a thesis consultation",
            student.id,
            db,
        )
        assert "which professor" not in reply["message"].lower()
        assert reply["phase"] == "pick_date"
        assert len(reply.get("slots", [])) > 0

    async def test_thesis_consultation_survives_duplicate_conversation_rows(
        self, db, student, professor, course, enrolled
    ):
        """Regression: duplicate Conversation rows must not crash chat (scalar → MultipleResultsFound)."""
        from backend.db.models import ThesisApplication, ThesisApplicationStatus, WindowType

        db.add(
            ThesisApplication(
                student_id=student.id,
                professor_id=professor.id,
                topic_description="Test thesis",
                status=ThesisApplicationStatus.active,
            )
        )
        student.thesis_professor_id = professor.id
        db.add(Conversation(student_id=student.id, state={}))
        db.add(Conversation(student_id=student.id, state={"stale": True}))
        await db.flush()

        await add_windows_all_days(db, professor.id, wtype=WindowType.thesis)

        reply = await chat_service.process(
            "I need a thesis consultation",
            student.id,
            db,
        )
        assert reply["phase"] == "pick_date"
        assert len(reply.get("slots", [])) > 0

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
        assert "thesis" in msg and "page" in msg
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
