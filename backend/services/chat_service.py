"""Rule-based chatbot — all parsing and responses live here."""

from __future__ import annotations

import difflib
import logging
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    AcademicEvent,
    Booking,
    BookingStatus,
    ConsultationSession,
    ConsultationType,
    Conversation,
    Course,
    CourseProfessor,
    CourseStudent,
    PreparationVote,
    SchedulingRequest,
    SchedulingRequestStatus,
    ThesisApplication,
    ThesisApplicationStatus,
    User,
    UserRole,
    Waitlist,
)
from backend.services import (
    booking_service,
    config_service,
    notification_service,
    slot_service,
    thesis_service,
)

logger = logging.getLogger(__name__)

RESET_KEYWORDS = ["start over", "restart", "reset", "nevermind", "cancel everything", "begin again"]
CANCEL_KEYWORDS = ["cancel", "remove", "delete booking", "undo"]

# GRADED_WORK_REVIEW checked first — "review" maps here, not preparation.
# GENERAL before THESIS — if text has both "help"+"thesis", it's likely just a student asking for general help mentioning thesis.
# GENERAL before PREPARATION so e.g. "question" matches general, not a prep substring.
# PREPARATION keywords still match for intent so Phase 1 can show the deferral message (not offered in type lists).
TYPE_KEYWORDS: dict[ConsultationType, list[str]] = {
    ConsultationType.graded_work_review: [
        "graded work",
        "points",
        "score",
        "grade",
        "how many points",
        "check my grade",
        "see my work",
        "review my exam",
        "review my grade",
        "check my points",
        "my result",
    ],
    ConsultationType.general: [
        "question",
        "don't understand",
        "explain",
        "how to",
        "task",
        "topic",
        "concept",
        "help",
        "don't know",
        "homework",
    ],
    ConsultationType.thesis: [
        "thesis",
        "dissertation",
        "final project",
        "mentor",
        "supervisor",
    ],
    ConsultationType.preparation: [
        "prepare",
        "preparation",
        "study",
        "studying",
        "before the exam",
        "exam prep",
        "prep session",
    ],
}


@dataclass
class ParsedContext:
    professor: Optional[str] = None
    professor_id: Optional[int] = None
    consultation_type: Optional[str] = None
    course: Optional[str] = None
    course_id: Optional[int] = None
    task: Optional[str] = None
    anonymous_question: Optional[str] = None
    is_urgent: bool = False
    failed_parse_count: int = 0
    raw_text: str = ""
    phase: str = "collect"
    pending_session_id: Optional[int] = None
    thesis_topic: Optional[str] = None
    preferred_times: Optional[list[str]] = None

    def to_state(self) -> dict[str, Any]:
        return {
            "professor": self.professor,
            "professor_id": self.professor_id,
            "consultation_type": self.consultation_type,
            "course": self.course,
            "course_id": self.course_id,
            "task": self.task,
            "anonymous_question": self.anonymous_question,
            "is_urgent": self.is_urgent,
            "failed_parse_count": self.failed_parse_count,
            "raw_text": self.raw_text,
            "phase": self.phase,
            "pending_session_id": self.pending_session_id,
            "thesis_topic": self.thesis_topic,
        }

    @classmethod
    def from_state(cls, d: dict[str, Any]) -> ParsedContext:
        return cls(
            professor=d.get("professor"),
            professor_id=d.get("professor_id"),
            consultation_type=d.get("consultation_type"),
            course=d.get("course"),
            course_id=d.get("course_id"),
            task=d.get("task"),
            anonymous_question=d.get("anonymous_question"),
            is_urgent=bool(d.get("is_urgent")),
            failed_parse_count=int(d.get("failed_parse_count") or 0),
            raw_text=d.get("raw_text") or "",
            phase=str(d.get("phase") or "collect"),
            pending_session_id=d.get("pending_session_id"),
            thesis_topic=d.get("thesis_topic"),
        )


def check_cancel_intent(text: str) -> bool:
    t = text.lower()
    negation = any(n in t for n in ["don't want to cancel", "not cancel", "no cancel", "without cancel", "don't cancel"])
    if negation:
        return False
    return any(k in t for k in CANCEL_KEYWORDS)


