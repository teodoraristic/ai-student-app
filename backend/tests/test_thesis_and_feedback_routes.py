"""Route-level tests for thesis lifecycle and feedback gating."""

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend.db.models import (
    Booking,
    BookingStatus,
    ConsultationType,
    CourseProfessor,
    CourseStudent,
    CourseStudentStatus,
    Feedback,
    ThesisApplication,
    ThesisApplicationStatus,
    UserRole,
)
from backend.routers.professor import ThesisRespond, thesis_respond
from backend.routers.shared import FeedbackBody, post_feedback
from backend.routers.student import ThesisApplyBody, thesis_apply, thesis_cancel, thesis_my

from .conftest import _user, future_session


class TestThesisLifecycle:
    async def test_apply_rejects_non_final_year_student(self, db, professor, course):
        frosh = _user(UserRole.student, "Bob", "Fresh", is_final_year=False)
        db.add(frosh)
        await db.flush()
        db.add(CourseProfessor(professor_id=professor.id, course_id=course.id, academic_year="2025/2026"))
        db.add(
            CourseStudent(
                student_id=frosh.id,
                course_id=course.id,
                academic_year="2025/2026",
                status=CourseStudentStatus.active,
            )
        )
        await db.flush()

        with pytest.raises(HTTPException) as exc:
            await thesis_apply(
                ThesisApplyBody(professor_id=professor.id, topic_description="Topic"),
                db=db,
                user=frosh,
            )
        assert exc.value.status_code == 400
        assert "final-year" in (exc.value.detail or "").lower()

    async def test_cancel_pending_application(self, db, student, professor, enrolled):
        app = ThesisApplication(
            student_id=student.id,
            professor_id=professor.id,
            topic_description="Distributed systems",
            status=ThesisApplicationStatus.pending,
        )
        db.add(app)
        await db.flush()

        payload = await thesis_cancel(db=db, user=student)

        assert payload == {"ok": True}
        remaining = await db.scalar(select(ThesisApplication).where(ThesisApplication.id == app.id))
        assert remaining is None

    async def test_apply_rejects_second_pending_application(self, db, student, professor, course, enrolled):
        other_prof = _user(UserRole.professor, "Mila", "Jovanovic")
        db.add(other_prof)
        await db.flush()
        db.add(CourseProfessor(professor_id=other_prof.id, course_id=course.id, academic_year="2025/2026"))
        db.add(
            ThesisApplication(
                student_id=student.id,
                professor_id=professor.id,
                topic_description="Distributed systems",
                status=ThesisApplicationStatus.pending,
            )
        )
        await db.flush()

        with pytest.raises(HTTPException, match="Cancel your current pending thesis application"):
            await thesis_apply(
                ThesisApplyBody(professor_id=other_prof.id, topic_description="Another topic"),
                db=db,
                user=student,
            )

    async def test_accept_sets_student_thesis_professor(self, db, student, professor, enrolled):
        app = ThesisApplication(
            student_id=student.id,
            professor_id=professor.id,
            topic_description="Distributed systems",
            status=ThesisApplicationStatus.pending,
        )
        db.add(app)
        await db.flush()

        payload = await thesis_respond(
            app_id=app.id,
            body=ThesisRespond(accept=True),
            db=db,
            user=professor,
        )

        assert payload == {"ok": True}
        assert student.thesis_professor_id == professor.id
        assert app.status == ThesisApplicationStatus.active

    async def test_my_application_prefers_active_over_later_rejected(self, db, student, professor, enrolled):
        other_prof = _user(UserRole.professor, "Mila", "Jovanovic")
        db.add(other_prof)
        await db.flush()

        active = ThesisApplication(
            student_id=student.id,
            professor_id=professor.id,
            topic_description="Accepted topic",
            status=ThesisApplicationStatus.active,
        )
        rejected = ThesisApplication(
            student_id=student.id,
            professor_id=other_prof.id,
            topic_description="Rejected topic",
            status=ThesisApplicationStatus.rejected,
        )
        db.add(active)
        db.add(rejected)
        student.thesis_professor_id = professor.id
        await db.flush()

        payload = await thesis_my(db=db, user=student)

        assert payload["professor_id"] == professor.id
        assert payload["status"] == ThesisApplicationStatus.active.value


class TestFeedbackRules:
    async def test_feedback_requires_attended_booking(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general)
        db.add(cs)
        await db.flush()
        booking = Booking(
            student_id=student.id,
            session_id=cs.id,
            status=BookingStatus.cancelled,
            group_size=1,
        )
        db.add(booking)
        await db.flush()

        with pytest.raises(HTTPException, match="attended consultations"):
            await post_feedback(
                booking_id=booking.id,
                body=FeedbackBody(rating=5, comment="Great"),
                db=db,
                user=student,
            )

        saved = await db.scalar(select(Feedback).where(Feedback.booking_id == booking.id))
        assert saved is None


class TestProfessorHall:
    async def test_thesis_professors_includes_hall(self, db, professor, course, enrolled, student):
        """Test that thesis_professors endpoint includes hall information."""
        from sqlalchemy import select

        from backend.routers.student import thesis_professors
        from backend.db.models import ProfessorProfile

        profile = await db.scalar(select(ProfessorProfile).where(ProfessorProfile.user_id == professor.id))
        assert profile is not None
        profile.hall = "Test Hall"
        await db.flush()

        result = await thesis_professors(db, student)

        prof_data = next(p for p in result if p["professor_id"] == professor.id)
        assert prof_data["hall"] == "Test Hall"
        assert "department" in prof_data
        assert "courses" in prof_data and len(prof_data["courses"]) >= 1
        assert "consultation_regular_hours" in prof_data
        assert "consultation_thesis_hours" in prof_data
        assert isinstance(prof_data["consultation_regular_hours"], list)
