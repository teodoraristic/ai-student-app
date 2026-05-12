"""Seed database — minimal demo data for general consultation group-join scenario."""

import asyncio
import logging
from datetime import datetime, time, timedelta, UTC

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dates import utc_today
from backend.db.base import async_session_maker
from backend.db.models import (
    Booking,
    BookingStatus,
    ConsultationSession,
    ConsultationType,
    ConsultationWindow,
    Course,
    CourseProfessor,
    CourseStudent,
    CourseStudentStatus,
    ProfessorProfile,
    Semester,
    SessionFormat,
    SessionStatus,
    SystemConfig,
    User,
    UserRole,
    WindowType,
)

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACADEMIC_YEAR = "2025/2026"

DEFAULT_CONFIG: list[tuple[str, str, str]] = [
    ("days_before_exam_trigger", "7", "Days before exam/midterm to run preparation workflow"),
    ("preparation_vote_threshold_percent", "10", "Percent of enrolled students for prep vote threshold"),
    ("auto_schedule_vote_threshold", "5", "Minimum votes when percent threshold is disabled"),
    ("thesis_auto_book_on_accept", "1", "1 = book earliest thesis slot when professor accepts application"),
    ("professor_response_deadline_hours", "48", "Hours professor has to respond to scheduling request"),
    ("no_notice_cancel_window_hours", "1", "Cancellation within this window counts as no-notice"),
    ("penalty_cancellations_limit", "2", "No-notice cancellations triggering low priority"),
    ("penalty_duration_days", "30", "Duration of low waitlist priority penalty"),
    ("notification_polling_seconds", "60", "Suggested frontend notification poll interval"),
    ("waitlist_confirm_hours", "2", "Hours to confirm waitlist promotion"),
    ("waitlist_cutoff_hours", "2", "Hours before session start when waitlist auto-promotion stops"),
]


async def _ensure_user(session: AsyncSession, *, email: str, password: str, **attrs) -> User:
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