def match_type(text: str) -> Optional[ConsultationType]:
    t = text.lower()
    for ctype, words in TYPE_KEYWORDS.items():
        for w in words:
            if w in t:
                return ctype
    return None


def extract_description(text: str) -> Optional[str]:
    cleaned = text.strip()
    if len(cleaned) < 12:
        return None
    return cleaned


def extract_task(text: str) -> Optional[str]:
    m = re.search(r"about\s+([^?.!]+)", text.lower())
    if m:
        return m.group(1).strip()[:200]
    return None


def merge_descriptions(existing: Optional[str], new: str) -> Optional[str]:
    if not existing:
        return new if len(new.strip()) > 5 else existing
    return f"{existing}\n{new}".strip()[:4000]


async def _professor_candidates(session: AsyncSession, student_id: int) -> list[User]:
    q = (
        select(User)
        .join(CourseProfessor, CourseProfessor.professor_id == User.id)
        .join(CourseStudent, CourseStudent.course_id == CourseProfessor.course_id)
        .where(
            CourseStudent.student_id == student_id,
            User.role == UserRole.professor,
            User.is_active.is_(True),
        )
        .distinct()
    )
    return list((await session.scalars(q)).all())


async def _all_professors(session: AsyncSession) -> list[User]:
    return list(
        (
            await session.scalars(
                select(User).where(User.role == UserRole.professor, User.is_active.is_(True))
            )
        ).all()
    )


async def _fuzzy_match_from_list(text: str, profs: list[User]) -> tuple[Optional[str], Optional[int]]:
    if not profs:
        return None, None
    tokens = re.findall(r"[A-Za-zćčžšđČĆŽŠĐ]+", text)
    best: Optional[User] = None
    best_score = 0.0
    for p in profs:
        full = f"{p.first_name} {p.last_name}".lower()
        last = p.last_name.lower()
        for tok in tokens:
            if len(tok) < 2:
                continue
            for part in full.split():
                score = difflib.SequenceMatcher(None, tok.lower(), part).ratio()
                if score > best_score and score >= 0.6:
                    best_score = score
                    best = p
            if difflib.SequenceMatcher(None, tok.lower(), last).ratio() >= 0.6:
                best = p
                best_score = 0.9
    if best:
        return f"{best.first_name} {best.last_name}", best.id
    return None, None


async def match_professor(
    session: AsyncSession, text: str, student_id: int
) -> tuple[Optional[str], Optional[int]]:
    profs = await _professor_candidates(session, student_id)
    return await _fuzzy_match_from_list(text, profs)


async def match_professor_any(
    session: AsyncSession, text: str
) -> tuple[Optional[str], Optional[int]]:
    """Match any active professor — used for thesis (not restricted to student's courses)."""
    profs = await _all_professors(session)
    return await _fuzzy_match_from_list(text, profs)


async def _student_prof_courses(
    session: AsyncSession, professor_id: int, student_id: int
) -> list[Course]:
    q = (
        select(Course)
        .join(CourseProfessor, CourseProfessor.course_id == Course.id)
        .join(CourseStudent, CourseStudent.course_id == Course.id)
        .where(
            CourseProfessor.professor_id == professor_id,
            CourseStudent.student_id == student_id,
        )
    )
    return list((await session.scalars(q)).all())


async def match_course(
    session: AsyncSession, text: str, professor_id: int, student_id: int
) -> tuple[Optional[str], Optional[int]]:
    courses = await _student_prof_courses(session, professor_id, student_id)
    if not courses:
        return None, None
    t = text.lower()
    for c in courses:
        if c.name.lower() in t or c.code.lower() in t:
            return c.name, c.id
    names = [c.name for c in courses]
    close = difflib.get_close_matches(t[:80], [n.lower() for n in names], n=1, cutoff=0.5)
    if close:
        for c in courses:
            if c.name.lower() == close[0]:
                return c.name, c.id
    return None, None


