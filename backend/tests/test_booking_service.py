"""Tests for booking_service — create, cancel, waitlist promotion."""

from datetime import date, datetime, time, timedelta, UTC

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.models import (
    Booking,
    BookingStatus,
    ConsultationSession,
    ConsultationType,
    SessionFormat,
    SessionStatus,
    ThesisApplication,
    ThesisApplicationStatus,
    User,
    Waitlist,
)
from backend.services import booking_service

from .conftest import active_booking, future_session


class TestCreateBooking:
    async def test_thesis_booking_requires_active_supervision(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.thesis, days_ahead=5)
        db.add(cs)
        await db.flush()

        with pytest.raises(ValueError, match="approved supervision"):
            await booking_service.create_booking(
                db,
                student=student,
                session_id=cs.id,
                task=None,
                anonymous_question=None,
                is_urgent=False,
                group_size=1,
            )

    async def test_success(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general)
        db.add(cs)
        await db.flush()

        b = await booking_service.create_booking(
            db,
            student=student,
            session_id=cs.id,
            task="SQL joins",
            anonymous_question="How does LEFT JOIN work?",
            is_urgent=False,
            group_size=1,
        )

        assert b.id is not None
        assert b.student_id == student.id
        assert b.session_id == cs.id
        assert b.status == BookingStatus.active

    async def test_duplicate_raises(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general)
        db.add(cs)
        await db.flush()  # get cs.id before creating booking
        db.add(active_booking(student.id, cs.id))
        await db.flush()

        with pytest.raises(ValueError, match="Already booked"):
            await booking_service.create_booking(
                db,
                student=student,
                session_id=cs.id,
                task=None,
                anonymous_question=None,
                is_urgent=False,
                group_size=1,
            )

    async def test_graded_work_review_group_raises(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.graded_work_review, announced=True)
        db.add(cs)
        await db.flush()

        with pytest.raises(ValueError, match="1-on-1 only"):
            await booking_service.create_booking(
                db,
                student=student,
                session_id=cs.id,
                task=None,
                anonymous_question=None,
                is_urgent=False,
                group_size=3,
            )

    async def test_full_session_raises(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general, capacity=1)
        db.add(cs)
        # Use a second student to fill the slot
        from .conftest import _user
        from backend.db.models import UserRole
        other = _user(UserRole.student)
        db.add(other)
        await db.flush()
        db.add(active_booking(other.id, cs.id, group_size=1))
        await db.flush()

        with pytest.raises(ValueError, match="full"):
            await booking_service.create_booking(
                db,
                student=student,
                session_id=cs.id,
                task=None,
                anonymous_question=None,
                is_urgent=False,
                group_size=1,
            )

    async def test_session_not_found_raises(self, db, student):
        with pytest.raises(ValueError, match="not found"):
            await booking_service.create_booking(
                db,
                student=student,
                session_id=99999,
                task=None,
                anonymous_question=None,
                is_urgent=False,
                group_size=1,
            )

    async def test_urgent_notifies_professor(self, db, student, professor, course, enrolled):
        """Urgent booking creates notification for professor."""
        from sqlalchemy import select
        from backend.db.models import Notification

        cs = future_session(professor.id, course.id, ConsultationType.general)
        db.add(cs)
        await db.flush()

        await booking_service.create_booking(
            db,
            student=student,
            session_id=cs.id,
            task=None,
            anonymous_question="urgent question",
            is_urgent=True,
            group_size=1,
        )

        notifs = list((await db.scalars(
            select(Notification).where(Notification.user_id == professor.id, Notification.notification_type == "urgent")
        )).all())
        assert len(notifs) == 1


