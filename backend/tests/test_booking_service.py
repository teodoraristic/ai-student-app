"""Tests for booking_service — create, cancel, waitlist promotion."""

from datetime import date, datetime, time, timedelta, UTC

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.models import (
    Booking,
    BookingPriority,
    BookingStatus,
    ConsultationSession,
    ConsultationType,
    CourseStudent,
    CourseStudentStatus,
    Notification,
    SessionFormat,
    SessionStatus,
    ThesisApplication,
    ThesisApplicationStatus,
    UserRole,
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
                group_size=1,
            )

    async def test_rebook_same_session_after_cancel(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general, capacity=3)
        db.add(cs)
        await db.flush()
        b1 = await booking_service.create_booking(
            db,
            student=student,
            session_id=cs.id,
            task="A",
            anonymous_question=None,
            group_size=1,
        )
        await booking_service.cancel_booking(db, student=student, booking_id=b1.id)
        await db.flush()
        b2 = await booking_service.create_booking(
            db,
            student=student,
            session_id=cs.id,
            task="B",
            anonymous_question=None,
            group_size=1,
        )
        assert b2.id != b1.id
        assert b2.status == BookingStatus.active

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
                group_size=1,
            )

    async def test_peers_notified_when_another_joins_group_general(self, db, student, professor, course, enrolled):
        """Existing bookers get in-app notice when a second student joins the same group slot."""
        from .conftest import _user

        other = _user(UserRole.student, "Bob", "Peer")
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
        cs = future_session(professor.id, course.id, ConsultationType.general, capacity=8)
        db.add(cs)
        await db.flush()
        db.add(active_booking(other.id, cs.id, group_size=1))
        await db.flush()

        await booking_service.create_booking(
            db,
            student=student,
            session_id=cs.id,
            task=None,
            anonymous_question=None,
            group_size=1,
        )

        peer_notifs = list(
            (
                await db.scalars(
                    select(Notification).where(
                        Notification.user_id == other.id,
                        Notification.notification_type == "group_session",
                    )
                )
            ).all()
        )
        assert len(peer_notifs) == 1
        assert "One more person" in peer_notifs[0].text
        assert "/student/bookings" in (peer_notifs[0].link or "")

    async def test_no_peer_group_notif_for_first_booker_only(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general, capacity=8)
        db.add(cs)
        await db.flush()

        await booking_service.create_booking(
            db,
            student=student,
            session_id=cs.id,
            task=None,
            anonymous_question=None,
            group_size=1,
        )

        peer_group = list(
            (
                await db.scalars(
                    select(Notification).where(
                        Notification.user_id == student.id,
                        Notification.notification_type == "group_session",
                    )
                )
            ).all()
        )
        assert len(peer_group) == 0


