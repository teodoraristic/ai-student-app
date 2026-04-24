"""SQLAlchemy ORM models."""

import enum
from datetime import UTC, date, datetime, time
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class UserRole(str, enum.Enum):
    student = "student"
    professor = "professor"
    admin = "admin"


class Semester(str, enum.Enum):
    winter = "WINTER"
    summer = "SUMMER"


class CourseStudentStatus(str, enum.Enum):
    active = "ACTIVE"
    completed = "COMPLETED"
    failed = "FAILED"
    withdrawn = "WITHDRAWN"


class WindowType(str, enum.Enum):
    regular = "REGULAR"
    thesis = "THESIS"


class ConsultationType(str, enum.Enum):
    graded_work_review = "GRADED_WORK_REVIEW"
    thesis = "THESIS"
    general = "GENERAL"
    preparation = "PREPARATION"


class SessionFormat(str, enum.Enum):
    in_person = "IN_PERSON"
    online = "ONLINE"


class SessionStatus(str, enum.Enum):
    pending_confirmation = "PENDING_CONFIRMATION"
    confirmed = "CONFIRMED"
    cancelled = "CANCELLED"


class AcademicEventType(str, enum.Enum):
    midterm = "MIDTERM"
    exam = "EXAM"


class BookingStatus(str, enum.Enum):
    active = "ACTIVE"
    waitlist = "WAITLIST"
    cancelled = "CANCELLED"
    attended = "ATTENDED"
    no_show = "NO_SHOW"


class BookingPriority(str, enum.Enum):
    normal = "NORMAL"
    low = "LOW"


class ThesisApplicationStatus(str, enum.Enum):
    pending = "PENDING"
    rejected = "REJECTED"
    active = "ACTIVE"


class SchedulerLogStatus(str, enum.Enum):
    ok = "OK"
    error = "ERROR"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    student_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_final_year: Mapped[bool] = mapped_column(Boolean, default=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    one_time_password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_change_required: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    thesis_professor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    consent_accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    professor_profile: Mapped[Optional["ProfessorProfile"]] = relationship(
        back_populates="user", uselist=False
    )
    created_by: Mapped[Optional["User"]] = relationship(
        remote_side=[id],
        foreign_keys=[created_by_id],
    )


class ProfessorProfile(Base):
    __tablename__ = "professor_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String(255), default="")
    office_location: Mapped[str] = mapped_column(String(255), default="")
    default_room: Mapped[str] = mapped_column(String(255), default="")
    hall: Mapped[str] = mapped_column(String(255), default="")
    photo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    pinned_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    max_thesis_students: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="professor_profile")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    semester: Mapped[Semester] = mapped_column(Enum(Semester), nullable=False)
    year_of_study: Mapped[int] = mapped_column(Integer, default=1)
    department: Mapped[str] = mapped_column(String(255), default="")