async def parse_first_message(session: AsyncSession, text: str, student_id: int) -> ParsedContext:
    ctx = ParsedContext(raw_text=text)
    mt = match_type(text)
    ctx.consultation_type = mt.value if mt else None

    if mt == ConsultationType.thesis:
        ctx.professor, ctx.professor_id = await match_professor_any(session, text)
    else:
        ctx.professor, ctx.professor_id = await match_professor(session, text, student_id)

    if ctx.professor_id and mt != ConsultationType.thesis:
        ctx.course, ctx.course_id = await match_course(session, text, ctx.professor_id, student_id)

    ctx.anonymous_question = extract_description(text)
    tl = text.lower()
    ctx.is_urgent = any(k in tl for k in ["urgent", "asap", "today", "emergency"])
    if mt == ConsultationType.general:
        ctx.task = extract_task(text)
    return ctx


async def process_reply(
    session: AsyncSession, ctx: ParsedContext, new_text: str, student_id: int
) -> ParsedContext:
    mt = match_type(new_text)
    # Always refresh type from the latest message when keywords match, so stale
    # conversation state (e.g. PREPARATION from Phase 2 experiments) cannot block
    # a new GENERAL / thesis / review intent.
    if mt is not None:
        ctx.consultation_type = mt.value

    ctype = ConsultationType(ctx.consultation_type) if ctx.consultation_type else None

    if not ctx.professor_id:
        if ctype == ConsultationType.thesis:
            p, pid = await match_professor_any(session, new_text)
        else:
            p, pid = await match_professor(session, new_text, student_id)
        if pid:
            ctx.professor, ctx.professor_id = p, pid

    if not ctx.course_id and ctx.professor_id and ctype != ConsultationType.thesis:
        c, cid = await match_course(session, new_text, ctx.professor_id, student_id)
        if cid:
            ctx.course, ctx.course_id = c, cid

    if not ctx.task:
        t = extract_task(new_text)
        if t:
            ctx.task = t

    ctx.anonymous_question = merge_descriptions(ctx.anonymous_question, new_text)
    ctx.raw_text = f"{ctx.raw_text}\n{new_text}".strip()[:8000]
    return ctx


async def determine_next_question(
    session: AsyncSession, ctx: ParsedContext, student_id: int
) -> Optional[str]:
    """Returns next question to ask, or None if all required info is collected. May auto-fill ctx."""
    for _ in range(6):
        ctype = ConsultationType(ctx.consultation_type) if ctx.consultation_type else None

        if not ctx.professor_id:
            if ctype == ConsultationType.thesis:
                profs = await _all_professors(session)
            else:
                profs = await _professor_candidates(session, student_id)

            if len(profs) == 1:
                ctx.professor = f"{profs[0].first_name} {profs[0].last_name}"
                ctx.professor_id = profs[0].id
                continue

            if ctype == ConsultationType.thesis:
                names = ", ".join(f"{p.first_name} {p.last_name}" for p in profs[:5])
                return f"Which professor for thesis supervision? ({names})"
            sug = [f"{p.first_name} {p.last_name}" for p in profs[:5]]
            return f"Which professor? ({', '.join(sug)})" if sug else "Which professor would you like to book a consultation with?"

        if not ctx.consultation_type:
            exam = await slot_service.is_exam_period(session, date.today())
            avail = slot_service.get_available_types(date.today(), exam)
            # Exclude preparation from user-facing list (Phase 2 deferral)
            avail = [a for a in avail if a != ConsultationType.preparation]
            labels = " / ".join(a.value for a in avail)
            return f"What is the consultation about? ({labels})"

        if ctype != ConsultationType.thesis:
            if not ctx.course_id:
                courses = await _student_prof_courses(session, ctx.professor_id, student_id)
                if len(courses) == 1:
                    ctx.course = courses[0].name
                    ctx.course_id = courses[0].id
                    continue
                names = ", ".join(c.name for c in courses) or "your courses"
                return f"Which course? ({names})"

        if ctype == ConsultationType.general and not ctx.task:
            return "Which topic or task are you asking about? (e.g. recursion, SQL joins...)"

        break

    return None


