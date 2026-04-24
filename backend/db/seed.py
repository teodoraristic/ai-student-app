"""Seed database with system config defaults and richer demo data."""

import asyncio
import logging
from datetime import UTC, date, datetime, time, timedelta

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import async_session_maker
from backend.db.models import (
    AcademicEvent,
    AcademicEventType,
    Announcement,
    Booking,
    BookingPriority,
    BookingStatus,
    ConsultationSession,
    ConsultationType,
    ConsultationWindow,
    Course,
    CourseProfessor,
    CourseStudent,
    CourseStudentStatus,
    ExamPeriod,
    Feedback,
    ProfessorAnnouncement,
    ProfessorProfile,
    Semester,
    SessionFormat,
    SessionStatus,
    SystemConfig,
    ThesisApplication,
    ThesisApplicationStatus,
    User,
    UserRole,
    Waitlist,
    WindowType,
)

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACADEMIC_YEAR = "2025/2026"

DEFAULT_CONFIG: list[tuple[str, str, str]] = [
    ("days_before_exam_trigger", "7", "Days before exam/midterm to run preparation workflow"),
    ("preparation_vote_threshold_percent", "10", "Percent of enrolled students for prep vote threshold; 0 = use absolute count only"),
    ("auto_schedule_vote_threshold", "5", "Minimum votes when percent threshold is disabled or enrollment is zero"),
    ("thesis_auto_book_on_accept", "1", "1 = book earliest thesis slot when professor accepts application"),
    ("professor_response_deadline_hours", "48", "Hours professor has to respond to scheduling request"),
    ("no_notice_cancel_window_hours", "1", "Cancellation within this window counts as no-notice"),
    ("penalty_cancellations_limit", "2", "No-notice cancellations triggering low priority"),
    ("penalty_duration_days", "30", "Duration of low waitlist priority penalty"),
    ("notification_polling_seconds", "60", "Suggested frontend notification poll interval"),
    ("waitlist_confirm_hours", "2", "Hours to confirm waitlist promotion"),
]


async def _ensure_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    **attrs,
) -> User:
    user = await session.scalar(select(User).where(User.email == email))
    if not user:
        user = User(
            email=email,
            password_hash=pwd_context.hash(password),
            one_time_password_hash=None,
            consent_accepted_at=datetime.now(UTC),
            **attrs,
        )
        session.add(user)
        await session.flush()
        return user

    for key, value in attrs.items():
        setattr(user, key, value)
    if not user.consent_accepted_at:
        user.consent_accepted_at = datetime.now(UTC)
    return user


async def _ensure_professor_profile(
    session: AsyncSession,
    *,
    professor: User,
    department: str,
    office_location: str,
    default_room: str,
    hall: str,
    pinned_note: str,
    max_thesis_students: int,
) -> ProfessorProfile:
    profile = await session.scalar(select(ProfessorProfile).where(ProfessorProfile.user_id == professor.id))
    if not profile:
        profile = ProfessorProfile(
            user_id=professor.id,
            department=department,
            office_location=office_location,
            default_room=default_room,
            hall=hall,
            pinned_note=pinned_note,
            max_thesis_students=max_thesis_students,
            is_active=True,
        )
        session.add(profile)
        await session.flush()
        return profile

    profile.department = department
    profile.office_location = office_location
    profile.default_room = default_room
    profile.hall = hall
    profile.pinned_note = pinned_note
    profile.max_thesis_students = max_thesis_students
    profile.is_active = True
    return profile


async def _ensure_course(
    session: AsyncSession,
    *,
    code: str,
    name: str,
    semester: Semester,
    year_of_study: int,
    department: str,
) -> Course:
    course = await session.scalar(select(Course).where(Course.code == code))
    if not course:
        course = Course(
            code=code,
            name=name,
            semester=semester,
            year_of_study=year_of_study,
            department=department,
        )
        session.add(course)
        await session.flush()
        return course

    course.name = name
    course.semester = semester
    course.year_of_study = year_of_study
    course.department = department
    return course


async def _ensure_course_professor(
    session: AsyncSession,
    *,
    professor: User,
    course: Course,
) -> CourseProfessor:
    row = await session.scalar(
        select(CourseProfessor).where(
            CourseProfessor.professor_id == professor.id,
            CourseProfessor.course_id == course.id,
        )
    )
    if not row:
        row = CourseProfessor(
            professor_id=professor.id,
            course_id=course.id,
            academic_year=ACADEMIC_YEAR,
        )
        session.add(row)
        await session.flush()
        return row

    row.academic_year = ACADEMIC_YEAR
    return row


