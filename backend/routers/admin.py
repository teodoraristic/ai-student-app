"""Admin / staff endpoints."""

from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field, model_validator
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.base import get_db
from backend.db.models import (
    AcademicEvent,
    AcademicEventType,
    Announcement,
    Booking,
    BookingStatus,
    ConsultationSession,
    Course,
    CourseProfessor,
    CourseStudent,
    CourseStudentStatus,
    ExamPeriod,
    KnowledgeBase,
    SchedulerLog,
    SchedulerLogStatus,
    SystemConfig,
    User,
    UserRole,
)
from backend.middleware.auth_middleware import require_role
from backend.services import admin_service, exam_service, notification_service

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateUserBody(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    role: UserRole
    student_number: Optional[str] = Field(None, max_length=64)
    """Undergraduate / combined study year (1–6). Required when role is student."""
    study_year: Optional[int] = Field(None, ge=1, le=6)

    @model_validator(mode="after")
    def student_study_year(self) -> "CreateUserBody":
        if self.role == UserRole.student:
            if self.study_year is None:
                raise ValueError("study_year is required for students (1–6)")
        else:
            self.study_year = None
        return self


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    rows = list((await db.scalars(select(User))).all())
    return [
        {
            "id": u.id,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "role": u.role.value,
            "is_active": u.is_active,
            "password_change_required": u.password_change_required,
            "study_year": u.study_year,
            "is_final_year": u.is_final_year,
        }
        for u in rows
    ]


@router.post("/users")
async def create_user_admin(
    body: CreateUserBody,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    try:
        user, otp = await admin_service.create_user(
            db,
            email=body.email,
            first_name=body.first_name,
            last_name=body.last_name,
            role=body.role,
            student_number=body.student_number,
            study_year=body.study_year,
            created_by=admin,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.value,
            "password_change_required": user.password_change_required,
            "study_year": user.study_year,
            "is_final_year": user.is_final_year,
        },
        "one_time_password": otp,
    }


class UserPatch(BaseModel):
    is_final_year: Optional[bool] = None
    is_active: Optional[bool] = None


@router.patch("/users/{user_id}")
async def patch_user(
    user_id: int,
    body: UserPatch,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(u, k, v)
    await db.commit()
    return {"ok": True}


@router.patch("/users/{user_id}/deactivate")
async def deactivate(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404)
    await admin_service.deactivate_user(db, u)
    await db.commit()
    return {"ok": True}


@router.post("/users/{user_id}/reset-password")
async def reset_pw(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    u = await db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404)
    otp = await admin_service.reset_user_password(db, u)
    await db.commit()
    return {"one_time_password": otp}


class CourseLink(BaseModel):
    course_id: int
    academic_year: str = "2025/2026"


@router.post("/users/{user_id}/enroll")
async def enroll_student(
    user_id: int,
    body: CourseLink,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    st = await db.get(User, user_id)
    if not st or st.role != UserRole.student:
        raise HTTPException(status_code=400)
    exists = await db.scalar(
        select(CourseStudent).where(
            CourseStudent.student_id == user_id,
            CourseStudent.course_id == body.course_id,
        )
    )
    if not exists:
        db.add(
            CourseStudent(
                student_id=user_id,
                course_id=body.course_id,
                academic_year=body.academic_year,
                status=CourseStudentStatus.active,
            )
        )
        await db.commit()
    return {"ok": True}


@router.post("/users/{professor_id}/assign-course")
async def assign_prof_course(
    professor_id: int,
    body: CourseLink,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    exists = await db.scalar(
        select(CourseProfessor).where(
            CourseProfessor.professor_id == professor_id,
            CourseProfessor.course_id == body.course_id,
        )
    )
    if not exists:
        db.add(
            CourseProfessor(
                professor_id=professor_id,
                course_id=body.course_id,
                academic_year=body.academic_year,
            )
        )
        await db.commit()
    return {"ok": True}


@router.get("/events")
async def list_events(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    rows = list((await db.scalars(select(AcademicEvent))).all())
    return [
        {
            "id": r.id,
            "course_id": r.course_id,
            "type": r.event_type.value,
            "date": r.event_date.isoformat(),
            "name": r.name,
            "academic_year": r.academic_year,
            "time_from": r.time_from.isoformat() if r.time_from else None,
            "time_to": r.time_to.isoformat() if r.time_to else None,
            "hall": r.hall,
            "exam_period_id": r.exam_period_id,
        }
        for r in rows
    ]


class EventBody(BaseModel):
    course_id: int
    type: AcademicEventType
    date: date
    name: str = Field(max_length=255)
    academic_year: str = "2025/2026"
    time_from: Optional[time] = None
    time_to: Optional[time] = None
    hall: Optional[str] = None
    exam_period_id: Optional[int] = None


@router.post("/events")
async def add_event(
    body: EventBody,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    ep_id = None if body.type == AcademicEventType.midterm else body.exam_period_id
    try:
        await exam_service.validate_academic_event_fields(
            db,
            event_type=body.type,
            event_date=body.date,
            exam_period_id=ep_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    e = AcademicEvent(
        course_id=body.course_id,
        event_type=body.type,
        event_date=body.date,
        name=body.name,
        academic_year=body.academic_year,
        time_from=body.time_from,
        time_to=body.time_to,
        hall=body.hall,
        exam_period_id=ep_id,
    )
    db.add(e)
    await db.commit()
    return {"id": e.id}


class EventPatch(BaseModel):
    course_id: Optional[int] = None
    type: Optional[AcademicEventType] = None
    date: Optional[date] = None
    name: Optional[str] = Field(default=None, max_length=255)
    academic_year: Optional[str] = None
    time_from: Optional[time] = None
    time_to: Optional[time] = None
    hall: Optional[str] = None
    exam_period_id: Optional[int] = None
    clear_exam_period: bool = False


@router.patch("/events/{event_id}")
async def patch_event(
    event_id: int,
    body: EventPatch,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    raw = body.model_dump(exclude_unset=True)
    clear = bool(raw.pop("clear_exam_period", False))
    try:
        await exam_service.patch_academic_event(db, event_id, raw, clear_exam_period=clear)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"ok": True}


@router.delete("/events/{event_id}")
async def del_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    res = await db.execute(delete(AcademicEvent).where(AcademicEvent.id == event_id))
    if res.rowcount == 0:
        raise HTTPException(status_code=404)
    await db.commit()
    return {"ok": True}


@router.get("/exam-period")
async def list_exam_periods(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    rows = list((await db.scalars(select(ExamPeriod))).all())
    return [
        {"id": r.id, "date_from": r.date_from.isoformat(), "date_to": r.date_to.isoformat(), "name": r.name}
        for r in rows
    ]


class ExamPeriodBody(BaseModel):
    date_from: date
    date_to: date
    name: str


@router.post("/exam-period")
async def add_exam_period(
    body: ExamPeriodBody,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    ep = ExamPeriod(date_from=body.date_from, date_to=body.date_to, name=body.name)
    db.add(ep)
    await db.commit()
    return {"id": ep.id}


class ExamPeriodPatch(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    name: Optional[str] = None


@router.patch("/exam-period/{period_id}")
async def patch_exam_period(
    period_id: int,
    body: ExamPeriodPatch,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    ep = await db.get(ExamPeriod, period_id)
    if not ep:
        raise HTTPException(status_code=404)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(ep, k, v)
    await db.commit()
    return {"ok": True}


@router.get("/knowledge-base")
async def kb_list(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    rows = list((await db.scalars(select(KnowledgeBase))).all())
    return [
        {
            "id": r.id,
            "topic": r.topic,
            "question": r.question,
            "answer": r.answer,
            "keywords": r.keywords or [],
            "is_active": r.is_active,
        }
        for r in rows
    ]


class KBBody(BaseModel):
    topic: str
    question: str
    answer: str
    keywords: list[str] = Field(default_factory=list)


@router.post("/knowledge-base")
async def kb_add(
    body: KBBody,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    kb = KnowledgeBase(
        topic=body.topic,
        question=body.question,
        answer=body.answer,
        keywords=body.keywords,
        updated_by_id=admin.id,
    )
    db.add(kb)
    await db.commit()
    return {"id": kb.id}


class KBPatch(BaseModel):
    topic: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    keywords: Optional[list[str]] = None
    is_active: Optional[bool] = None


@router.patch("/knowledge-base/{kb_id}")
async def kb_patch(
    kb_id: int,
    body: KBPatch,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        raise HTTPException(status_code=404)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(kb, k, v)
    kb.updated_by_id = admin.id
    await db.commit()
    return {"ok": True}


@router.delete("/knowledge-base/{kb_id}")
async def kb_del(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    res = await db.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    if res.rowcount == 0:
        raise HTTPException(status_code=404)
    await db.commit()
    return {"ok": True}


@router.get("/announcements")
async def ann_list(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    rows = list((await db.scalars(select(Announcement))).all())
    return [{"id": r.id, "title": r.title, "published_at": r.published_at.isoformat()} for r in rows]


class AnnBody(BaseModel):
    title: str
    body: str
    expires_at: Optional[datetime] = None


@router.post("/announcements")
async def ann_add(
    body: AnnBody,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    ann = await admin_service.notify_all_students(db, body.title, body.body, admin)
    if body.expires_at:
        ann.expires_at = body.expires_at
    await db.commit()
    return {"id": ann.id}


@router.delete("/announcements/{ann_id}")
async def ann_del(
    ann_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    a = await db.get(Announcement, ann_id)
    if not a:
        raise HTTPException(status_code=404)
    await db.execute(delete(Announcement).where(Announcement.id == ann_id))
    await db.commit()
    return {"ok": True}


@router.get("/sessions")
async def admin_sessions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    rows = list((await db.scalars(select(ConsultationSession))).all())
    return [
        {
            "id": r.id,
            "professor_id": r.professor_id,
            "course_id": r.course_id,
            "date": r.session_date.isoformat(),
            "status": r.status.value,
        }
        for r in rows
    ]


@router.delete("/sessions/{session_id}")
async def admin_cancel_session(
    session_id: int,
    reason: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    from backend.db.models import SessionStatus

    if len(reason.strip()) < 3:
        raise HTTPException(status_code=400, detail="Reason required")
    cs = await db.get(ConsultationSession, session_id)
    if not cs:
        raise HTTPException(status_code=404)
    cs.status = SessionStatus.cancelled
    bookings = list((await db.scalars(select(Booking).where(Booking.session_id == session_id))).all())
    for b in bookings:
        if b.status == BookingStatus.active:
            b.status = BookingStatus.cancelled
            await notification_service.notify_user(
                db,
                b.student_id,
                f"Your consultation was cancelled by staff: {reason}",
                notification_type="cancel",
            )
    await db.commit()
    return {"ok": True}


@router.get("/dashboard")
async def admin_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    total = await db.scalar(select(func.count()).select_from(Booking))
    return {"total_bookings": int(total or 0), "no_show_rate": 0.0, "waitlist_per_professor": {}}


@router.get("/system-config")
async def cfg_list(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    rows = list((await db.scalars(select(SystemConfig))).all())
    return [{"key": r.key, "value": r.value, "description": r.description} for r in rows]


class ConfigPatch(BaseModel):
    value: str


@router.patch("/system-config/{key}")
async def cfg_patch(
    key: str,
    body: ConfigPatch,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    await admin_service.upsert_system_config(db, key, body.value)
    await db.commit()
    return {"ok": True}


@router.get("/scheduler-log")
async def sched_log(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    rows = list(
        (await db.scalars(select(SchedulerLog).order_by(SchedulerLog.ran_at.desc()).limit(100))).all()
    )
    return [
        {"id": r.id, "task_name": r.task_name, "ran_at": r.ran_at.isoformat(), "status": r.status.value}
        for r in rows
    ]


@router.post("/scheduler/run/{task_name}")
async def sched_run(
    task_name: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    from backend.workers import tasks as worker_tasks

    await worker_tasks.run_task_by_name(db, task_name)
    await db.commit()
    return {"ok": True, "task": task_name}


class CourseCreateBody(BaseModel):
    name: str
    code: str


@router.get("/courses")
async def list_courses(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    rows = list((await db.scalars(select(Course).order_by(Course.code))).all())
    return [{"id": c.id, "name": c.name, "code": c.code, "semester": c.semester.value} for c in rows]


@router.post("/courses")
async def create_course(
    body: CourseCreateBody,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin)),
):
    from backend.db.models import Semester

    c = Course(name=body.name, code=body.code, semester=Semester.winter, year_of_study=1, department="")
    db.add(c)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"id": c.id}
