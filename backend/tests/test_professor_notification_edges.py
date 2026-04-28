"""Edge cases: professor must teach course; notifications respect academic year and enrollment status."""

from datetime import date, time, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from backend.db.models import (
    CourseProfessor,
    CourseStudent,
    CourseStudentStatus,
    Notification,
    UserRole,
)
from backend.routers.professor import (
    AnnounceGradedReviewBody,
    AnnouncementCreate,
    AnnouncePreparationBody,
    announce_graded_review,
    announce_preparation,
    create_announcement,
)
from .conftest import _user


class TestProfessorMustTeachCourse:
    async def test_announce_preparation_403_without_assignment(self, db, professor, course, student):
        """Professor cannot announce prep for a course they are not assigned to."""
        db.add(
            CourseStudent(
                student_id=student.id,
                course_id=course.id,
                academic_year="2025/2026",
                status=CourseStudentStatus.active,
            )
        )
        await db.flush()
        body = AnnouncePreparationBody(
            course_id=course.id,
            date=date.today() + timedelta(days=10),
            time_from=time(10, 0),
            time_to=time(11, 0),
        )
        with pytest.raises(HTTPException) as exc:
            await announce_preparation(body, db, professor)
        assert exc.value.status_code == 403

    async def test_announce_graded_review_403_without_assignment(self, db, professor, course, student):
        db.add(
            CourseStudent(
                student_id=student.id,
                course_id=course.id,
                academic_year="2025/2026",
                status=CourseStudentStatus.active,
            )
        )
        await db.flush()
        body = AnnounceGradedReviewBody(
            course_id=course.id,
            date=date.today() + timedelta(days=10),
            time_from=time(14, 0),
            time_to=time(15, 0),
        )
        with pytest.raises(HTTPException) as exc:
            await announce_graded_review(body, db, professor)
        assert exc.value.status_code == 403


class TestNotificationAcademicYearAndStatus:
    async def test_announcement_only_notifies_matching_academic_year(
        self, db, professor, course, student
    ):
        """Students enrolled under a year the professor does not teach get no announcement."""
        db.add(CourseProfessor(professor_id=professor.id, course_id=course.id, academic_year="2025/2026"))
        other_year_student = _user(UserRole.student, "Old", "Year")
        db.add(other_year_student)
        await db.flush()
        db.add(
            CourseStudent(
                student_id=student.id,
                course_id=course.id,
                academic_year="2025/2026",
                status=CourseStudentStatus.active,
            )
        )
        db.add(
            CourseStudent(
                student_id=other_year_student.id,
                course_id=course.id,
                academic_year="2023/2024",
                status=CourseStudentStatus.active,
            )
        )
        await db.flush()

        body = AnnouncementCreate(
            course_id=course.id,
            announcement_type="general",
            title="Syllabus",
            message="Check the portal.",
        )
        await create_announcement(body, db, professor)

        n_current = await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == student.id, Notification.notification_type == "announcement")
        )
        n_other = await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == other_year_student.id,
                Notification.notification_type == "announcement",
            )
        )
        assert int(n_current or 0) == 1
        assert int(n_other or 0) == 0

    async def test_announcement_skips_withdrawn_enrollment(self, db, professor, course, student):
        db.add(CourseProfessor(professor_id=professor.id, course_id=course.id, academic_year="2025/2026"))
        db.add(
            CourseStudent(
                student_id=student.id,
                course_id=course.id,
                academic_year="2025/2026",
                status=CourseStudentStatus.withdrawn,
            )
        )
        await db.flush()

        body = AnnouncementCreate(
            course_id=course.id,
            announcement_type="general",
            title="Exam",
            message="Details inside.",
        )
        await create_announcement(body, db, professor)

        n = await db.scalar(
            select(func.count()).select_from(Notification).where(Notification.user_id == student.id)
        )
        assert int(n or 0) == 0

    async def test_announcement_notifies_multiple_years_when_professor_teaches_both(
        self, db, professor, course
    ):
        db.add(
            CourseProfessor(professor_id=professor.id, course_id=course.id, academic_year="2024/2025")
        )
        db.add(
            CourseProfessor(professor_id=professor.id, course_id=course.id, academic_year="2025/2026")
        )
        s1 = _user(UserRole.student, "Y1", "Student")
        s2 = _user(UserRole.student, "Y2", "Student")
        db.add(s1)
        db.add(s2)
        await db.flush()
        db.add(
            CourseStudent(
                student_id=s1.id,
                course_id=course.id,
                academic_year="2024/2025",
                status=CourseStudentStatus.active,
            )
        )
        db.add(
            CourseStudent(
                student_id=s2.id,
                course_id=course.id,
                academic_year="2025/2026",
                status=CourseStudentStatus.active,
            )
        )
        await db.flush()

        body = AnnouncementCreate(
            course_id=course.id,
            announcement_type="preparation",
            title="Both cohorts",
            message="Hello.",
        )
        await create_announcement(body, db, professor)

        c1 = await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == s1.id, Notification.notification_type == "announcement")
        )
        c2 = await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == s2.id, Notification.notification_type == "announcement")
        )
        assert int(c1 or 0) == 1
        assert int(c2 or 0) == 1

    async def test_preparation_announce_succeeds_with_zero_active_students(self, db, professor, course):
        """Professor may announce even when nobody is actively enrolled (no in-app notifications)."""
        db.add(CourseProfessor(professor_id=professor.id, course_id=course.id, academic_year="2025/2026"))
        await db.flush()
        body = AnnouncePreparationBody(
            course_id=course.id,
            date=date.today() + timedelta(days=14),
            time_from=time(9, 0),
            time_to=time(10, 0),
        )
        out = await announce_preparation(body, db, professor)
        assert "id" in out


class TestWrongProfessorCannotUsePeerCourse:
    async def test_other_professor_cannot_announce_on_course(self, db, professor, course, enrolled, student):
        intruder = _user(UserRole.professor, "X", "Stranger")
        db.add(intruder)
        await db.flush()

        body = AnnouncementCreate(
            course_id=course.id,
            announcement_type="general",
            title="Spam",
            message="Should not send.",
        )
        with pytest.raises(HTTPException) as exc:
            await create_announcement(body, db, intruder)
        assert exc.value.status_code == 403