async def _ensure_course_student(
    session: AsyncSession,
    *,
    student: User,
    course: Course,
    status: CourseStudentStatus = CourseStudentStatus.active,
) -> CourseStudent:
    row = await session.scalar(
        select(CourseStudent).where(
            CourseStudent.student_id == student.id,
            CourseStudent.course_id == course.id,
        )
    )
    if not row:
        row = CourseStudent(
            student_id=student.id,
            course_id=course.id,
            academic_year=ACADEMIC_YEAR,
            status=status,
        )
        session.add(row)
        await session.flush()
        return row

    row.academic_year = ACADEMIC_YEAR
    row.status = status
    return row


async def _ensure_window(
    session: AsyncSession,
    *,
    professor: User,
    day_of_week: str,
    time_from: time,
    time_to: time,
    window_type: WindowType,
) -> ConsultationWindow:
    row = await session.scalar(
        select(ConsultationWindow).where(
            ConsultationWindow.professor_id == professor.id,
            ConsultationWindow.day_of_week == day_of_week,
            ConsultationWindow.time_from == time_from,
            ConsultationWindow.time_to == time_to,
            ConsultationWindow.window_type == window_type,
        )
    )
    if not row:
        row = ConsultationWindow(
            professor_id=professor.id,
            day_of_week=day_of_week,
            time_from=time_from,
            time_to=time_to,
            window_type=window_type,
            is_active=True,
        )
        session.add(row)
        await session.flush()
        return row

    row.is_active = True
    return row


async def _ensure_announcement(
    session: AsyncSession,
    *,
    admin: User,
    title: str,
    body: str,
    expires_at: datetime | None = None,
) -> Announcement:
    row = await session.scalar(select(Announcement).where(Announcement.title == title))
    if not row:
        row = Announcement(
            title=title,
            body=body,
            created_by_id=admin.id,
            expires_at=expires_at,
        )
        session.add(row)
        await session.flush()
        return row

    row.body = body
    row.created_by_id = admin.id
    row.expires_at = expires_at
    return row


async def _ensure_event(
    session: AsyncSession,
    *,
    course: Course,
    event_type: AcademicEventType,
    event_date: date,
    name: str,
) -> AcademicEvent:
    row = await session.scalar(
        select(AcademicEvent).where(
            AcademicEvent.course_id == course.id,
            AcademicEvent.name == name,
        )
    )
    if not row:
        row = AcademicEvent(
            course_id=course.id,
            event_type=event_type,
            event_date=event_date,
            name=name,
        )
        session.add(row)
        await session.flush()
        return row

    row.event_type = event_type
    row.event_date = event_date
    return row


async def _ensure_session(
    session: AsyncSession,
    *,
    professor: User,
    course: Course | None,
    consultation_type: ConsultationType,
    session_date: date,
    time_from: time,
    time_to: time,
    capacity: int,
    announced_by_professor: bool = False,
    format: SessionFormat = SessionFormat.in_person,
    status: SessionStatus = SessionStatus.confirmed,
    event: AcademicEvent | None = None,
) -> ConsultationSession:
    row = await session.scalar(
        select(ConsultationSession).where(
            ConsultationSession.professor_id == professor.id,
            ConsultationSession.course_id == (course.id if course else None),
            ConsultationSession.consultation_type == consultation_type,
            ConsultationSession.session_date == session_date,
            ConsultationSession.time_from == time_from,
            ConsultationSession.time_to == time_to,
        )
    )
    if not row:
        row = ConsultationSession(
            professor_id=professor.id,
            course_id=course.id if course else None,
            consultation_type=consultation_type,
            session_date=session_date,
            time_from=time_from,
            time_to=time_to,
            format=format,
            status=status,
            capacity=capacity,
            announced_by_professor=announced_by_professor,
            event_id=event.id if event else None,
        )
        session.add(row)
        await session.flush()
        return row

    row.format = format
    row.status = status
    row.capacity = capacity
    row.announced_by_professor = announced_by_professor
    row.event_id = event.id if event else None
    return row