class TestCancelBooking:
    async def test_success(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general, days_ahead=5)
        db.add(cs)
        await db.flush()
        b = await booking_service.create_booking(
            db, student=student, session_id=cs.id,
            task=None, anonymous_question=None, group_size=1,
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
            task=None, anonymous_question=None, group_size=1,
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
            task=None, anonymous_question=None, group_size=1,
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

    async def test_thesis_cancel_promotes_waitlist(self, db, student, professor, course, enrolled):
        """Thesis cancellation promotes the next waitlisted student when eligible."""
        from .conftest import _user
        from backend.db.models import UserRole, CourseStudent, CourseStudentStatus

        other = _user(UserRole.student)
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
        db.add(
            ThesisApplication(
                student_id=student.id,
                professor_id=professor.id,
                status=ThesisApplicationStatus.active,
                topic_description="T",
            )
        )
        db.add(
            ThesisApplication(
                student_id=other.id,
                professor_id=professor.id,
                status=ThesisApplicationStatus.active,
                topic_description="T2",
            )
        )
        await db.flush()

        cs = future_session(professor.id, course.id, ConsultationType.thesis, days_ahead=5, announced=True)
        db.add(cs)
        await db.flush()

        b = await booking_service.create_booking(
            db, student=student, session_id=cs.id,
            task=None, anonymous_question=None, group_size=1,
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

        remaining_wl = await db.scalar(select(Waitlist).where(Waitlist.student_id == other.id))
        assert remaining_wl is None
        new_booking = await db.scalar(
            select(Booking).where(
                Booking.student_id == other.id,
                Booking.session_id == cs.id,
                Booking.status == BookingStatus.active,
            )
        )
        assert new_booking is not None


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


class TestCalendarBookings:
    async def test_student_calendar_month_contains_booking(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general, days_ahead=10)
        db.add(cs)
        await db.flush()
        db.add(active_booking(student.id, cs.id))
        await db.flush()

        y, m = cs.session_date.year, cs.session_date.month
        rows = await booking_service.list_calendar_bookings(db, student, year=y, month=m)
        assert len(rows) == 1
        assert rows[0]["session_date"] == cs.session_date.isoformat()
        assert rows[0]["consultation_type"] == "GENERAL"

    async def test_professor_calendar_lists_session_bookings(self, db, student, professor, course, enrolled):
        cs = future_session(professor.id, course.id, ConsultationType.general, days_ahead=12)
        db.add(cs)
        await db.flush()
        db.add(active_booking(student.id, cs.id))
        await db.flush()

        y, m = cs.session_date.year, cs.session_date.month
        rows = await booking_service.list_calendar_bookings(db, professor, year=y, month=m)
        assert len(rows) == 1
        assert rows[0]["id"] is not None

    async def test_calendar_omits_cancelled_bookings(self, db, student, professor, course, enrolled):
        cs_active = future_session(professor.id, course.id, ConsultationType.general, days_ahead=14)
        cs_cancel = future_session(professor.id, course.id, ConsultationType.general, days_ahead=15)
        db.add(cs_active)
        db.add(cs_cancel)
        await db.flush()
        db.add(active_booking(student.id, cs_active.id))
        db.add(
            Booking(
                student_id=student.id,
                session_id=cs_cancel.id,
                group_size=1,
                status=BookingStatus.cancelled,
                priority=BookingPriority.normal,
            )
        )
        await db.flush()
        y, m = cs_active.session_date.year, cs_active.session_date.month
        assert cs_cancel.session_date.month == m
        rows = await booking_service.list_calendar_bookings(db, student, year=y, month=m)
        assert len(rows) == 1
        assert rows[0]["session_id"] == cs_active.id


def test_merge_professor_slot_cards_merges_same_prep_timeslot():
    rows = [
        {
            "session_id": 10,
            "session_date": "2026-05-01",
            "time_from": "10:00:00",
            "time_to": "11:00:00",
            "consultation_type": "PREPARATION",
            "course_code": "CS101",
            "course_name": "Intro",
            "hall": None,
            "session_party_total": 1,
            "session_booking_count": 1,
            "bookings": [
                {"id": 1, "student_name": "A", "group_size": 1, "status": "ACTIVE", "task": None}
            ],
        },
        {
            "session_id": 11,
            "session_date": "2026-05-01",
            "time_from": "10:00:00",
            "time_to": "11:00:00",
            "consultation_type": "PREPARATION",
            "course_code": "CS101",
            "course_name": "Intro",
            "hall": None,
            "session_party_total": 2,
            "session_booking_count": 1,
            "bookings": [
                {"id": 2, "student_name": "B", "group_size": 2, "status": "ACTIVE", "task": None}
            ],
        },
    ]
    merged = booking_service.merge_professor_slot_cards_for_same_timeslot(rows)
    assert len(merged) == 1
    assert merged[0]["session_id"] == 10
    assert merged[0]["session_party_total"] == 3
    assert len(merged[0]["bookings"]) == 2


def test_merge_professor_slot_cards_leaves_general_unmerged():
    rows = [
        {
            "session_id": 1,
            "session_date": "2026-05-01",
            "time_from": "10:00:00",
            "time_to": "11:00:00",
            "consultation_type": "GENERAL",
            "course_code": "X",
            "course_name": "Y",
            "hall": None,
            "session_party_total": 1,
            "session_booking_count": 1,
            "bookings": [
                {"id": 1, "student_name": "A", "group_size": 1, "status": "ACTIVE", "task": None}
            ],
        },
        {
            "session_id": 2,
            "session_date": "2026-05-01",
            "time_from": "10:00:00",
            "time_to": "11:00:00",
            "consultation_type": "GENERAL",
            "course_code": "X",
            "course_name": "Y",
            "hall": None,
            "session_party_total": 1,
            "session_booking_count": 1,
            "bookings": [
                {"id": 2, "student_name": "B", "group_size": 1, "status": "ACTIVE", "task": None}
            ],
        },
    ]
    merged = booking_service.merge_professor_slot_cards_for_same_timeslot(rows)
    assert len(merged) == 2