def _extracted_any(ctx: ParsedContext, new_message_parsed: ParsedContext) -> bool:
    if new_message_parsed.professor_id and not ctx.professor_id:
        return True
    if new_message_parsed.consultation_type and not ctx.consultation_type:
        return True
    if new_message_parsed.course_id and not ctx.course_id:
        return True
    if new_message_parsed.task and not ctx.task:
        return True
    if new_message_parsed.anonymous_question and len(new_message_parsed.anonymous_question) > 10:
        return True
    return False


async def get_or_create_conversation(session: AsyncSession, student_id: int) -> Conversation:
    conv = await session.scalar(select(Conversation).where(Conversation.student_id == student_id))
    if not conv:
        conv = Conversation(student_id=student_id, state={})
        session.add(conv)
        await session.flush()
    return conv


async def _persist_response_state(
    session: AsyncSession,
    conv: Conversation,
    response: dict[str, Any],
    fallback_state: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    if response.get("phase") == "done":
        conv.state = {}
        response["context"] = {}
    else:
        conv.state = response.get("context", fallback_state or {})
    await session.flush()
    return response


async def _handle_thesis_flow(
    session: AsyncSession, ctx: ParsedContext, user: User
) -> Optional[dict[str, Any]]:
    """
    Handle thesis-specific business rules. Mutates ctx.phase when needed.
    Returns a response dict to send immediately, or None to proceed to slot display.
    """
    if not user.is_final_year:
        return {
            "message": "Thesis consultations are only available to final year students. "
                       "Contact the admin to update your student status.",
            "slots": [],
            "chips": [],
            "phase": "done",
            "manual_form": False,
            "context": ctx.to_state(),
        }

    if not ctx.professor_id:
        return None  # determine_next_question handles professor prompt

    # Find application, prioritizing active > pending > rejected
    apps = list((await session.scalars(
        select(ThesisApplication).where(
            ThesisApplication.student_id == user.id,
            ThesisApplication.professor_id == ctx.professor_id,
        )
    )).all())

    # Prioritize by status: active first, then pending, then rejected
    app = None
    for status in [ThesisApplicationStatus.active, ThesisApplicationStatus.pending, ThesisApplicationStatus.rejected]:
        for a in apps:
            if a.status == status:
                app = a
                break
        if app:
            break

    if app and app.status == ThesisApplicationStatus.rejected:
        prof = await session.get(User, ctx.professor_id)
        prof_name = f"{prof.first_name} {prof.last_name}" if prof else "the professor"
        ctx.professor_id = None
        ctx.professor = None
        return {
            "message": f"Prof. {prof_name} has declined thesis supervision. Please choose a different professor.",
            "slots": [],
            "chips": [],
            "phase": "collect",
            "manual_form": False,
            "context": ctx.to_state(),
        }

    if not app or app.status != ThesisApplicationStatus.active:
        # Thesis supervision申请 only through Thesis page, not chatbot
        return {
            "message": "Thesis supervision申请 must be submitted through the Thesis page. "
                       "This chat is only for consultations on your approved thesis topic.",
            "slots": [],
            "chips": [],
            "phase": "done",
            "manual_form": False,
            "context": ctx.to_state(),
        }

    if app.status == ThesisApplicationStatus.pending:
        return {
            "message": "Your thesis application is waiting for the professor's decision. "
                       "After approval, you can book thesis consultation slots (you may receive an automatic booking).",
            "slots": [],
            "chips": [],
            "phase": "done",
            "manual_form": False,
            "context": ctx.to_state(),
        }

    return None


async def _register_preparation_vote(
    session: AsyncSession,
    student_id: int,
    course_id: int,
    professor_id: int,
    ctx: ParsedContext,
) -> dict[str, Any]:
    today = date.today()
    event = await session.scalar(
        select(AcademicEvent)
        .where(AcademicEvent.course_id == course_id, AcademicEvent.event_date >= today)
        .order_by(AcademicEvent.event_date)
    )

    if not event:
        return {
            "message": "No upcoming exam found for this course. "
                       "Preparation sessions are tied to scheduled exams.",
            "slots": [],
            "chips": [],
            "phase": "done",
            "manual_form": False,
            "context": ctx.to_state(),
        }

    if not ctx.preferred_times:
        ctx.phase = "preparation_times"
        return {
            "message": "What times work best for you? (e.g. Monday 10-12, Wednesday 14-16)",
            "slots": [],
            "chips": [],
            "phase": "preparation_times",
            "manual_form": False,
            "context": ctx.to_state(),
        }

    votes_before = int(
        await session.scalar(
            select(func.count()).select_from(PreparationVote).where(
                PreparationVote.academic_event_id == event.id
            )
        )
        or 0
    )

    existing_vote = await session.scalar(
        select(PreparationVote).where(
            PreparationVote.student_id == student_id,
            PreparationVote.academic_event_id == event.id,
        )
    )
    is_new_vote = not existing_vote
    if is_new_vote:
        session.add(PreparationVote(
            student_id=student_id,
            course_id=course_id,
            academic_event_id=event.id,
            preferred_times=ctx.preferred_times,
        ))
        await session.flush()

    vote_count = int(
        await session.scalar(
            select(func.count()).select_from(PreparationVote).where(
                PreparationVote.academic_event_id == event.id
            )
        ) or 0
    )
    threshold = await slot_service.preparation_vote_threshold_needed(session, course_id)

    sr = await session.scalar(
        select(SchedulingRequest).where(
            SchedulingRequest.professor_id == professor_id,
            SchedulingRequest.course_id == course_id,
            SchedulingRequest.academic_event_id == event.id,
            SchedulingRequest.status == SchedulingRequestStatus.pending,
        )
    )
    if not sr:
        deadline = datetime.combine(event.event_date, datetime.min.time()).replace(tzinfo=UTC) - timedelta(hours=48)
        sr = SchedulingRequest(
            professor_id=professor_id,
            course_id=course_id,
            academic_event_id=event.id,
            vote_count=vote_count,
            status=SchedulingRequestStatus.pending,
            deadline_at=deadline,
        )
        session.add(sr)
    else:
        sr.vote_count = vote_count
    await session.flush()

    if is_new_vote:
        st = await session.get(User, student_id)
        st_name = f"{st.first_name} {st.last_name}" if st else "A student"
        await notification_service.notify_course_students_except(
            session,
            course_id,
            student_id,
            f"{st_name} requested exam preparation for '{event.name}' on {event.event_date}. "
            "You can add your interest via the chatbot (preparation consultation).",
            notification_type="preparation",
        )

    if vote_count >= threshold and votes_before < threshold:
        await notification_service.notify_user(
            session,
            professor_id,
            f"Threshold reached: {vote_count} students requested a preparation session for "
            f"'{event.name}' ({event.event_date}). Please schedule one.",
            notification_type="scheduling_request",
        )
    elif is_new_vote and vote_count == 1 and threshold > 1:
        await notification_service.notify_user(
            session,
            professor_id,
            f"A student started interest in a preparation session before '{event.name}' "
            f"({event.event_date}). More votes may follow — you will be notified when the class threshold is met.",
            notification_type="scheduling_request",
        )

    return {
        "message": f"Your vote for a preparation session before '{event.name}' ({event.event_date}) "
                   f"has been registered (vote #{vote_count} of {threshold} needed). "
                   "The professor will be notified when enough students request it.",
        "slots": [],
        "chips": [],
        "phase": "done",
        "manual_form": False,
        "context": ctx.to_state(),
    }


async def process(
    text: str,
    user_id: int,
    session: AsyncSession,
    *,
    structured: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Main chat entry — returns JSON-serializable assistant payload."""
    user = await session.get(User, user_id)
    if not user or user.role != UserRole.student:
        raise ValueError("Only students may use the booking chat")

    t_lower = text.strip().lower()

    # Reset conversation
    if not structured and any(k in t_lower for k in RESET_KEYWORDS):
        conv = await get_or_create_conversation(session, user_id)
        conv.state = {}
        await session.flush()
        return {
            "message": "Starting fresh. What do you need help with?",
            "slots": [],
            "chips": [],
            "phase": "collect",
            "manual_form": False,
            "context": {},
        }

    # Join waitlist
    if not structured and t_lower.startswith("join_waitlist:"):
        try:
            session_id = int(text.split(":", 1)[1].strip())
        except (ValueError, IndexError):
            return {"message": "Invalid waitlist request.", "slots": [], "chips": [], "phase": "collect", "manual_form": False, "context": {}}

        cs = await session.get(ConsultationSession, session_id)
        if not cs:
            return {"message": "Session not found.", "slots": [], "chips": [], "phase": "collect", "manual_form": False, "context": {}}

        existing_wl = await session.scalar(
            select(Waitlist).where(
                Waitlist.student_id == user_id,
                Waitlist.session_id == session_id,
                Waitlist.notified.is_(False),
            )
        )
        if existing_wl:
            return {
                "message": f"You're already on the waitlist (position #{existing_wl.position_hint}).",
                "slots": [],
                "chips": [],
                "phase": "done",
                "manual_form": False,
                "context": {},
            }

        pos = int(
            await session.scalar(
                select(func.count()).select_from(Waitlist).where(Waitlist.session_id == session_id)
            ) or 0
        ) + 1
        session.add(Waitlist(
            student_id=user_id,
            professor_id=cs.professor_id,
            session_id=session_id,
            preferred_date=cs.session_date,
            consultation_type=cs.consultation_type,
            course_id=cs.course_id,
            position_hint=pos,
        ))
        await session.flush()
        return {
            "message": f"You've joined the waitlist at position #{pos}. We'll notify you if a spot opens.",
            "slots": [],
            "chips": [],
            "phase": "done",
            "manual_form": False,
            "context": {},
        }

    # Confirm slot
    if not structured and t_lower.startswith("confirm_slot:"):
        try:
            session_id = int(text.split(":", 1)[1].strip())
        except (ValueError, IndexError):
            return {"message": "Invalid slot selection.", "slots": [], "chips": [], "phase": "collect", "manual_form": False, "context": {}}

        conv = await get_or_create_conversation(session, user_id)
        ctx = ParsedContext.from_state(dict(conv.state or {}))
        try:
            b = await booking_service.create_booking(
                session,
                student=user,
                session_id=session_id,
                task=ctx.task,
                anonymous_question=ctx.anonymous_question,
                is_urgent=ctx.is_urgent,
                group_size=1,
            )
            cs = await session.get(ConsultationSession, session_id)
            prof = await session.get(User, cs.professor_id) if cs else None
            prof_name = f"{prof.first_name} {prof.last_name}" if prof else ctx.professor or "the professor"
            date_str = cs.session_date.isoformat() if cs else "?"
            time_str = f"{cs.time_from.strftime('%H:%M')}–{cs.time_to.strftime('%H:%M')}" if cs else ""
            conv.state = {}
            await session.flush()
            return {
                "message": f"Confirmed — booking #{b.id}. Session: {date_str} {time_str} with {prof_name}.",
                "slots": [],
                "chips": [],
                "phase": "done",
                "manual_form": False,
                "context": {},
            }
        except ValueError as e:
            return {
                "message": str(e),
                "slots": [],
                "chips": [],
                "phase": "collect",
                "manual_form": False,
                "context": ctx.to_state(),
            }

    conv = await get_or_create_conversation(session, user_id)
    state = dict(conv.state or {})

    # Cancel intent
    if not structured and check_cancel_intent(text):
        bookings = list(
            (
                await session.scalars(
                    select(Booking).where(
                        Booking.student_id == user_id,
                        Booking.status == BookingStatus.active,
                    )
                )
            ).all()
        )
        chips = [{"id": b.id, "label": f"Booking #{b.id}"} for b in bookings]
        snap = ParsedContext.from_state(state) if state else ParsedContext()
        return {
            "message": "Pick a booking to cancel:" if chips else "You have no active bookings.",
            "chips": chips,
            "phase": "cancel_pick",
            "manual_form": state.get("failed_parse_count", 0) >= 2,
            "context": snap.to_state(),
        }

    if structured:
        merged = {**state, **{k: v for k, v in structured.items() if v is not None}}
        state = merged
        conv.state = merged
        ctx = ParsedContext.from_state(state)
        ctx.failed_parse_count = 0
    elif not state:
        ctx = await parse_first_message(session, text, user_id)
        extracted = bool(
            ctx.professor_id
            or ctx.consultation_type
            or ctx.course_id
            or ctx.task
            or (ctx.anonymous_question and len(ctx.anonymous_question) > 10)
        )
        ctx.failed_parse_count = 0 if extracted else (1 if text.strip() else 0)
    else:
        prev_phase = state.get("phase", "collect")
        prev_snap = ParsedContext.from_state(state)

        # Thesis topic collection phase — the user's message IS the topic
        if (
            prev_phase == "thesis_topic"
            and prev_snap.consultation_type == ConsultationType.thesis.value
            and prev_snap.professor_id
        ):
            prev_snap.thesis_topic = text.strip()[:500]
            ctx = prev_snap
            existing_app = await session.scalar(
                select(ThesisApplication).where(
                    ThesisApplication.student_id == user_id,
                    ThesisApplication.professor_id == prev_snap.professor_id,
                )
            )
            if not existing_app:
                if not await thesis_service.professor_has_open_thesis_spot(session, prev_snap.professor_id):
                    prof_u = await session.get(User, prev_snap.professor_id)
                    pn = (
                        f"{prof_u.first_name} {prof_u.last_name}"
                        if prof_u
                        else (prev_snap.professor or "This professor")
                    )
                    return await _persist_response_state(
                        session,
                        conv,
                        {
                            "message": f"{pn} has no open thesis supervision spots. Try another professor.",
                            "slots": [],
                            "chips": [],
                            "phase": "done",
                            "manual_form": False,
                            "context": {},
                        },
                        prev_snap.to_state(),
                    )
                app = ThesisApplication(
                    student_id=user_id,
                    professor_id=prev_snap.professor_id,
                    topic_description=prev_snap.thesis_topic,
                    status=ThesisApplicationStatus.pending,
                )
                session.add(app)
                await session.flush()
                await notification_service.notify_user(
                    session,
                    prev_snap.professor_id,
                    f"New thesis application from {user.first_name} {user.last_name}: "
                    f"{prev_snap.thesis_topic[:120]}",
                    notification_type="thesis",
                )
            ctx.phase = "collect"
            ctx.failed_parse_count = 0
        # Preparation times collection phase
        elif (
            prev_phase == "preparation_times"
            and prev_snap.consultation_type == ConsultationType.preparation.value
            and prev_snap.professor_id
            and prev_snap.course_id
        ):
            times = [t.strip() for t in text.split(",") if t.strip()]
            prev_snap.preferred_times = times[:5]  # limit to 5
            ctx = prev_snap
            ctx.phase = "collect"
            ctx.failed_parse_count = 0
        else:
            ctx = await process_reply(session, prev_snap, text, user_id)
            delta = await parse_first_message(session, text, user_id)
            extracted = _extracted_any(prev_snap, delta)
            ctx.failed_parse_count = 0 if extracted else (int(state.get("failed_parse_count") or 0) + 1)

    # Thesis-specific business rules
    if ctx.consultation_type == ConsultationType.thesis.value:
        thesis_resp = await _handle_thesis_flow(session, ctx, user)
        if thesis_resp is not None:
            return await _persist_response_state(session, conv, thesis_resp, ctx.to_state())

    # Determine next question (may auto-fill professor/course on ctx)
    nq = await determine_next_question(session, ctx, user_id)
    if nq:
        conv.state = {**ctx.to_state(), "failed_parse_count": ctx.failed_parse_count}
        await session.flush()
        hint = (
            "I wasn't able to understand your request. Try writing something like: "
            "'I want a consultation with prof. Marković about databases, I have a question about SQL joins.'"
        )
        msg = hint if ctx.failed_parse_count >= 2 and len(text.strip()) < 5 else nq
        return {
            "message": msg,
            "manual_form": ctx.failed_parse_count >= 2,
            "phase": "collect",
            "context": conv.state,
        }

    # Preparation: disabled for Phase 1 — only when context explicitly requests it.
    if ctx.consultation_type == ConsultationType.preparation.value:
        return await _persist_response_state(session, conv, {
            "message": "Exam preparation consultations are not available yet.",
            "slots": [],
            "chips": [],
            "phase": "done",
            "manual_form": False,
            "context": {},
        }, ctx.to_state())

    ctype = ConsultationType(ctx.consultation_type)  # type: ignore[arg-type]

    # Preparation vote registration: kept for Phase 2, not called in Phase 1
    # if ctype == ConsultationType.preparation and ctx.professor_id and ctx.course_id:
    #     vote_resp = await _register_preparation_vote(
    #         session, user_id, ctx.course_id, ctx.professor_id, ctx
    #     )
    #     return await _persist_response_state(session, conv, vote_resp, ctx.to_state())

    try:
        slots = await slot_service.get_free_slots(
            session,
            professor_id=ctx.professor_id,  # type: ignore[arg-type]
            course_id=ctx.course_id,
            ctype=ctype,
            group_size=1,
            student_id=user_id,
            next_weeks=3,
        )
    except ValueError as e:
        conv.state = {**ctx.to_state(), "failed_parse_count": ctx.failed_parse_count}
        await session.flush()
        return {"message": str(e), "manual_form": False, "phase": "collect", "context": conv.state}

    if not slots:
        # Graded work review: specific no-session message
        if ctype == ConsultationType.graded_work_review:
            return await _persist_response_state(session, conv, {
                "message": "No graded work review session has been announced yet. "
                           "You'll receive a notification when your professor announces one.",
                "slots": [],
                "chips": [],
                "phase": "done",
                "manual_form": False,
                "context": ctx.to_state(),
            }, ctx.to_state())

        # Thesis: no available slots
        if ctype == ConsultationType.thesis:
            return await _persist_response_state(session, conv, {
                "message": "No thesis consultation slots available right now. "
                           "Please contact your thesis mentor directly or check again later.",
                "slots": [],
                "chips": [],
                "phase": "done",
                "manual_form": False,
                "context": ctx.to_state(),
            }, ctx.to_state())

        # Other types: offer waitlist if full sessions exist
        if ctx.professor_id:
            full_sessions = await slot_service.get_full_sessions(
                session,
                professor_id=ctx.professor_id,
                course_id=ctx.course_id,
                ctype=ctype,
                next_weeks=3,
            )
            if full_sessions:
                chips = [
                    {
                        "id": s.id,
                        "label": f"Waitlist: {s.session_date} {s.time_from.strftime('%H:%M')}–{s.time_to.strftime('%H:%M')}",
                        "action": f"join_waitlist:{s.id}",
                    }
                    for s in full_sessions[:12]
                ]
                conv.state = {**ctx.to_state(), "phase": "waitlist_offer"}
                await session.flush()
                return {
                    "message": "All slots are full. Would you like to join the waitlist for one of these sessions?",
                    "slots": [],
                    "chips": chips,
                    "phase": "waitlist_offer",
                    "manual_form": False,
                    "context": conv.state,
                }

        return await _persist_response_state(session, conv, {
            "message": "No free slots in the next 3 weeks.",
            "slots": [],
            "chips": [],
            "phase": "done",
            "manual_form": False,
            "context": ctx.to_state(),
        }, ctx.to_state())

    chips = [
        {
            "id": s.id,
            "label": f"{s.session_date} {s.time_from.strftime('%H:%M')}–{s.time_to.strftime('%H:%M')}",
        }
        for s in slots[:24]
    ]
    conv.state = {**ctx.to_state(), "phase": "pick_slot", "failed_parse_count": 0}
    await session.flush()
    return {
        "message": "Here are available slots — pick one:",
        "slots": chips,
        "phase": "pick_slot",
        "manual_form": False,
        "context": conv.state,
    }
