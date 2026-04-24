"""Tests for workers/tasks — daily_check scheduling, deadline expiry, reminders."""

from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    AcademicEvent,
    AcademicEventType,
    Booking,
    BookingStatus,
    BookingPriority,
    ConsultationSession,
    ConsultationType,
    CourseProfessor,
    CourseStudent,
    CourseStudentStatus,
    Notification,
    PreparationVote,
    SchedulingRequest,
    SchedulingRequestStatus,
    SessionFormat,
    SessionStatus,
    SystemConfig,
    UserRole,
)
from backend.workers.tasks import daily_check, reminder_check, waitlist_check

from .conftest import future_session, active_booking, _user


class TestDailyCheck:
    async def test_creates_scheduling_request(self, db, student, professor, course):
        """Votes for an event → SchedulingRequest created for professor."""
        db.add(CourseProfessor(professor_id=professor.id, course_id=course.id, academic_year="2025/2026"))
        db.add(CourseStudent(student_id=student.id, course_id=course.id, academic_year="2025/2026", status=CourseStudentStatus.active))
        db.add(SystemConfig(key="days_before_exam_trigger", value="7", description=""))
        db.add(SystemConfig(key="auto_schedule_vote_threshold", value="5", description=""))
        await db.flush()

        event_date = date.today() + timedelta(days=5)
        ev = AcademicEvent(
            course_id=course.id,
            event_type=AcademicEventType.exam,
            event_date=event_date,
            name="Midterm",
        )
        db.add(ev)
        await db.flush()

        db.add(PreparationVote(student_id=student.id, course_id=course.id, academic_event_id=ev.id))
        await db.flush()

        await daily_check(db)

        sr = await db.scalar(
            select(SchedulingRequest).where(
                SchedulingRequest.professor_id == professor.id,
                SchedulingRequest.academic_event_id == ev.id,
            )
        )
        assert sr is not None
        assert sr.vote_count == 1
        assert sr.status == SchedulingRequestStatus.pending

    async def test_notifies_professor_at_threshold(self, db, professor, course):
        """Enough votes → professor gets notification."""
        db.add(CourseProfessor(professor_id=professor.id, course_id=course.id, academic_year="2025/2026"))
        db.add(SystemConfig(key="days_before_exam_trigger", value="7", description=""))
        db.add(SystemConfig(key="preparation_vote_threshold_percent", value="0", description=""))
        # Set threshold to 3 so we can easily hit it
        db.add(SystemConfig(key="auto_schedule_vote_threshold", value="3", description=""))
        await db.flush()

        event_date = date.today() + timedelta(days=4)
        ev = AcademicEvent(
            course_id=course.id,
            event_type=AcademicEventType.exam,
            event_date=event_date,
            name="Final",
        )
        db.add(ev)
        await db.flush()

        # Add 3 votes (meets threshold)
        for _ in range(3):
            u = _user(UserRole.student)
            db.add(u)
            await db.flush()
            db.add(PreparationVote(student_id=u.id, course_id=course.id, academic_event_id=ev.id))
        await db.flush()

        await daily_check(db)

        notif = await db.scalar(
            select(Notification).where(
                Notification.user_id == professor.id,
                Notification.notification_type == "scheduling_request",
            )
        )
        assert notif is not None
        assert "3" in notif.text

    async def test_no_votes_no_request(self, db, professor, course):
        """No votes → no SchedulingRequest created."""
        db.add(CourseProfessor(professor_id=professor.id, course_id=course.id, academic_year="2025/2026"))
        db.add(SystemConfig(key="days_before_exam_trigger", value="7", description=""))
        db.add(SystemConfig(key="auto_schedule_vote_threshold", value="5", description=""))
        await db.flush()

        ev = AcademicEvent(
            course_id=course.id,
            event_type=AcademicEventType.exam,
            event_date=date.today() + timedelta(days=3),
            name="Quiz",
        )
        db.add(ev)
        await db.flush()

        await daily_check(db)

        count = await db.scalar(
            select(SchedulingRequest).where(SchedulingRequest.academic_event_id == ev.id)
        )
        assert count is None

    async def test_expires_overdue_scheduling_request(self, db, student, professor, course):
        """Overdue SchedulingRequest marked EXPIRED; voters notified."""
        db.add(CourseProfessor(professor_id=professor.id, course_id=course.id, academic_year="2025/2026"))
        db.add(CourseStudent(student_id=student.id, course_id=course.id, academic_year="2025/2026", status=CourseStudentStatus.active))
        db.add(SystemConfig(key="days_before_exam_trigger", value="7", description=""))
        db.add(SystemConfig(key="auto_schedule_vote_threshold", value="5", description=""))
        await db.flush()

        # Event far in future so it won't appear in the trigger window
        ev = AcademicEvent(
            course_id=course.id,
            event_type=AcademicEventType.exam,
            event_date=date.today() + timedelta(days=60),
            name="Future Exam",
        )
        db.add(ev)
        await db.flush()

        db.add(PreparationVote(student_id=student.id, course_id=course.id, academic_event_id=ev.id))

        # Overdue scheduling request (deadline in the past)
        from backend.db.models import SchedulingRequest
        sr = SchedulingRequest(
            professor_id=professor.id,
            course_id=course.id,
            academic_event_id=ev.id,
            vote_count=1,
            status=SchedulingRequestStatus.pending,
            deadline_at=datetime.now(UTC) - timedelta(hours=1),
        )
        db.add(sr)
        await db.flush()

        await daily_check(db)

        await db.refresh(sr)
        assert sr.status == SchedulingRequestStatus.expired

        # Student should be notified
        notif = await db.scalar(
            select(Notification).where(
                Notification.user_id == student.id,
                Notification.notification_type == "scheduler",
            )
        )
        assert notif is not None
        assert "not confirmed" in notif.text.lower()

    async def test_existing_request_vote_count_updated(self, db, professor, course):
        """Existing PENDING SchedulingRequest gets vote_count updated on re-run."""
        db.add(CourseProfessor(professor_id=professor.id, course_id=course.id, academic_year="2025/2026"))
        db.add(SystemConfig(key="days_before_exam_trigger", value="7", description=""))
        db.add(SystemConfig(key="auto_schedule_vote_threshold", value="10", description=""))
        await db.flush()

        ev = AcademicEvent(
            course_id=course.id,
            event_type=AcademicEventType.exam,
            event_date=date.today() + timedelta(days=6),
            name="Lab",
        )
        db.add(ev)
        await db.flush()

        from backend.db.models import SchedulingRequest
        existing_sr = SchedulingRequest(
            professor_id=professor.id,
            course_id=course.id,
            academic_event_id=ev.id,
            vote_count=1,
            status=SchedulingRequestStatus.pending,
            deadline_at=datetime.now(UTC) + timedelta(days=10),
        )
        db.add(existing_sr)

        for _ in range(2):
            u = _user(UserRole.student)
            db.add(u)
            await db.flush()
            db.add(PreparationVote(student_id=u.id, course_id=course.id, academic_event_id=ev.id))
        await db.flush()

        await daily_check(db)

        await db.refresh(existing_sr)
        assert existing_sr.vote_count == 2