async def seed(session: AsyncSession) -> None:
    today = utc_today()

    # System config
    for key, value, description in DEFAULT_CONFIG:
        existing = await session.scalar(select(SystemConfig).where(SystemConfig.key == key))
        if existing:
            existing.value = value
            existing.description = description
            continue
        session.add(SystemConfig(key=key, value=value, description=description))

    # Users
    await _ensure_user(
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
    prof_nikolic = await _ensure_user(
        session,
        email="prof.nikolic@university.edu",
        password="ProfPass123!",
        first_name="Stefan",
        last_name="Nikolic",
        role=UserRole.professor,
        is_active=True,
        password_change_required=False,
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

    # Professor profile
    profile = await session.scalar(
        select(ProfessorProfile).where(ProfessorProfile.user_id == prof_markovic.id)
    )
    if not profile:
        profile = ProfessorProfile(
            user_id=prof_markovic.id,
            department="Computer Science",
            office_location="Building A, 201",
            default_room="A-201",
            hall="Hall A",
            pinned_note="Bring your student ID.",
            max_thesis_students=3,
            is_active=True,
        )
        session.add(profile)
        await session.flush()
    else:
        profile.is_active = True

    for prof, dept, office, room, hall, note in (
        (prof_petrovic,  "Software Engineering", "Building B, 104", "B-104", "Hall B", "Include examples you are stuck on."),
        (prof_jovanovic, "Systems",              "Building C, 301", "C-301", "Hall C", "Group-friendly sessions, bring classmates."),
        (prof_nikolic,   "Mathematics",          "Building M, 210", "M-210", "Hall M", "Bring attempted proofs or homework drafts."),
    ):
        p = await session.scalar(select(ProfessorProfile).where(ProfessorProfile.user_id == prof.id))
        if not p:
            session.add(ProfessorProfile(
                user_id=prof.id,
                department=dept,
                office_location=office,
                default_room=room,
                hall=hall,
                pinned_note=note,
                max_thesis_students=2,
                is_active=True,
            ))
        else:
            p.is_active = True
    await session.flush()

    # Course
    course_databases = await session.scalar(select(Course).where(Course.code == "CS101"))
    if not course_databases:
        course_databases = Course(
            code="CS101",
            name="Databases",
            semester=Semester.winter,
            year_of_study=2,
            department="Computer Science",
        )
        session.add(course_databases)
        await session.flush()

    course_algorithms = await session.scalar(select(Course).where(Course.code == "CS202"))
    if not course_algorithms:
        course_algorithms = Course(code="CS202", name="Algorithms", semester=Semester.winter, year_of_study=2, department="Computer Science")
        session.add(course_algorithms)
        await session.flush()

    course_systems = await session.scalar(select(Course).where(Course.code == "CS303"))
    if not course_systems:
        course_systems = Course(code="CS303", name="Operating Systems", semester=Semester.summer, year_of_study=3, department="Computer Science")
        session.add(course_systems)
        await session.flush()

    course_discrete = await session.scalar(select(Course).where(Course.code == "MATH201"))
    if not course_discrete:
        course_discrete = Course(code="MATH201", name="Discrete Structures", semester=Semester.winter, year_of_study=1, department="Mathematics")
        session.add(course_discrete)
        await session.flush()

    # Professor → course
    cp = await session.scalar(
        select(CourseProfessor).where(
            CourseProfessor.professor_id == prof_markovic.id,
            CourseProfessor.course_id == course_databases.id,
            CourseProfessor.academic_year == ACADEMIC_YEAR,
        )
    )
    if not cp:
        session.add(CourseProfessor(
            professor_id=prof_markovic.id,
            course_id=course_databases.id,
            academic_year=ACADEMIC_YEAR,
        ))
        await session.flush()

    for prof, course in (
        (prof_petrovic,  course_algorithms),
        (prof_jovanovic, course_systems),
        (prof_nikolic,   course_discrete),
    ):
        exists = await session.scalar(
            select(CourseProfessor).where(
                CourseProfessor.professor_id == prof.id,
                CourseProfessor.course_id == course.id,
                CourseProfessor.academic_year == ACADEMIC_YEAR,
            )
        )
        if not exists:
            session.add(CourseProfessor(professor_id=prof.id, course_id=course.id, academic_year=ACADEMIC_YEAR))
    await session.flush()

    # Students → courses (all four courses so chatbot can find all professors)
    for student in (student_ivan, student_milica):
        for course in (course_databases, course_algorithms, course_systems, course_discrete):
            cs = await session.scalar(
                select(CourseStudent).where(
                    CourseStudent.student_id == student.id,
                    CourseStudent.course_id == course.id,
                    CourseStudent.academic_year == ACADEMIC_YEAR,
                )
            )
            if not cs:
                session.add(CourseStudent(
                    student_id=student.id,
                    course_id=course.id,
                    academic_year=ACADEMIC_YEAR,
                    status=CourseStudentStatus.active,
                ))
            else:
                cs.status = CourseStudentStatus.active
    await session.flush()

    # Consultation windows — Ana: Wednesday 10-12 (regular), Friday 14-16 (thesis)
    for day, tf, tt, wtype in (
        ("wednesday", time(10, 0), time(12, 0), WindowType.regular),
        ("friday",    time(14, 0), time(16, 0), WindowType.thesis),
    ):
        w = await session.scalar(
            select(ConsultationWindow).where(
                ConsultationWindow.professor_id == prof_markovic.id,
                ConsultationWindow.day_of_week == day,
                ConsultationWindow.time_from == tf,
                ConsultationWindow.time_to == tt,
                ConsultationWindow.window_type == wtype,
            )
        )
        slot_mins = 60 if wtype == WindowType.thesis else 15
        if not w:
            session.add(ConsultationWindow(
                professor_id=prof_markovic.id,
                day_of_week=day,
                time_from=tf,
                time_to=tt,
                window_type=wtype,
                slot_duration_minutes=slot_mins,
                is_active=True,
            ))
        else:
            w.is_active = True
            w.slot_duration_minutes = slot_mins

    for prof, reg_day, reg_from, reg_to, thesis_day, thesis_from, thesis_to in (
        (prof_petrovic,  "monday",    time(9,  0), time(11, 0), "thursday", time(13, 0), time(15, 0)),
        (prof_jovanovic, "tuesday",   time(12, 0), time(14, 0), "thursday", time(10, 0), time(12, 0)),
        (prof_nikolic,   "wednesday", time(15, 0), time(17, 0), "friday",   time(9,  0), time(11, 0)),
    ):
        for day, tf, tt, wtype in (
            (reg_day,    reg_from,    reg_to,    WindowType.regular),
            (thesis_day, thesis_from, thesis_to, WindowType.thesis),
        ):
            slot_mins = 60 if wtype == WindowType.thesis else 15
            w = await session.scalar(
                select(ConsultationWindow).where(
                    ConsultationWindow.professor_id == prof.id,
                    ConsultationWindow.day_of_week == day,
                    ConsultationWindow.time_from == tf,
                    ConsultationWindow.time_to == tt,
                    ConsultationWindow.window_type == wtype,
                )
            )
            if not w:
                session.add(ConsultationWindow(
                    professor_id=prof.id,
                    day_of_week=day,
                    time_from=tf,
                    time_to=tt,
                    window_type=wtype,
                    slot_duration_minutes=slot_mins,
                    is_active=True,
                ))
            else:
                w.is_active = True
                w.slot_duration_minutes = slot_mins
    await session.flush()

    # Demo session: Ana / Databases / general, today+7, capacity=5
    # Ivan already booked with task="SQL joins" — when Milica asks same topic, chatbot offers group join
    demo_session = await session.scalar(
        select(ConsultationSession).where(
            ConsultationSession.professor_id == prof_markovic.id,
            ConsultationSession.course_id == course_databases.id,
            ConsultationSession.consultation_type == ConsultationType.general,
            ConsultationSession.session_date == today + timedelta(days=7),
            ConsultationSession.time_from == time(11, 0),
            ConsultationSession.time_to == time(12, 0),
        )
    )
    if not demo_session:
        demo_session = ConsultationSession(
            professor_id=prof_markovic.id,
            course_id=course_databases.id,
            consultation_type=ConsultationType.general,
            session_date=today + timedelta(days=7),
            time_from=time(11, 0),
            time_to=time(12, 0),
            format=SessionFormat.in_person,
            capacity=5,
            announced_by_professor=False,
            status=SessionStatus.confirmed,
        )
        session.add(demo_session)
        await session.flush()
    else:
        demo_session.capacity = 5
        demo_session.status = SessionStatus.confirmed

    # Extra upcoming sessions with bookings
    upcoming_extra = [
        (today + timedelta(days=3),  time(10, 0), time(11, 0), 8,  student_ivan,   "Indexing strategies"),
        (today + timedelta(days=5),  time(13, 0), time(14, 0), 10, student_milica, "Transaction isolation levels"),
        (today + timedelta(days=14), time(10, 0), time(11, 0), 6,  student_ivan,   "Stored procedures"),
    ]
    for s_date, tf, tt, cap, student, task in upcoming_extra:
        up_s = await session.scalar(
            select(ConsultationSession).where(
                ConsultationSession.professor_id == prof_markovic.id,
                ConsultationSession.session_date == s_date,
                ConsultationSession.time_from == tf,
                ConsultationSession.time_to == tt,
            )
        )
        if not up_s:
            up_s = ConsultationSession(
                professor_id=prof_markovic.id,
                course_id=course_databases.id,
                consultation_type=ConsultationType.general,
                session_date=s_date,
                time_from=tf,
                time_to=tt,
                format=SessionFormat.in_person,
                capacity=cap,
                announced_by_professor=False,
                status=SessionStatus.confirmed,
            )
            session.add(up_s)
            await session.flush()

        bk = await session.scalar(
            select(Booking).where(
                Booking.student_id == student.id,
                Booking.session_id == up_s.id,
            )
        )
        if not bk:
            session.add(Booking(
                student_id=student.id,
                session_id=up_s.id,
                group_size=1,
                status=BookingStatus.active,
                task=task,
            ))
        else:
            bk.status = BookingStatus.active
            bk.task = task
    await session.flush()

    # Past sessions with bookings (2 attended, 1 no-show)
    past_data = [
        (today - timedelta(days=10), time(10, 0), time(11, 0), student_ivan,   BookingStatus.attended, "Normalization forms"),
        (today - timedelta(days=6),  time(13, 0), time(14, 0), student_milica, BookingStatus.attended, "ER diagram review"),
        (today - timedelta(days=2),  time(10, 0), time(11, 0), student_ivan,   BookingStatus.active,   "Query optimization"),
    ]
    for s_date, tf, tt, student, bstatus, task in past_data:
        past_s = await session.scalar(
            select(ConsultationSession).where(
                ConsultationSession.professor_id == prof_markovic.id,
                ConsultationSession.session_date == s_date,
                ConsultationSession.time_from == tf,
                ConsultationSession.time_to == tt,
            )
        )
        if not past_s:
            past_s = ConsultationSession(
                professor_id=prof_markovic.id,
                course_id=course_databases.id,
                consultation_type=ConsultationType.general,
                session_date=s_date,
                time_from=tf,
                time_to=tt,
                format=SessionFormat.in_person,
                capacity=8,
                announced_by_professor=False,
                status=SessionStatus.confirmed,
            )
            session.add(past_s)
            await session.flush()

        bk = await session.scalar(
            select(Booking).where(
                Booking.student_id == student.id,
                Booking.session_id == past_s.id,
            )
        )
        if not bk:
            session.add(Booking(
                student_id=student.id,
                session_id=past_s.id,
                group_size=1,
                status=bstatus,
                task=task,
            ))
        else:
            bk.status = bstatus
            bk.task = task

    await session.commit()
    logger.info("Seed complete — demo data ready.")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with async_session_maker() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