async def _ensure_booking(
    session: AsyncSession,
    *,
    student: User,
    consult_session: ConsultationSession,
    status: BookingStatus,
    group_size: int = 1,
    task: str | None = None,
    anonymous_question: str | None = None,
    is_urgent: bool = False,
    priority: BookingPriority = BookingPriority.normal,
    cancelled_at: datetime | None = None,
    cancellation_reason: str | None = None,
) -> Booking:
    row = await session.scalar(
        select(Booking).where(
            Booking.student_id == student.id,
            Booking.session_id == consult_session.id,
        )
    )
    if not row:
        row = Booking(
            student_id=student.id,
            session_id=consult_session.id,
            group_size=group_size,
            status=status,
            task=task,
            anonymous_question=anonymous_question,
            is_urgent=is_urgent,
            priority=priority,
            cancelled_at=cancelled_at,
            cancellation_reason=cancellation_reason,
        )
        session.add(row)
        await session.flush()
        return row

    row.group_size = group_size
    row.status = status
    row.task = task
    row.anonymous_question = anonymous_question
    row.is_urgent = is_urgent
    row.priority = priority
    row.cancelled_at = cancelled_at
    row.cancellation_reason = cancellation_reason
    return row


async def _ensure_feedback(
    session: AsyncSession,
    *,
    booking: Booking,
    rating: int,
    comment: str | None,
) -> Feedback:
    row = await session.scalar(select(Feedback).where(Feedback.booking_id == booking.id))
    if not row:
        row = Feedback(booking_id=booking.id, rating=rating, comment=comment)
        session.add(row)
        await session.flush()
        return row

    row.rating = rating
    row.comment = comment
    return row


async def _ensure_waitlist(
    session: AsyncSession,
    *,
    student: User,
    professor: User,
    consult_session: ConsultationSession,
    course: Course,
    position_hint: int,
) -> Waitlist:
    row = await session.scalar(
        select(Waitlist).where(
            Waitlist.student_id == student.id,
            Waitlist.session_id == consult_session.id,
        )
    )
    if not row:
        row = Waitlist(
            student_id=student.id,
            professor_id=professor.id,
            session_id=consult_session.id,
            preferred_date=consult_session.session_date,
            consultation_type=consult_session.consultation_type,
            course_id=course.id,
            position_hint=position_hint,
            notified=False,
        )
        session.add(row)
        await session.flush()
        return row

    row.professor_id = professor.id
    row.preferred_date = consult_session.session_date
    row.consultation_type = consult_session.consultation_type
    row.course_id = course.id
    row.position_hint = position_hint
    row.notified = False
    return row


async def _ensure_thesis_application(
    session: AsyncSession,
    *,
    student: User,
    professor: User,
    topic_description: str,
    status: ThesisApplicationStatus,
    applied_at: datetime,
    responded_at: datetime | None = None,
) -> ThesisApplication:
    row = await session.scalar(
        select(ThesisApplication).where(
            ThesisApplication.student_id == student.id,
            ThesisApplication.professor_id == professor.id,
        )
    )
    if not row:
        row = ThesisApplication(
            student_id=student.id,
            professor_id=professor.id,
            topic_description=topic_description,
            status=status,
            applied_at=applied_at,
            responded_at=responded_at,
        )
        session.add(row)
        await session.flush()
        return row

    row.topic_description = topic_description
    row.status = status
    row.applied_at = applied_at
    row.responded_at = responded_at
    return row