class TestReminderCheck:
    async def test_sends_reminder_for_tomorrow_sessions(self, db, student, professor, course, enrolled):
        """Sessions tomorrow → bookings get reminder notification."""
        tomorrow = date.today() + timedelta(days=1)
        cs = ConsultationSession(
            professor_id=professor.id,
            course_id=course.id,
            consultation_type=ConsultationType.general,
            session_date=tomorrow,
            time_from=time(10, 0),
            time_to=time(11, 0),
            format=SessionFormat.in_person,
            status=SessionStatus.confirmed,
            capacity=20,
        )
        db.add(cs)
        await db.flush()
        db.add(active_booking(student.id, cs.id))
        await db.flush()

        await reminder_check(db)

        notif = await db.scalar(
            select(Notification).where(
                Notification.user_id == student.id,
                Notification.notification_type == "reminder",
            )
        )
        assert notif is not None
        assert "tomorrow" in notif.text.lower()

    async def test_no_reminder_for_past_sessions(self, db, student, professor, course, enrolled):
        """No notifications sent for sessions that aren't tomorrow."""
        cs = ConsultationSession(
            professor_id=professor.id,
            course_id=course.id,
            consultation_type=ConsultationType.general,
            session_date=date.today() + timedelta(days=3),
            time_from=time(10, 0),
            time_to=time(11, 0),
            format=SessionFormat.in_person,
            status=SessionStatus.confirmed,
            capacity=20,
        )
        db.add(cs)
        await db.flush()
        db.add(active_booking(student.id, cs.id))
        await db.flush()

        await reminder_check(db)

        notif = await db.scalar(
            select(Notification).where(Notification.user_id == student.id)
        )
        assert notif is None


class TestWaitlistCheck:
    async def test_removes_waitlist_for_past_session(self, db, student, professor, course, enrolled):
        """Stale waitlist rows for past sessions are cleared and the student is notified."""
        from backend.db.models import Waitlist

        yesterday = date.today() - timedelta(days=1)
        cs = ConsultationSession(
            professor_id=professor.id,
            course_id=course.id,
            consultation_type=ConsultationType.general,
            session_date=yesterday,
            time_from=time(10, 0),
            time_to=time(11, 0),
            format=SessionFormat.in_person,
            status=SessionStatus.confirmed,
            capacity=5,
        )
        db.add(cs)
        await db.flush()
        db.add(
            Waitlist(
                student_id=student.id,
                professor_id=professor.id,
                session_id=cs.id,
                preferred_date=yesterday,
                consultation_type=ConsultationType.general,
                course_id=course.id,
                position_hint=1,
                notified=False,
            )
        )
        await db.flush()

        await waitlist_check(db)

        wl = await db.scalar(select(Waitlist).where(Waitlist.student_id == student.id))
        assert wl is None
        notif = await db.scalar(
            select(Notification).where(
                Notification.user_id == student.id,
                Notification.notification_type == "waitlist",
            )
        )
        assert notif is not None

    async def test_promotes_waitlist_when_seat_available(self, db, student, professor, course, enrolled):
        from backend.db.models import Waitlist

        from .conftest import _user, future_session, active_booking

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

        cs = future_session(professor.id, course.id, ConsultationType.general, days_ahead=3, capacity=2)
        db.add(cs)
        await db.flush()
        db.add(active_booking(student.id, cs.id))
        db.add(
            Waitlist(
                student_id=other.id,
                professor_id=professor.id,
                session_id=cs.id,
                preferred_date=cs.session_date,
                consultation_type=ConsultationType.general,
                course_id=course.id,
                position_hint=1,
                notified=False,
            )
        )
        await db.flush()

        await waitlist_check(db)

        b = await db.scalar(
            select(Booking).where(
                Booking.student_id == other.id,
                Booking.session_id == cs.id,
                Booking.status == BookingStatus.active,
            )
        )
        assert b is not None