class CourseProfessor(Base):
    __tablename__ = "course_professors"
    __table_args__ = (UniqueConstraint("professor_id", "course_id", "academic_year", name="uq_cp_prof_course_year"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, default="2025/2026")


class CourseStudent(Base):
    __tablename__ = "course_students"
    __table_args__ = (UniqueConstraint("student_id", "course_id", "academic_year", name="uq_cs_stu_course_year"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(32), nullable=False, default="2025/2026")
    status: Mapped[CourseStudentStatus] = mapped_column(Enum(CourseStudentStatus), default=CourseStudentStatus.active)


class ConsultationWindow(Base):
    __tablename__ = "consultation_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    day_of_week: Mapped[str] = mapped_column(String(16), nullable=False)
    time_from: Mapped[time] = mapped_column(Time, nullable=False)
    time_to: Mapped[time] = mapped_column(Time, nullable=False)
    window_type: Mapped[WindowType] = mapped_column("type", Enum(WindowType), nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class BlockedDate(Base):
    __tablename__ = "blocked_dates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    blocked_date: Mapped[date] = mapped_column("date", Date, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ExtraSlot(Base):
    __tablename__ = "extra_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    slot_date: Mapped[date] = mapped_column("date", Date, nullable=False)
    time_from: Mapped[time] = mapped_column(Time, nullable=False)
    time_to: Mapped[time] = mapped_column(Time, nullable=False)
    slot_type: Mapped[WindowType] = mapped_column("type", Enum(WindowType), nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ExamPeriod(Base):
    __tablename__ = "exam_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class AcademicEvent(Base):
    __tablename__ = "academic_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    event_type: Mapped[AcademicEventType] = mapped_column(Enum(AcademicEventType), nullable=False)
    event_date: Mapped[date] = mapped_column("date", Date, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class ConsultationSession(Base):
    __tablename__ = "consultation_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[Optional[int]] = mapped_column(ForeignKey("courses.id"), nullable=True)
    consultation_type: Mapped[ConsultationType] = mapped_column(Enum(ConsultationType), nullable=False)
    session_date: Mapped[date] = mapped_column("date", Date, nullable=False)
    time_from: Mapped[time] = mapped_column(Time, nullable=False)
    time_to: Mapped[time] = mapped_column(Time, nullable=False)
    format: Mapped[SessionFormat] = mapped_column(Enum(SessionFormat), nullable=False)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), default=SessionStatus.pending_confirmation)
    event_id: Mapped[Optional[int]] = mapped_column(ForeignKey("academic_events.id"), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=20)
    announced_by_professor: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_id: Mapped[int] = mapped_column(ForeignKey("consultation_sessions.id"), nullable=False)
    task: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    anonymous_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False)
    group_size: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.active)
    priority: Mapped[BookingPriority] = mapped_column(Enum(BookingPriority), default=BookingPriority.normal)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    waitlist_confirm_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ThesisApplication(Base):
    __tablename__ = "thesis_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    professor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    topic_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ThesisApplicationStatus] = mapped_column(
        Enum(ThesisApplicationStatus), default=ThesisApplicationStatus.pending
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Waitlist(Base):
    __tablename__ = "waitlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    professor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("consultation_sessions.id"), nullable=True)
    window_id: Mapped[Optional[int]] = mapped_column(ForeignKey("consultation_windows.id"), nullable=True)
    preferred_date: Mapped[date] = mapped_column(Date, nullable=False)
    consultation_type: Mapped[ConsultationType] = mapped_column(Enum(ConsultationType), nullable=False)
    course_id: Mapped[Optional[int]] = mapped_column(ForeignKey("courses.id"), nullable=True)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    position_hint: Mapped[int] = mapped_column(Integer, default=0)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(64), default="info")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    link: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)


class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    detail: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class SchedulerLog(Base):
    __tablename__ = "scheduler_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_name: Mapped[str] = mapped_column(String(128), nullable=False)
    ran_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    status: Mapped[SchedulerLogStatus] = mapped_column(Enum(SchedulerLogStatus), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SystemConfig(Base):
    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    state: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class ProfessorAnnouncement(Base):
    __tablename__ = "professor_announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    academic_event_id: Mapped[Optional[int]] = mapped_column(ForeignKey("academic_events.id"), nullable=True)
    announcement_type: Mapped[str] = mapped_column(String(64), nullable=False)  # 'preparation', 'graded_work_review', etc.
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class PreparationVote(Base):
    __tablename__ = "preparation_votes"
    __table_args__ = (UniqueConstraint("student_id", "academic_event_id", name="uq_vote_student_event"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    academic_event_id: Mapped[int] = mapped_column(ForeignKey("academic_events.id"), nullable=False)
    preferred_times: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class SchedulingRequestStatus(str, enum.Enum):
    pending = "PENDING"
    accepted = "ACCEPTED"
    declined = "DECLINED"
    expired = "EXPIRED"
    auto_scheduled = "AUTO_SCHEDULED"


class SchedulingRequest(Base):
    __tablename__ = "scheduling_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    professor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    academic_event_id: Mapped[int] = mapped_column(ForeignKey("academic_events.id"), nullable=False)
    vote_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[SchedulingRequestStatus] = mapped_column(
        Enum(SchedulingRequestStatus), default=SchedulingRequestStatus.pending
    )
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("consultation_sessions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class Appeal(Base):
    __tablename__ = "appeals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