async def seed(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    today = date.today()

    for key, value, description in DEFAULT_CONFIG:
        existing = await session.scalar(select(SystemConfig).where(SystemConfig.key == key))
        if existing:
            existing.value = value
            existing.description = description
            continue
        session.add(SystemConfig(key=key, value=value, description=description))

    admin = await _ensure_user(
        session,
        email="admin@university.edu",
        password="AdminPass123!",
        first_name="Admin",
        last_name="User",
        role=UserRole.admin,
        is_active=True,
        password_change_required=False,
    )

    prof_markovic = await _ensure_user(
        session,
        email="prof.markovic@university.edu",
        password="ProfPass123!",
        first_name="Ana",
        last_name="Markovic",
        role=UserRole.professor,
        is_active=True,
        password_change_required=False,
    )
    prof_petrovic = await _ensure_user(
        session,
        email="prof.petrovic@university.edu",
        password="ProfPass123!",
        first_name="Petar",
        last_name="Petrovic",
        role=UserRole.professor,
        is_active=True,
        password_change_required=False,
    )
    prof_jovanovic = await _ensure_user(
        session,
        email="prof.jovanovic@university.edu",
        password="ProfPass123!",
        first_name="Jelena",
        last_name="Jovanovic",
        role=UserRole.professor,
        is_active=True,
        password_change_required=False,
    )
    prof_radovan = await _ensure_user(
        session,
        email="prof.djurdjevic@university.edu",
        password="ProfPass123!",
        first_name="Radovan",
        last_name="Djurdjevic",
        role=UserRole.professor,
        is_active=True,
        password_change_required=False,
    )
    prof_maja = await _ensure_user(
        session,
        email="prof.jovic@university.edu",
        password="ProfPass123!",
        first_name="Maja",
        last_name="Jovic",
        role=UserRole.professor,
        is_active=True,
        password_change_required=False,
    )
    prof_stefan = await _ensure_user(
        session,
        email="prof.nikolic@university.edu",
        password="ProfPass123!",
        first_name="Stefan",
        last_name="Nikolic",
        role=UserRole.professor,
        is_active=True,
        password_change_required=False,
    )

    await _ensure_professor_profile(
        session,
        professor=prof_markovic,
        department="Computer Science",
        office_location="Building A, 201",
        default_room="A-201",
        hall="Hall A",
        pinned_note="Bring your student ID. Thesis students should book only thesis sessions.",
        max_thesis_students=3,
    )
    await _ensure_professor_profile(
        session,
        professor=prof_petrovic,
        department="Software Engineering",
        office_location="Building B, 104",
        default_room="B-104",
        hall="Hall B",
        pinned_note="Algorithms consultations move fast. Please include examples you are stuck on.",
        max_thesis_students=2,
    )
    await _ensure_professor_profile(
        session,
        professor=prof_jovanovic,
        department="Systems",
        office_location="Building C, 301",
        default_room="C-301",
        hall="Hall C",
        pinned_note="Preparation sessions are usually group-friendly, so bring classmates if needed.",
        max_thesis_students=4,
    )
    await _ensure_professor_profile(
        session,
        professor=prof_radovan,
        department="Computer Science",
        office_location="Building D, 102",
        default_room="D-102",
        hall="Hall D",
        pinned_note="Bring network diagrams or packet captures if discussing labs.",
        max_thesis_students=3,
    )
    await _ensure_professor_profile(
        session,
        professor=prof_maja,
        department="Software Engineering",
        office_location="Building A, 015",
        default_room="A-015",
        hall="Lab A",
        pinned_note="For frontend topics, send a link to your repo or sandbox before the session.",
        max_thesis_students=2,
    )
    await _ensure_professor_profile(
        session,
        professor=prof_stefan,
        department="Mathematics",
        office_location="Building M, 210",
        default_room="M-210",
        hall="Hall M",
        pinned_note="Discrete math consultations: bring attempted proofs or homework drafts.",
        max_thesis_students=3,
    )

    student_ivan = await _ensure_user(
        session,
        email="student@university.edu",
        password="StudentPass123!",
        first_name="Ivan",
        last_name="Horvat",
        student_number="2024001",
        role=UserRole.student,
        is_final_year=True,
        is_active=True,
        password_change_required=False,
    )
    student_milica = await _ensure_user(
        session,
        email="milica.student@university.edu",
        password="StudentPass123!",
        first_name="Milica",
        last_name="Simic",
        student_number="2024002",
        role=UserRole.student,
        is_final_year=True,
        is_active=True,
        password_change_required=False,
    )
    student_nikola = await _ensure_user(
        session,
        email="nikola.student@university.edu",
        password="StudentPass123!",
        first_name="Nikola",
        last_name="Ilic",
        student_number="2024003",
        role=UserRole.student,
        is_final_year=False,
        is_active=True,
        password_change_required=False,
    )
    student_sara = await _ensure_user(
        session,
        email="sara.student@university.edu",
        password="StudentPass123!",
        first_name="Sara",
        last_name="Kovacevic",
        student_number="2024004",
        role=UserRole.student,
        is_final_year=False,
        is_active=True,
        password_change_required=False,
    )
    student_luka = await _ensure_user(
        session,
        email="luka.pavlovic.student@university.edu",
        password="StudentPass123!",
        first_name="Luka",
        last_name="Pavlovic",
        student_number="2024005",
        role=UserRole.student,
        is_final_year=True,
        is_active=True,
        password_change_required=False,
    )
    student_tea = await _ensure_user(
        session,
        email="tea.markovic.student@university.edu",
        password="StudentPass123!",
        first_name="Tea",
        last_name="Markovic",
        student_number="2024006",
        role=UserRole.student,
        is_final_year=False,
        is_active=True,
        password_change_required=False,
    )
    student_uros = await _ensure_user(
        session,
        email="uros.stankovic.student@university.edu",
        password="StudentPass123!",
        first_name="Uros",
        last_name="Stankovic",
        student_number="2024007",
        role=UserRole.student,
        is_final_year=True,
        is_active=True,
        password_change_required=False,
    )
    student_jovana = await _ensure_user(
        session,
        email="jovana.milic.student@university.edu",
        password="StudentPass123!",
        first_name="Jovana",
        last_name="Milic",
        student_number="2024008",
        role=UserRole.student,
        is_final_year=False,
        is_active=True,
        password_change_required=False,
    )
    student_dusan = await _ensure_user(
        session,
        email="dusan.todorovic.student@university.edu",
        password="StudentPass123!",
        first_name="Dusan",
        last_name="Todorovic",
        student_number="2024009",
        role=UserRole.student,
        is_final_year=False,
        is_active=True,
        password_change_required=False,
    )
    student_nina = await _ensure_user(
        session,
        email="nina.jankovic.student@university.edu",
        password="StudentPass123!",
        first_name="Nina",
        last_name="Jankovic",
        student_number="2024010",
        role=UserRole.student,
        is_final_year=True,
        is_active=True,
        password_change_required=False,
    )

    course_databases = await _ensure_course(
        session,
        code="CS101",
        name="Databases",
        semester=Semester.winter,
        year_of_study=2,
        department="Computer Science",
    )
    course_algorithms = await _ensure_course(
        session,
        code="CS202",
        name="Algorithms",
        semester=Semester.winter,
        year_of_study=2,
        department="Computer Science",
    )
    course_systems = await _ensure_course(
        session,
        code="CS303",
        name="Operating Systems",
        semester=Semester.summer,
        year_of_study=3,
        department="Computer Science",
    )
    course_networks = await _ensure_course(
        session,
        code="CS205",
        name="Computer Networks",
        semester=Semester.winter,
        year_of_study=2,
        department="Computer Science",
    )
    course_web = await _ensure_course(
        session,
        code="CS104",
        name="Web Development",
        semester=Semester.winter,
        year_of_study=1,
        department="Software Engineering",
    )
    course_discrete = await _ensure_course(
        session,
        code="MATH201",
        name="Discrete Structures",
        semester=Semester.winter,
        year_of_study=1,
        department="Mathematics",
    )
    course_ml = await _ensure_course(
        session,
        code="CS401",
        name="Introduction to Machine Learning",
        semester=Semester.summer,
        year_of_study=3,
        department="Computer Science",
    )

    await _ensure_course_professor(session, professor=prof_markovic, course=course_databases)
    await _ensure_course_professor(session, professor=prof_petrovic, course=course_algorithms)
    await _ensure_course_professor(session, professor=prof_jovanovic, course=course_systems)
    await _ensure_course_professor(session, professor=prof_radovan, course=course_networks)
    await _ensure_course_professor(session, professor=prof_maja, course=course_web)
    await _ensure_course_professor(session, professor=prof_stefan, course=course_discrete)
    await _ensure_course_professor(session, professor=prof_petrovic, course=course_ml)
    await _ensure_course_professor(session, professor=prof_jovanovic, course=course_ml)

    for student, course in (
        (student_ivan, course_databases),
        (student_ivan, course_algorithms),
        (student_milica, course_databases),
        (student_milica, course_systems),
        (student_nikola, course_algorithms),
        (student_nikola, course_systems),
        (student_sara, course_databases),
        (student_sara, course_systems),
        (student_luka, course_networks),
        (student_luka, course_ml),
        (student_luka, course_algorithms),
        (student_tea, course_web),
        (student_tea, course_discrete),
        (student_tea, course_databases),
        (student_uros, course_networks),
        (student_uros, course_systems),
        (student_uros, course_ml),
        (student_jovana, course_web),
        (student_jovana, course_algorithms),
        (student_dusan, course_discrete),
        (student_dusan, course_networks),
        (student_dusan, course_web),
        (student_nina, course_ml),
        (student_nina, course_databases),
        (student_nina, course_discrete),
    ):
        await _ensure_course_student(session, student=student, course=course)

    for professor, regular_day, regular_from, regular_to, thesis_day, thesis_from, thesis_to in (
        (prof_markovic, "wednesday", time(10, 0), time(12, 0), "friday", time(14, 0), time(16, 0)),
        (prof_petrovic, "monday", time(9, 0), time(11, 0), "thursday", time(13, 0), time(15, 0)),
        (prof_jovanovic, "tuesday", time(12, 0), time(14, 0), "thursday", time(10, 0), time(12, 0)),
        (prof_radovan, "monday", time(14, 0), time(16, 0), "wednesday", time(9, 0), time(11, 0)),
        (prof_maja, "tuesday", time(10, 0), time(12, 0), "friday", time(10, 0), time(12, 0)),
        (prof_stefan, "wednesday", time(15, 0), time(17, 0), "friday", time(9, 0), time(11, 0)),
    ):
        await _ensure_window(
            session,
            professor=professor,
            day_of_week=regular_day,
            time_from=regular_from,
            time_to=regular_to,
            window_type=WindowType.regular,
        )
        await _ensure_window(
            session,
            professor=professor,
            day_of_week=thesis_day,
            time_from=thesis_from,
            time_to=thesis_to,
            window_type=WindowType.thesis,
        )

    exam_period = await session.scalar(select(ExamPeriod).where(ExamPeriod.name == "Summer exam period"))
    if not exam_period:
        session.add(
            ExamPeriod(
                date_from=date(today.year, 6, 10),
                date_to=date(today.year, 6, 25),
                name="Summer exam period",
            )
        )

    event_databases_exam = await _ensure_event(
        session,
        course=course_databases,
        event_type=AcademicEventType.exam,
        event_date=today + timedelta(days=10),
        name="Databases Final Exam",
    )
    event_algorithms_midterm = await _ensure_event(
        session,
        course=course_algorithms,
        event_type=AcademicEventType.midterm,
        event_date=today + timedelta(days=14),
        name="Algorithms Midterm",
    )
    event_systems_exam = await _ensure_event(
        session,
        course=course_systems,
        event_type=AcademicEventType.exam,
        event_date=today + timedelta(days=18),
        name="Operating Systems Final Exam",
    )
    event_networks_exam = await _ensure_event(
        session,
        course=course_networks,
        event_type=AcademicEventType.exam,
        event_date=today + timedelta(days=12),
        name="Networks Final Exam",
    )
    event_web_midterm = await _ensure_event(
        session,
        course=course_web,
        event_type=AcademicEventType.midterm,
        event_date=today + timedelta(days=8),
        name="Web Development Midterm",
    )
    event_discrete_exam = await _ensure_event(
        session,
        course=course_discrete,
        event_type=AcademicEventType.exam,
        event_date=today + timedelta(days=20),
        name="Discrete Structures Exam",
    )
    event_ml_project = await _ensure_event(
        session,
        course=course_ml,
        event_type=AcademicEventType.exam,
        event_date=today + timedelta(days=22),
        name="Machine Learning Project Deadline",
    )

    await _ensure_announcement(
        session,
        admin=admin,
        title="Welcome to the demo data set",
        body="The seed includes six professors, ten students, seven courses, bookings, thesis cases, and waitlist entries.",
        expires_at=now + timedelta(days=30),
    )
    await _ensure_announcement(
        session,
        admin=admin,
        title="Preparation booking reminder",
        body="Use the chat or professor-announced preparation sessions to book before upcoming exams.",
        expires_at=now + timedelta(days=14),
    )

    ana_general_upcoming = await _ensure_session(
        session,
        professor=prof_markovic,
        course=course_databases,
        consultation_type=ConsultationType.general,
        session_date=today + timedelta(days=2),
        time_from=time(10, 0),
        time_to=time(11, 0),
        capacity=8,
    )
    ana_thesis_upcoming = await _ensure_session(
        session,
        professor=prof_markovic,
        course=course_databases,
        consultation_type=ConsultationType.thesis,
        session_date=today + timedelta(days=3),
        time_from=time(14, 0),
        time_to=time(15, 0),
        capacity=1,
    )
    ana_prep_upcoming = await _ensure_session(
        session,
        professor=prof_markovic,
        course=course_databases,
        consultation_type=ConsultationType.preparation,
        session_date=today + timedelta(days=4),
        time_from=time(13, 0),
        time_to=time(14, 0),
        capacity=30,
        announced_by_professor=True,
        event=event_databases_exam,
    )
    ana_review_full = await _ensure_session(
        session,
        professor=prof_markovic,
        course=course_databases,
        consultation_type=ConsultationType.graded_work_review,
        session_date=today + timedelta(days=6),
        time_from=time(15, 0),
        time_to=time(16, 0),
        capacity=1,
        announced_by_professor=True,
        event=event_databases_exam,
    )
    petar_general_upcoming = await _ensure_session(
        session,
        professor=prof_petrovic,
        course=course_algorithms,
        consultation_type=ConsultationType.general,
        session_date=today + timedelta(days=5),
        time_from=time(11, 0),
        time_to=time(12, 0),
        capacity=10,
    )
    jelena_general_upcoming = await _ensure_session(
        session,
        professor=prof_jovanovic,
        course=course_systems,
        consultation_type=ConsultationType.general,
        session_date=today + timedelta(days=5),
        time_from=time(12, 0),
        time_to=time(13, 0),
        capacity=10,
    )
    jelena_prep_upcoming = await _ensure_session(
        session,
        professor=prof_jovanovic,
        course=course_systems,
        consultation_type=ConsultationType.preparation,
        session_date=today + timedelta(days=7),
        time_from=time(10, 0),
        time_to=time(11, 30),
        capacity=20,
        announced_by_professor=True,
        event=event_systems_exam,
    )
    radovan_general_upcoming = await _ensure_session(
        session,
        professor=prof_radovan,
        course=course_networks,
        consultation_type=ConsultationType.general,
        session_date=today + timedelta(days=4),
        time_from=time(15, 0),
        time_to=time(16, 0),
        capacity=12,
    )
    maja_general_upcoming = await _ensure_session(
        session,
        professor=prof_maja,
        course=course_web,
        consultation_type=ConsultationType.general,
        session_date=today + timedelta(days=3),
        time_from=time(14, 0),
        time_to=time(15, 0),
        capacity=15,
    )
    stefan_general_upcoming = await _ensure_session(
        session,
        professor=prof_stefan,
        course=course_discrete,
        consultation_type=ConsultationType.general,
        session_date=today + timedelta(days=6),
        time_from=time(11, 0),
        time_to=time(12, 0),
        capacity=20,
    )
    petar_ml_general = await _ensure_session(
        session,
        professor=prof_petrovic,
        course=course_ml,
        consultation_type=ConsultationType.general,
        session_date=today + timedelta(days=8),
        time_from=time(10, 0),
        time_to=time(11, 0),
        capacity=12,
    )
    radovan_prep_upcoming = await _ensure_session(
        session,
        professor=prof_radovan,
        course=course_networks,
        consultation_type=ConsultationType.preparation,
        session_date=today + timedelta(days=9),
        time_from=time(16, 0),
        time_to=time(17, 0),
        capacity=25,
        announced_by_professor=True,
        event=event_networks_exam,
    )
    ana_past_attended = await _ensure_session(
        session,
        professor=prof_markovic,
        course=course_databases,
        consultation_type=ConsultationType.general,
        session_date=today - timedelta(days=7),
        time_from=time(10, 0),
        time_to=time(11, 0),
        capacity=8,
    )
    petar_past_attended = await _ensure_session(
        session,
        professor=prof_petrovic,
        course=course_algorithms,
        consultation_type=ConsultationType.general,
        session_date=today - timedelta(days=10),
        time_from=time(11, 0),
        time_to=time(12, 0),
        capacity=10,
    )
    ana_past_cancelled = await _ensure_session(
        session,
        professor=prof_markovic,
        course=course_databases,
        consultation_type=ConsultationType.general,
        session_date=today - timedelta(days=3),
        time_from=time(9, 0),
        time_to=time(10, 0),
        capacity=8,
        status=SessionStatus.cancelled,
    )

    ivan_general_booking = await _ensure_booking(
        session,
        student=student_ivan,
        consult_session=ana_general_upcoming,
        status=BookingStatus.active,
        task="Need help understanding joins and normalization.",
        anonymous_question="Can we review a sample query plan?",
    )
    ivan_prep_booking = await _ensure_booking(
        session,
        student=student_ivan,
        consult_session=ana_prep_upcoming,
        status=BookingStatus.active,
        is_urgent=True,
        task="Exam preparation for transactions and indexes.",
        anonymous_question="I want to cover transactions and indexes.",
    )
    ivan_thesis_booking = await _ensure_booking(
        session,
        student=student_ivan,
        consult_session=ana_thesis_upcoming,
        status=BookingStatus.active,
        task="Discuss thesis outline and milestone plan.",
        anonymous_question="I have a draft architecture for the project.",
    )
    ivan_attended_booking = await _ensure_booking(
        session,
        student=student_ivan,
        consult_session=ana_past_attended,
        status=BookingStatus.attended,
        task="Reviewed ER modeling homework.",
    )
    ivan_feedback_booking = await _ensure_booking(
        session,
        student=student_ivan,
        consult_session=petar_past_attended,
        status=BookingStatus.attended,
        task="Complexity and recurrence relations.",
    )
    await _ensure_feedback(
        session,
        booking=ivan_feedback_booking,
        rating=5,
        comment="Very clear explanation and useful follow-up examples.",
    )
    await _ensure_booking(
        session,
        student=student_ivan,
        consult_session=ana_past_cancelled,
        status=BookingStatus.cancelled,
        task="Wanted to go over SQL constraints.",
        cancelled_at=now - timedelta(days=3),
        cancellation_reason="Professor unavailable that day.",
    )
    await _ensure_booking(
        session,
        student=student_milica,
        consult_session=jelena_general_upcoming,
        status=BookingStatus.active,
        task="Need help with process scheduling.",
    )
    await _ensure_booking(
        session,
        student=student_nikola,
        consult_session=petar_general_upcoming,
        status=BookingStatus.active,
        task="Need more examples for graph traversals.",
    )
    await _ensure_booking(
        session,
        student=student_sara,
        consult_session=ana_review_full,
        status=BookingStatus.active,
        task="Review graded lab assignment.",
        priority=BookingPriority.normal,
    )
    await _ensure_booking(
        session,
        student=student_milica,
        consult_session=jelena_prep_upcoming,
        status=BookingStatus.active,
        task="Preparation for the OS final.",
    )
    await _ensure_booking(
        session,
        student=student_luka,
        consult_session=radovan_general_upcoming,
        status=BookingStatus.active,
        task="TCP congestion control lab.",
    )
    await _ensure_booking(
        session,
        student=student_tea,
        consult_session=maja_general_upcoming,
        status=BookingStatus.active,
        task="React hooks and state lifting.",
    )
    await _ensure_booking(
        session,
        student=student_nina,
        consult_session=stefan_general_upcoming,
        status=BookingStatus.active,
        task="Graph theory homework — spanning trees.",
    )
    await _ensure_booking(
        session,
        student=student_uros,
        consult_session=petar_ml_general,
        status=BookingStatus.active,
        task="Gradient descent intuition.",
    )
    await _ensure_booking(
        session,
        student=student_dusan,
        consult_session=radovan_prep_upcoming,
        status=BookingStatus.active,
        task="Exam prep: routing and switching.",
    )

    await _ensure_waitlist(
        session,
        student=student_ivan,
        professor=prof_markovic,
        consult_session=ana_review_full,
        course=course_databases,
        position_hint=1,
    )

    await _ensure_thesis_application(
        session,
        student=student_ivan,
        professor=prof_markovic,
        topic_description="Schema-aware assistant for student consultation workflows.",
        status=ThesisApplicationStatus.active,
        applied_at=now - timedelta(days=21),
        responded_at=now - timedelta(days=19),
    )
    student_ivan.thesis_professor_id = prof_markovic.id

    await _ensure_thesis_application(
        session,
        student=student_milica,
        professor=prof_petrovic,
        topic_description="Visualization of graph algorithms for teaching assistants.",
        status=ThesisApplicationStatus.pending,
        applied_at=now - timedelta(days=2),
    )
    student_milica.thesis_professor_id = None

    await _ensure_thesis_application(
        session,
        student=student_nikola,
        professor=prof_markovic,
        topic_description="Performance testing for relational databases.",
        status=ThesisApplicationStatus.rejected,
        applied_at=now - timedelta(days=30),
        responded_at=now - timedelta(days=28),
    )
    student_nikola.thesis_professor_id = None
    student_sara.thesis_professor_id = None

    # Add some professor announcements
    session.add(ProfessorAnnouncement(
        professor_id=prof_markovic.id,
        course_id=course_databases.id,
        academic_event_id=event_databases_exam.id,
        announcement_type="preparation",
        title="Preparation Session for Databases Exam",
        message="I'll be holding a preparation session for the upcoming databases exam. This will cover key topics like normalization, indexing, and query optimization. Students can book slots through the chatbot or directly.",
        created_at=now - timedelta(days=5),
        expires_at=now + timedelta(days=5),
    ))
    session.add(ProfessorAnnouncement(
        professor_id=prof_jovanovic.id,
        course_id=course_systems.id,
        announcement_type="general",
        title="Office Hours Reminder",
        message="Remember that my regular office hours are on Tuesdays 12-14 in Hall C. For thesis students, additional slots are available on Thursdays.",
        created_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=14),
    ))

    await session.commit()
    logger.info("Seed completed with expanded demo data.")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with async_session_maker() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