class TestCancelBooking:
    async def test_success(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general, days_ahead=5)
        db.add(cs)
        await db.flush()
        b = await booking_service.create_booking(
            db, student=student, session_id=cs.id,
            task=None, anonymous_question=None, is_urgent=False, group_size=1,
        )

        cancelled = await booking_service.cancel_booking(db, student=student, booking_id=b.id)

        assert cancelled.status == BookingStatus.cancelled
        assert cancelled.cancelled_at is not None

    async def test_cancel_wrong_student_raises(self, db, student, professor, course, enrolled):
        from .conftest import _user
        from backend.db.models import UserRole
        other = _user(UserRole.student)
        db.add(other)
        cs = future_session(professor.id, course.id, ConsultationType.general)
        db.add(cs)
        await db.flush()
        b = active_booking(other.id, cs.id)
        db.add(b)
        await db.flush()

        with pytest.raises(ValueError, match="not found"):
            await booking_service.cancel_booking(db, student=student, booking_id=b.id)

    async def test_cancel_promotes_waitlist(self, db, student, professor, course, enrolled):
        """Cancellation outside cutoff promotes first waitlist entry."""
        from .conftest import _user
        from backend.db.models import UserRole, CourseStudent, CourseStudentStatus

        # Second student on waitlist
        other = _user(UserRole.student)
        db.add(other)
        await db.flush()
        db.add(CourseStudent(student_id=other.id, course_id=course.id, academic_year="2025/2026", status=CourseStudentStatus.active))

        # Session well in the future (> cutoff)
        cs = future_session(professor.id, course.id, ConsultationType.general, days_ahead=5)
        db.add(cs)
        await db.flush()

        # Student books
        b = await booking_service.create_booking(
            db, student=student, session_id=cs.id,
            task=None, anonymous_question=None, is_urgent=False, group_size=1,
        )

        # Other student on waitlist
        wl = Waitlist(
            student_id=other.id,
            professor_id=professor.id,
            session_id=cs.id,
            preferred_date=cs.session_date,
            consultation_type=ConsultationType.general,
            course_id=course.id,
            position_hint=1,
            notified=False,
        )
        db.add(wl)
        await db.flush()

        await booking_service.cancel_booking(db, student=student, booking_id=b.id)

        # Waitlist entry should be gone (consumed)
        remaining_wl = await db.scalar(select(Waitlist).where(Waitlist.student_id == other.id))
        assert remaining_wl is None

        # Other student should now have an active booking
        new_booking = await db.scalar(
            select(Booking).where(
                Booking.student_id == other.id,
                Booking.session_id == cs.id,
                Booking.status == BookingStatus.active,
            )
        )
        assert new_booking is not None

    async def test_cancel_no_promotion_within_cutoff(self, db, student, professor, course, enrolled):
        """Cancellation within cutoff window — no waitlist promotion."""
        from .conftest import _user
        from backend.db.models import UserRole, CourseStudent, CourseStudentStatus

        other = _user(UserRole.student)
        db.add(other)
        await db.flush()
        db.add(CourseStudent(student_id=other.id, course_id=course.id, academic_year="2025/2026", status=CourseStudentStatus.active))

        # Session starting in 30 minutes UTC (within 2h cutoff)
        now_utc = datetime.now(UTC)
        t_from = (now_utc + timedelta(minutes=30)).time().replace(second=0, microsecond=0)
        t_to = (now_utc + timedelta(minutes=90)).time().replace(second=0, microsecond=0)
        cs = ConsultationSession(
            professor_id=professor.id,
            course_id=course.id,
            consultation_type=ConsultationType.general,
            session_date=now_utc.date(),
            time_from=t_from,
            time_to=t_to,
            format=SessionFormat.in_person,
            status=SessionStatus.confirmed,
            capacity=20,
        )
        db.add(cs)
        await db.flush()

        b = await booking_service.create_booking(
            db, student=student, session_id=cs.id,
            task=None, anonymous_question=None, is_urgent=False, group_size=1,
        )

        wl = Waitlist(
            student_id=other.id,
            professor_id=professor.id,
            session_id=cs.id,
            preferred_date=cs.session_date,
            consultation_type=ConsultationType.general,
            course_id=course.id,
            position_hint=1,
            notified=False,
        )
        db.add(wl)
        await db.flush()

        await booking_service.cancel_booking(db, student=student, booking_id=b.id)

        # Waitlist entry must still exist (no promotion)
        remaining_wl = await db.scalar(select(Waitlist).where(Waitlist.student_id == other.id))
        assert remaining_wl is not None

    async def test_thesis_cancel_no_waitlist_promotion(self, db, student, professor, course, enrolled):
        """Thesis cancellation never triggers waitlist promotion."""
        from .conftest import _user
        from backend.db.models import UserRole, CourseStudent, CourseStudentStatus

        other = _user(UserRole.student)
        db.add(other)
        await db.flush()

        db.add(
            ThesisApplication(
                student_id=student.id,
                professor_id=professor.id,
                status=ThesisApplicationStatus.active,
                topic_description="T",
            )
        )
        await db.flush()

        cs = future_session(professor.id, course.id, ConsultationType.thesis, days_ahead=5, announced=True)
        db.add(cs)
        await db.flush()

        b = await booking_service.create_booking(
            db, student=student, session_id=cs.id,
            task=None, anonymous_question=None, is_urgent=False, group_size=1,
        )

        wl = Waitlist(
            student_id=other.id,
            professor_id=professor.id,
            session_id=cs.id,
            preferred_date=cs.session_date,
            consultation_type=ConsultationType.thesis,
            course_id=course.id,
            position_hint=1,
            notified=False,
        )
        db.add(wl)
        await db.flush()

        await booking_service.cancel_booking(db, student=student, booking_id=b.id)

        # Waitlist entry must still exist (thesis exempt)
        remaining_wl = await db.scalar(select(Waitlist).where(Waitlist.student_id == other.id))
        assert remaining_wl is not None


class TestGradedWorkReviewNotifications:
    async def test_creating_graded_work_review_session_notifies_students(self, db, professor, course, enrolled, student):
        """Test that creating a graded work review session notifies enrolled students."""
        from backend.routers.professor import ExtraBody
        from backend.db.models import Notification, ConsultationType
        from datetime import date, time, timedelta

        body = ExtraBody(
            date=date.today() + timedelta(days=7),
            time_from=time(10, 0),
            time_to=time(11, 0),
            type=ConsultationType.graded_work_review,
        )

        # Create the session
        from backend.routers.professor import add_extra
        result = await add_extra(body, db, professor)

        # Check that notifications were created for enrolled students
        notifications = (
            await db.scalars(
                select(Notification).where(
                    Notification.user_id == student.id,
                    Notification.notification_type == "booking",
                )
            )
        ).all()
        assert len(notifications) == 1
        assert "Graded work review session available" in notifications[0].text
