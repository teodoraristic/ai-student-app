"""Rule-based chatbot — all parsing and responses live here."""

from __future__ import annotations

import difflib
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dates import utc_today
from backend.db.models import (
    AcademicEvent,
    AcademicEventType,
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
)
from backend.services import (
    booking_service,
    config_service,
    notification_service,
    slot_service,
    waitlist_service,
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

# Words from typical booking phrases — must not fuzzy-match name parts (e.g. "topic" ~ "Petrovic").
_PROF_FUZZY_STOPWORDS: frozenset[str] = frozenset({
    "i", "a", "an", "to", "for", "of", "the", "and", "or", "in", "on", "at", "my", "me", "we", "is", "it", "be",
    "need", "want", "help", "with", "have", "has", "book", "booking", "consultation", "consultations",
    "general", "thesis", "course", "courses", "topic", "topics", "task", "tasks", "question", "questions",
    "homework", "exam", "grade", "review", "about", "please", "thanks", "student", "students",
    "professor", "professors", "understand", "explain", "concept", "dissertation", "mentor", "supervisor",
    "prepare", "preparation", "studying", "session", "points", "score", "dont", "how", "what", "when", "why",
    "some", "any", "this", "that", "from", "into", "your", "our", "their", "would", "could", "should",
})

# Avoid weak SequenceMatcher hits (e.g. "topic" vs "Petrovic" ≈ 0.62).
_PROF_TOKEN_SIMILARITY_MIN: float = 0.75


@dataclass
class ParsedContext:
    professor: Optional[str] = None
    professor_id: Optional[int] = None
    consultation_type: Optional[str] = None
    course: Optional[str] = None
    course_id: Optional[int] = None
    task: Optional[str] = None
    anonymous_question: Optional[str] = None
    failed_parse_count: int = 0
    raw_text: str = ""
    phase: str = "collect"
    pending_session_id: Optional[int] = None
    picked_date: Optional[str] = None
    preferred_times: Optional[list[str]] = None
    group_join_session_id: Optional[int] = None
    academic_event_id: Optional[int] = None

    def to_state(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "professor": self.professor,
            "professor_id": self.professor_id,
            "consultation_type": self.consultation_type,
            "course": self.course,
            "course_id": self.course_id,
            "task": self.task,
            "anonymous_question": self.anonymous_question,
            "failed_parse_count": self.failed_parse_count,
            "raw_text": self.raw_text,
            "phase": self.phase,
            "pending_session_id": self.pending_session_id,
            "picked_date": self.picked_date,
            "group_join_session_id": self.group_join_session_id,
        }
        if self.academic_event_id is not None:
            d["academic_event_id"] = self.academic_event_id
        return d

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
            failed_parse_count=int(d.get("failed_parse_count") or 0),
            raw_text=d.get("raw_text") or "",
            phase=str(d.get("phase") or "collect"),
            pending_session_id=d.get("pending_session_id"),
            picked_date=d.get("picked_date"),
            group_join_session_id=d.get("group_join_session_id"),
            academic_event_id=d.get("academic_event_id") if "academic_event_id" in d else None,
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


def _is_boilerplate_booking_message(text: str) -> bool:
    """UI suggestion text or other generic phrases that must not carry stale booking context."""
    t = text.strip().lower().rstrip(".,!?")
    if not t:
        return False
    if t in {
        "i need help with a course topic",
        "i need a thesis consultation",
        "i want to book general consultations",
        "i want to book a general consultation",
    }:
        return True
    if re.match(r"^i want to book (a )?general consultations?$", t):
        return True
    if re.match(r"^i need help with (a )?course topics?$", t):
        return True
    return False


def _message_is_scheduling_transport(text: str) -> bool:
    tl = text.strip().lower()
    return any(
        tl.startswith(p)
        for p in (
            "pick_date:",
            "select_slot:",
            "confirm_booking:",
            "confirm_slot:",
            "join_waitlist:",
            "join_group_session:",
            "pick_prep_exam:",
        )
    )


def _topic_signature_for_group_match(task: Optional[str], anonymous_question: Optional[str]) -> str:
    """
    Normalize topic for equality. Prefer explicit task (post task_collect); otherwise fall back
    to anonymous_question so we do not miss a match when one student only has a long first message
    and the other answered with the same topic in the task field.
    """

    def norm(s: Optional[str]) -> str:
        return " ".join((s or "").split()).strip().casefold()

    t = norm(task)
    if t:
        return t
    return norm(anonymous_question)


async def _find_peer_general_group_booking(
    session: AsyncSession,
    *,
    student_id: int,
    ctx: ParsedContext,
) -> Optional[tuple[ConsultationSession, Booking]]:
    """
    Another student's active general booking for the same professor, course, and topic,
    on a session that still has capacity (shared group slot).
    """
    if ctx.consultation_type != ConsultationType.general.value:
        return None
    pid, cid = ctx.professor_id, ctx.course_id
    if not pid or not cid:
        return None
    sig = _topic_signature_for_group_match(ctx.task, ctx.anonymous_question)
    if len(sig) < 2:
        return None

    rows = (
        await session.execute(
            select(Booking, ConsultationSession)
            .join(ConsultationSession, ConsultationSession.id == Booking.session_id)
            .where(
                Booking.student_id != student_id,
                Booking.status == BookingStatus.active,
                ConsultationSession.professor_id == pid,
                ConsultationSession.course_id == cid,
                ConsultationSession.consultation_type == ConsultationType.general,
                ConsultationSession.session_date >= utc_today(),
            )
        )
    ).all()

    matches: list[tuple[ConsultationSession, Booking]] = []
    for b, cs in rows:
        if _topic_signature_for_group_match(b.task, b.anonymous_question) != sig:
            continue
        used = await slot_service._used_capacity(session, cs.id)
        if used < cs.capacity:
            matches.append((cs, b))
    if not matches:
        return None
    matches.sort(key=lambda x: (x[0].session_date, x[0].time_from, x[0].id))
    return matches[0]


async def _group_join_offer_message(session: AsyncSession, cs: ConsultationSession, ctx: ParsedContext) -> str:
    prof = await session.get(User, cs.professor_id)
    prof_name = f"{prof.first_name} {prof.last_name}" if prof else (ctx.professor or "the professor")
    course_name = ""
    if ctx.course_id:
        c = await session.get(Course, ctx.course_id)
        if c:
            course_name = f" for {c.name}"
    topic = (ctx.task or ctx.anonymous_question or "").strip() or "the same topic"
    date_str = cs.session_date.strftime("%A %d %B")
    time_str = f"{cs.time_from.strftime('%H:%M')}–{cs.time_to.strftime('%H:%M')}"
    return (
        f"Another student already booked {prof_name}{course_name} on {date_str} at {time_str} "
        f"for the same topic ({topic}).\n\n"
        f"Would you like to join that session as a group, or pick a different time?"
    )


def _ascii_fold(s: str) -> str:
    """Strip combining marks so e.g. 'Marković' and 'Markovic' can both be matched in student text."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def strip_professor_from_topic_text(
    text: Optional[str], first_name: str, last_name: str
) -> Optional[str]:
    """
    Remove the booked professor's name tokens from topic / anonymous question text so
    grouping and UI show the subject matter only (not e.g. the professor's last name).
    """
    if not text or not str(text).strip():
        return None
    fi = (first_name or "").strip()
    la = (last_name or "").strip()
    if not fi or not la:
        return text.strip() or None

    result = text.strip()
    last_variants = {la, _ascii_fold(la)}
    last_variants = {v for v in last_variants if v}

    for lv in sorted(last_variants, key=len, reverse=True):
        result = re.sub(rf"(?i){re.escape(fi)}\s+{re.escape(lv)}", " ", result)
        result = re.sub(rf"(?i){re.escape(lv)}\s*,\s*{re.escape(fi)}", " ", result)
    for lv in sorted(last_variants, key=len, reverse=True):
        result = re.sub(rf"(?i)\b{re.escape(lv)}\b", " ", result)
    result = re.sub(rf"(?i)\b{re.escape(fi)}\b", " ", result)

    result = re.sub(r"[\s,;–—\-]+", " ", result).strip(" —-,;\t")
    result = re.sub(r"\s+", " ", result).strip()
    return result or None


async def _apply_topic_professor_cleanup(session: AsyncSession, ctx: ParsedContext) -> None:
    if not ctx.professor_id:
        return
    u = await session.get(User, ctx.professor_id)
    if not u:
        return
    ctx.task = strip_professor_from_topic_text(ctx.task, u.first_name, u.last_name)
    ctx.anonymous_question = strip_professor_from_topic_text(
        ctx.anonymous_question, u.first_name, u.last_name
    )


async def _sanitize_state_dict(session: AsyncSession, state: dict[str, Any]) -> dict[str, Any]:
    """Strip matched professor names from task / anonymous_question before persisting conversation state."""
    ctx = ParsedContext.from_state(state)
    await _apply_topic_professor_cleanup(session, ctx)
    return {
        **state,
        "task": ctx.task,
        "anonymous_question": ctx.anonymous_question,
    }


def extract_description(text: str) -> Optional[str]:
    cleaned = text.strip()
    if len(cleaned) < 12:
        return None
    if _is_boilerplate_booking_message(cleaned):
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
            tl = tok.lower()
            if len(tl) < 2 or tl in _PROF_FUZZY_STOPWORDS:
                continue
            for part in full.split():
                score = difflib.SequenceMatcher(None, tl, part).ratio()
                if score > best_score and score >= _PROF_TOKEN_SIMILARITY_MIN:
                    best_score = score
                    best = p
            last_score = difflib.SequenceMatcher(None, tl, last).ratio()
            if last_score > best_score and last_score >= _PROF_TOKEN_SIMILARITY_MIN:
                best_score = last_score
                best = p
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

    if not _is_boilerplate_booking_message(new_text):
        ctx.anonymous_question = merge_descriptions(ctx.anonymous_question, new_text)
    ctx.raw_text = f"{ctx.raw_text}\n{new_text}".strip()[:8000]
    return ctx


async def determine_next_question(
    session: AsyncSession, ctx: ParsedContext, student_id: int
) -> Optional[str]:
    """Returns next question to ask, or None if all required info is collected. May auto-fill ctx."""
    for _ in range(6):
        ctype = ConsultationType(ctx.consultation_type) if ctx.consultation_type else None

        if not ctx.consultation_type:
            avail = slot_service.get_available_types(utc_today())
            # Exclude preparation from user-facing list (Phase 2 deferral)
            avail = [a for a in avail if a != ConsultationType.preparation]
            labels = " / ".join(a.value for a in avail)
            return f"What kind of consultation is this? ({labels})"

        if not ctx.professor_id:
            if ctype == ConsultationType.thesis:
                profs = await _all_professors(session)
            else:
                profs = await _professor_candidates(session, student_id)

            # Only graded-work review may infer the sole instructor; general consultations
            # must always ask so vague template messages do not skip professor/course.
            if len(profs) == 1 and ctype == ConsultationType.graded_work_review:
                ctx.professor = f"{profs[0].first_name} {profs[0].last_name}"
                ctx.professor_id = profs[0].id
                continue

            if ctype == ConsultationType.thesis:
                names = ", ".join(f"{p.first_name} {p.last_name}" for p in profs[:5])
                return f"Which professor for your thesis consultation? ({names})"
            sug = [f"{p.first_name} {p.last_name}" for p in profs[:5]]
            return f"Which professor? ({', '.join(sug)})" if sug else "Which professor would you like to book a consultation with?"

        if ctype in (ConsultationType.general, ConsultationType.graded_work_review, ConsultationType.preparation):
            shared = await _student_prof_courses(session, ctx.professor_id, student_id)  # type: ignore[arg-type]
            if not shared:
                ctx.professor_id = None
                ctx.professor = None
                ctx.course_id = None
                ctx.course = None
                return (
                    "That person is not one of your course instructors, so we cannot schedule this here. "
                    "Please choose a professor who teaches you."
                )

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
            ctx.phase = "task_collect"
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
    # conversations.student_id has no unique constraint — duplicate rows must not use scalar().
    conv = (
        await session.scalars(
            select(Conversation)
            .where(Conversation.student_id == student_id)
            .order_by(Conversation.id.asc())
            .limit(1)
        )
    ).first()
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
        raw = dict(response.get("context", fallback_state or {}))
        cleaned = await _sanitize_state_dict(session, raw)
        response["context"] = cleaned
        conv.state = cleaned
    await session.flush()
    return response


async def _autofill_thesis_mentor_if_approved(
    session: AsyncSession,
    ctx: ParsedContext,
    user: User,
) -> None:
    """
    When the student has an active thesis supervision record, default thesis consultations
    to that mentor so they are not prompted to pick among all professors.
    """
    if ctx.consultation_type != ConsultationType.thesis.value or ctx.professor_id:
        return

    active_apps = list(
        (
            await session.scalars(
                select(ThesisApplication).where(
                    ThesisApplication.student_id == user.id,
                    ThesisApplication.status == ThesisApplicationStatus.active,
                )
            )
        ).all()
    )
    if not active_apps:
        return

    chosen_id: Optional[int] = None
    if user.thesis_professor_id and any(
        a.professor_id == user.thesis_professor_id for a in active_apps
    ):
        chosen_id = user.thesis_professor_id
    elif len(active_apps) == 1:
        chosen_id = active_apps[0].professor_id

    if chosen_id is None:
        return

    prof = await session.get(User, chosen_id)
    if prof and prof.role == UserRole.professor:
        ctx.professor_id = prof.id
        ctx.professor = f"{prof.first_name} {prof.last_name}"


async def _handle_thesis_flow(
    session: AsyncSession, ctx: ParsedContext, user: User
) -> Optional[dict[str, Any]]:
    """
    Handle thesis-specific business rules. Mutates ctx.phase when needed.
    Returns a response dict to send immediately, or None to proceed to slot display.
    """
    await _apply_topic_professor_cleanup(session, ctx)
    if not user.is_final_year:
        return {
            "message": (
                "Thesis consultations are only for final-year students. "
                "You are not in your final year, so you cannot schedule thesis consultations here."
            ),
            "slots": [],
            "chips": [],
            "phase": "done",
            "manual_form": False,
            "context": ctx.to_state(),
        }

    await _autofill_thesis_mentor_if_approved(session, ctx, user)
    await _apply_topic_professor_cleanup(session, ctx)
    if not ctx.professor_id:
        return None  # determine_next_question handles professor prompt

    apps = list(
        (
            await session.scalars(
                select(ThesisApplication).where(
                    ThesisApplication.student_id == user.id,
                    ThesisApplication.professor_id == ctx.professor_id,
                )
            )
        ).all()
    )

    active = next((a for a in apps if a.status == ThesisApplicationStatus.active), None)
    if active:
        return None

    pending = next((a for a in apps if a.status == ThesisApplicationStatus.pending), None)
    if pending:
        return {
            "message": (
                "Your thesis supervision request is still waiting for the professor's decision. "
                "Open the Thesis page to see the status. Once your mentor approves, you can book "
                "thesis consultation slots from this chat."
            ),
            "slots": [],
            "chips": [],
            "phase": "done",
            "manual_form": False,
            "context": ctx.to_state(),
        }

    rejected = next((a for a in apps if a.status == ThesisApplicationStatus.rejected), None)
    if rejected:
        prof = await session.get(User, ctx.professor_id)
        prof_name = f"{prof.first_name} {prof.last_name}" if prof else "the professor"
        ctx.professor_id = None
        ctx.professor = None
        return {
            "message": (
                f"Prof. {prof_name} has declined thesis supervision. "
                "Choose a different professor, or submit a new request from the Thesis page."
            ),
            "slots": [],
            "chips": [],
            "phase": "collect",
            "manual_form": False,
            "context": ctx.to_state(),
        }

    return {
        "message": (
            "You do not have an approved thesis mentor yet. Open the Thesis page and submit "
            "a supervision request to a mentor. After approval, you can schedule thesis consultations here."
        ),
        "slots": [],
        "chips": [],
        "phase": "done",
        "manual_form": False,
        "context": ctx.to_state(),
    }


async def _slots_for_booking_ctx(
    session: AsyncSession, student_id: int, ctx: ParsedContext
) -> tuple[list[ConsultationSession], Optional[str]]:
    try:
        ctype = ConsultationType(ctx.consultation_type)  # type: ignore[arg-type]
        kwargs: dict[str, Any] = dict(
            session=session,
            professor_id=ctx.professor_id,  # type: ignore[arg-type]
            course_id=ctx.course_id,
            ctype=ctype,
            group_size=1,
            student_id=student_id,
            next_weeks=3,
        )
        if ctype == ConsultationType.preparation and ctx.academic_event_id is not None:
            kwargs["academic_event_id"] = ctx.academic_event_id
        slots = await slot_service.get_free_slots(**kwargs)
        return slots, None
    except ValueError as e:
        return [], str(e)


def _preparation_slots_by_event_id(slots: list[ConsultationSession]) -> dict[int, list[ConsultationSession]]:
    out: dict[int, list[ConsultationSession]] = {}
    for s in slots:
        k = int(s.event_id) if s.event_id is not None else 0
        out.setdefault(k, []).append(s)
    return out


async def _prep_exam_group_label(session: AsyncSession, event_key: int, course: Optional[Course]) -> str:
    if event_key == 0:
        cname = course.name if course else "your course"
        return f"Prep session · {cname} (not linked to a specific exam in the calendar)"
    ev = await session.get(AcademicEvent, event_key)
    if not ev:
        return f"Preparation · exam event #{event_key}"
    type_l = "Midterm" if ev.event_type == AcademicEventType.midterm else "Final"
    exam_day = ev.event_date.strftime("%d %b %Y")
    return f"{type_l}: {ev.name} — exam on {exam_day}"


async def _slots_to_date_chips_row(
    session: AsyncSession, slots: list[ConsultationSession], consultation_type_val: Optional[str]
) -> list[dict[str, Any]]:
    if consultation_type_val == ConsultationType.preparation.value:
        return await _date_choice_chips_preparation(session, slots)
    return _date_choice_chips(_distinct_slot_dates(slots))


async def _date_choice_chips_preparation(
    session: AsyncSession, slots: list[ConsultationSession]
) -> list[dict[str, Any]]:
    chips: list[dict[str, Any]] = []
    for d in _distinct_slot_dates(slots):
        sample = next(s for s in slots if s.session_date == d)
        if sample.event_id:
            ev = await session.get(AcademicEvent, sample.event_id)
            if ev:
                type_l = "Midterm" if ev.event_type == AcademicEventType.midterm else "Final"
                exam_day = ev.event_date.strftime("%d %b")
                label = f"{d.strftime('%a %d %b')} — {type_l}: {ev.name} (exam {exam_day})"
            else:
                label = d.strftime("%a %d %b")
        else:
            label = f"{d.strftime('%a %d %b')} — Prep session"
        chips.append(
            {
                "id": int(d.strftime("%Y%m%d")),
                "label": label,
                "action": f"pick_date:{d.isoformat()}",
            }
        )
    return chips


async def _maybe_preparation_exam_disambiguation(
    session: AsyncSession,
    conv: Conversation,
    ctx: ParsedContext,
    user_id: int,
) -> Optional[dict[str, Any]]:
    if ctx.consultation_type != ConsultationType.preparation.value:
        return None
    state = conv.state or {}
    if "academic_event_id" in state:
        return None
    if not (ctx.professor_id and ctx.course_id):
        return None
    slots_all, err = await _slots_for_booking_ctx(session, user_id, ctx)
    if err or not slots_all:
        return None
    groups = _preparation_slots_by_event_id(slots_all)
    if len(groups) <= 1:
        return None
    course = await session.get(Course, ctx.course_id) if ctx.course_id else None
    chips: list[dict[str, Any]] = []
    for eid in sorted(groups.keys()):
        label = await _prep_exam_group_label(session, eid, course)
        chips.append({"id": eid, "label": label, "action": f"pick_prep_exam:{eid}"})
    ctx.phase = "pick_prep_exam"
    conv.state = await _sanitize_state_dict(session, {**ctx.to_state(), "phase": "pick_prep_exam"})
    await session.flush()
    return {
        "message": (
            "There is more than one announced preparation session for this course with this professor. "
            "Which exam is this booking for?"
        ),
        "slots": [],
        "chips": chips,
        "phase": "pick_prep_exam",
        "manual_form": False,
        "context": conv.state,
    }


def _distinct_slot_dates(slots: list[ConsultationSession]) -> list[date]:
    seen: set[date] = set()
    ordered: list[date] = []
    for s in sorted(slots, key=lambda x: (x.session_date, x.time_from, x.time_to)):
        if s.session_date not in seen:
            seen.add(s.session_date)
            ordered.append(s.session_date)
    return ordered


def _day_waitlist_chips(dates: list[date]) -> list[dict[str, Any]]:
    """Chips for day-level waitlist (no concrete session yet)."""
    chips: list[dict[str, Any]] = []
    for d in dates[:14]:
        chips.append(
            {
                "id": int(d.strftime("%Y%m%d")),
                "label": f"Waitlist · any slot {d.strftime('%a %d %b')}",
                "action": f"join_day_waitlist:{d.isoformat()}",
            }
        )
    return chips


def _date_choice_chips(dates: list[date]) -> list[dict[str, Any]]:
    chips: list[dict[str, Any]] = []
    for d in dates[:14]:
        iso = d.isoformat()
        chips.append(
            {
                "id": int(d.strftime("%Y%m%d")),
                "label": d.strftime("%a %d %b"),
                "action": f"pick_date:{iso}",
            }
        )
    return chips


def _time_choice_chips(day_slots: list[ConsultationSession], limit: int = 24) -> list[dict[str, Any]]:
    ordered = sorted(day_slots, key=lambda x: (x.time_from, x.time_to, x.id))
    return [
        {
            "id": s.id,
            "label": f"{s.time_from.strftime('%H:%M')}–{s.time_to.strftime('%H:%M')}",
            "action": f"select_slot:{s.id}",
        }
        for s in ordered[:limit]
    ]


async def _time_choice_chips_with_prep_context(
    session: AsyncSession, ctx: ParsedContext, day_slots: list[ConsultationSession], limit: int = 24
) -> list[dict[str, Any]]:
    if ctx.consultation_type != ConsultationType.preparation.value or not day_slots:
        return _time_choice_chips(day_slots, limit=limit)
    first = day_slots[0]
    if not first.event_id:
        return _time_choice_chips(day_slots, limit=limit)
    ev = await session.get(AcademicEvent, first.event_id)
    if not ev:
        return _time_choice_chips(day_slots, limit=limit)
    type_l = "Midterm" if ev.event_type == AcademicEventType.midterm else "Final"
    suffix = f" · {type_l}, exam {ev.event_date.strftime('%d %b')}"
    ordered = sorted(day_slots, key=lambda x: (x.time_from, x.time_to, x.id))
    return [
        {
            "id": s.id,
            "label": f"{s.time_from.strftime('%H:%M')}–{s.time_to.strftime('%H:%M')}{suffix}",
            "action": f"select_slot:{s.id}",
        }
        for s in ordered[:limit]
    ]


def _confirm_booking_chips() -> list[dict[str, Any]]:
    return [
        {"id": 1, "label": "Yes, book it", "action": "confirm_booking:yes"},
        {"id": 0, "label": "No, pick another time", "action": "confirm_booking:no"},
    ]


async def _booking_confirm_summary(
    session: AsyncSession, ctx: ParsedContext, cs: ConsultationSession
) -> str:
    prof = await session.get(User, cs.professor_id)
    prof_name = f"{prof.first_name} {prof.last_name}" if prof else (ctx.professor or "the professor")
    ctype = ConsultationType(ctx.consultation_type).value if ctx.consultation_type else "?"
    date_str = cs.session_date.strftime("%A %d %B %Y")
    time_str = f"{cs.time_from.strftime('%H:%M')}–{cs.time_to.strftime('%H:%M')}"
    course_line = ""
    if ctx.course_id:
        c = await session.get(Course, ctx.course_id)
        if c:
            course_line = f"\n- Course: {c.name}"
    topic = (ctx.task or ctx.anonymous_question or "").strip()
    topic_line = f"\n- Topic: {topic}" if topic else ""
    return (
        f"Please confirm your booking:\n"
        f"- Type: {ctype}\n"
        f"- Professor: {prof_name}{course_line}{topic_line}\n"
        f"- When: {date_str}, {time_str}\n\n"
        f"Should I confirm this booking?"
    )


async def _handle_scheduling_commands(
    session: AsyncSession,
    user: User,
    conv: Conversation,
    text: str,
) -> Optional[dict[str, Any]]:
    """Handle pick_date / select_slot / confirm_booking / legacy confirm_slot. Returns None if not a command."""
    tl = text.strip().lower()
    state = dict(conv.state or {})

    async def persist(payload: dict[str, Any], ctx: ParsedContext) -> dict[str, Any]:
        raw_ctx = dict(payload.get("context", ctx.to_state()))
        cleaned = await _sanitize_state_dict(session, raw_ctx)
        payload = {**payload, "context": cleaned}
        conv.state = cleaned
        await session.flush()
        return payload

    if tl.startswith("pick_prep_exam:"):
        tail = text.split(":", 1)[1].strip()
        try:
            event_key = int(tail)
        except ValueError:
            return {
                "message": "Invalid preparation choice.",
                "slots": [],
                "chips": [],
                "phase": state.get("phase", "collect"),
                "manual_form": False,
                "context": state,
            }
        ctx = ParsedContext.from_state(state)
        if ctx.phase != "pick_prep_exam" or ctx.consultation_type != ConsultationType.preparation.value:
            return {
                "message": "Use the exam buttons above to continue your preparation booking.",
                "slots": [],
                "chips": [],
                "phase": ctx.phase,
                "manual_form": False,
                "context": state,
            }
        ctx.academic_event_id = event_key
        ctx.phase = "pick_date"
        ctx.picked_date = None
        ctx.pending_session_id = None
        slots, err = await _slots_for_booking_ctx(session, user.id, ctx)
        if err:
            return await persist(
                {
                    "message": err,
                    "slots": [],
                    "chips": [],
                    "phase": "collect",
                    "manual_form": False,
                    "context": ctx.to_state(),
                },
                ctx,
            )
        if not slots:
            return await persist(
                {
                    "message": "No preparation slots are available for that choice right now.",
                    "slots": [],
                    "chips": [],
                    "phase": "collect",
                    "manual_form": False,
                    "context": ctx.to_state(),
                },
                ctx,
            )
        date_chips = await _date_choice_chips_preparation(session, slots)
        return await persist(
            {
                "message": (
                    "Choose a day for this preparation session. "
                    "Each date shows which exam it supports when that applies."
                ),
                "slots": date_chips,
                "chips": [],
                "phase": "pick_date",
                "manual_form": False,
                "context": ctx.to_state(),
            },
            ctx,
        )

    # Legacy: one-click confirm from older clients (maps to select → confirm or final yes)
    if tl.startswith("confirm_slot:"):
        try:
            legacy_sid = int(text.split(":", 1)[1].strip())
        except (ValueError, IndexError):
            return {
                "message": "Invalid slot selection.",
                "slots": [],
                "chips": [],
                "phase": state.get("phase", "collect"),
                "manual_form": False,
                "context": state,
            }
        phase = str(state.get("phase") or "")
        if phase == "confirm_booking" and int(state.get("pending_session_id") or 0) == legacy_sid:
            text = "confirm_booking:yes"
            tl = text.lower()
        elif phase == "pick_time":
            text = f"select_slot:{legacy_sid}"
            tl = text.lower()
        else:
            return {
                "message": "Pick a date, then a time slot, and confirm — use the buttons in order.",
                "slots": [],
                "chips": [],
                "phase": phase or "collect",
                "manual_form": False,
                "context": state,
            }

    if tl.startswith("join_group_session:"):
        tail = text.split(":", 1)[1].strip()
        ctx = ParsedContext.from_state(state)
        if ctx.phase != "group_join_offer" or not ctx.group_join_session_id:
            return {
                "message": "There is no group join offer active. Continue your booking from the start.",
                "slots": [],
                "chips": [],
                "phase": ctx.phase,
                "manual_form": False,
                "context": state,
            }
        if tail.lower() == "skip":
            ctx.group_join_session_id = None
            ctx.phase = "pick_date"
            ctx.pending_session_id = None
            ctx.picked_date = None
            slots, err = await _slots_for_booking_ctx(session, user.id, ctx)
            if err:
                return await persist(
                    {
                        "message": err,
                        "slots": [],
                        "chips": [],
                        "phase": "collect",
                        "manual_form": False,
                        "context": ctx.to_state(),
                    },
                    ctx,
                )
            if not slots:
                return await persist(
                    {
                        "message": "No free slots right now.",
                        "slots": [],
                        "chips": [],
                        "phase": "collect",
                        "manual_form": False,
                        "context": ctx.to_state(),
                    },
                    ctx,
                )
            date_chips = await _slots_to_date_chips_row(session, slots, ctx.consultation_type)
            return await persist(
                {
                    "message": "Here are days with free slots in the next few weeks. Pick a date first:",
                    "slots": date_chips,
                    "chips": [],
                    "phase": "pick_date",
                    "manual_form": False,
                    "context": ctx.to_state(),
                },
                ctx,
            )
        try:
            sid = int(tail)
        except ValueError:
            return {
                "message": "Invalid choice. Use the Yes / No buttons.",
                "slots": [],
                "chips": [],
                "phase": "group_join_offer",
                "manual_form": False,
                "context": state,
            }
        if sid != ctx.group_join_session_id:
            return {
                "message": "That session does not match the offer. Use the buttons provided.",
                "slots": [],
                "chips": [],
                "phase": "group_join_offer",
                "manual_form": False,
                "context": state,
            }
        cs = await session.get(ConsultationSession, sid)
        if not cs:
            return {
                "message": "That session is no longer available.",
                "slots": [],
                "chips": [],
                "phase": "collect",
                "manual_form": False,
                "context": ctx.to_state(),
            }
        await _apply_topic_professor_cleanup(session, ctx)
        ctx.pending_session_id = sid
        ctx.picked_date = cs.session_date.isoformat()
        ctx.group_join_session_id = None
        ctx.phase = "confirm_booking"
        summary = await _booking_confirm_summary(session, ctx, cs)
        return await persist(
            {
                "message": summary,
                "slots": [],
                "chips": _confirm_booking_chips(),
                "phase": "confirm_booking",
                "manual_form": False,
                "context": ctx.to_state(),
            },
            ctx,
        )

    if tl.startswith("pick_date:"):
        iso = text.split(":", 1)[1].strip()
        try:
            picked = date.fromisoformat(iso)
        except ValueError:
            return {
                "message": "That date is not valid. Pick one of the suggested dates.",
                "slots": [],
                "chips": [],
                "phase": state.get("phase", "collect"),
                "manual_form": False,
                "context": state,
            }
        ctx = ParsedContext.from_state(state)
        if ctx.phase != "pick_date":
            return {
                "message": "First complete the questions above, then pick a date from the list when it appears.",
                "slots": [],
                "chips": [],
                "phase": ctx.phase,
                "manual_form": False,
                "context": state,
            }
        slots, err = await _slots_for_booking_ctx(session, user.id, ctx)
        if err:
            return {
                "message": err,
                "slots": [],
                "chips": [],
                "phase": "collect",
                "manual_form": False,
                "context": ctx.to_state(),
            }
        day_slots = [s for s in slots if s.session_date == picked]
        if not day_slots:
            try:
                ctype_pd = ConsultationType(ctx.consultation_type)  # type: ignore[arg-type]
            except ValueError:
                return await persist(
                    {
                        "message": "No free slots on that day. Pick another date.",
                        "slots": await _slots_to_date_chips_row(session, slots, ctx.consultation_type),
                        "chips": [],
                        "phase": "pick_date",
                        "manual_form": False,
                        "context": {**ctx.to_state(), "phase": "pick_date", "picked_date": None, "pending_session_id": None},
                    },
                    ctx,
                )
            full_day: list[ConsultationSession] = []
            if ctx.professor_id:
                full_day = await slot_service.get_full_sessions(
                    session,
                    professor_id=int(ctx.professor_id),
                    course_id=ctx.course_id,
                    ctype=ctype_pd,
                    next_weeks=3,
                    on_date=picked,
                    student_id=user.id,
                )
            chips: list[dict[str, Any]] = []
            for s in full_day[:16]:
                chips.append(
                    {
                        "id": s.id,
                        "label": f"Waitlist {s.time_from.strftime('%H:%M')}–{s.time_to.strftime('%H:%M')}",
                        "action": f"join_waitlist:{s.id}",
                    }
                )
            if ctype_pd in (ConsultationType.general, ConsultationType.thesis):
                chips.append(
                    {
                        "id": int(picked.strftime("%Y%m%d")),
                        "label": f"Waitlist · any slot {picked.strftime('%a %d %b')}",
                        "action": f"join_day_waitlist:{picked.isoformat()}",
                    }
                )
            if chips:
                ctx.phase = "waitlist_offer"
                return await persist(
                    {
                        "message": (
                            "That day has no free times left. Join the waitlist for a full slot, "
                            "or pick “any slot” to be notified if something opens that day."
                        ),
                        "slots": [],
                        "chips": chips,
                        "phase": "waitlist_offer",
                        "manual_form": False,
                        "context": ctx.to_state(),
                    },
                    ctx,
                )
            return await persist(
                {
                    "message": "No free slots on that day. Pick another date.",
                    "slots": await _slots_to_date_chips_row(session, slots, ctx.consultation_type),
                    "chips": [],
                    "phase": "pick_date",
                    "manual_form": False,
                    "context": {**ctx.to_state(), "phase": "pick_date", "picked_date": None, "pending_session_id": None},
                },
                ctx,
            )
        ctx.picked_date = picked.isoformat()
        ctx.phase = "pick_time"
        ctx.pending_session_id = None
        chips = await _time_choice_chips_with_prep_context(session, ctx, day_slots)
        return await persist(
            {
                "message": f"Here are the times on {picked.strftime('%A %d %B')}. Pick one:",
                "slots": chips,
                "chips": [],
                "phase": "pick_time",
                "manual_form": False,
                "context": ctx.to_state(),
            },
            ctx,
        )

    if tl.startswith("select_slot:"):
        try:
            sid = int(text.split(":", 1)[1].strip())
        except (ValueError, IndexError):
            return {
                "message": "Invalid time slot.",
                "slots": [],
                "chips": [],
                "phase": state.get("phase", "collect"),
                "manual_form": False,
                "context": state,
            }
        ctx = ParsedContext.from_state(state)
        if ctx.phase != "pick_time" or not ctx.picked_date:
            return {
                "message": "Pick a date first, then a time slot.",
                "slots": [],
                "chips": [],
                "phase": ctx.phase,
                "manual_form": False,
                "context": state,
            }
        slots, err = await _slots_for_booking_ctx(session, user.id, ctx)
        if err:
            return {
                "message": err,
                "slots": [],
                "chips": [],
                "phase": "collect",
                "manual_form": False,
                "context": ctx.to_state(),
            }
        picked = date.fromisoformat(ctx.picked_date)
        day_slots = [s for s in slots if s.session_date == picked]
        match = next((s for s in day_slots if s.id == sid), None)
        if not match:
            ctx.pending_session_id = None
            return await persist(
                {
                    "message": "That slot is no longer available. Pick another time.",
                    "slots": await _time_choice_chips_with_prep_context(session, ctx, day_slots),
                    "chips": [],
                    "phase": "pick_time",
                    "manual_form": False,
                    "context": ctx.to_state(),
                },
                ctx,
            )
        ctx.pending_session_id = sid
        ctx.phase = "confirm_booking"
        await _apply_topic_professor_cleanup(session, ctx)
        summary = await _booking_confirm_summary(session, ctx, match)
        return await persist(
            {
                "message": summary,
                "slots": [],
                "chips": _confirm_booking_chips(),
                "phase": "confirm_booking",
                "manual_form": False,
                "context": ctx.to_state(),
            },
            ctx,
        )

    if tl.startswith("confirm_booking:"):
        tail = text.split(":", 1)[1].strip().lower()
        ctx = ParsedContext.from_state(state)
        if ctx.phase != "confirm_booking":
            return {
                "message": "There is nothing to confirm right now.",
                "slots": [],
                "chips": [],
                "phase": ctx.phase,
                "manual_form": False,
                "context": state,
            }
        if tail in ("no", "n", "false", "0"):
            ctx.pending_session_id = None
            ctx.phase = "pick_time"
            slots, err = await _slots_for_booking_ctx(session, user.id, ctx)
            if err or not ctx.picked_date:
                return await persist(
                    {
                        "message": err or "Could not reload slots.",
                        "slots": [],
                        "chips": [],
                        "phase": "collect",
                        "manual_form": False,
                        "context": ctx.to_state(),
                    },
                    ctx,
                )
            picked = date.fromisoformat(ctx.picked_date)
            day_slots = [s for s in slots if s.session_date == picked]
            return await persist(
                {
                    "message": "No problem — pick a different time:",
                    "slots": await _time_choice_chips_with_prep_context(session, ctx, day_slots),
                    "chips": [],
                    "phase": "pick_time",
                    "manual_form": False,
                    "context": ctx.to_state(),
                },
                ctx,
            )
        if tail not in ("yes", "y", "true", "1"):
            return await persist(
                {
                    "message": "Reply with Yes to confirm or No to pick another time.",
                    "slots": [],
                    "chips": _confirm_booking_chips(),
                    "phase": "confirm_booking",
                    "manual_form": False,
                    "context": ctx.to_state(),
                },
                ctx,
            )
        if not ctx.pending_session_id:
            return {
                "message": "No slot selected. Pick a time first.",
                "slots": [],
                "chips": [],
                "phase": "collect",
                "manual_form": False,
                "context": ctx.to_state(),
            }
        await _apply_topic_professor_cleanup(session, ctx)
        try:
            b = await booking_service.create_booking(
                session,
                student=user,
                session_id=ctx.pending_session_id,
                task=ctx.task,
                anonymous_question=ctx.anonymous_question,
                group_size=1,
            )
        except ValueError as e:
            return await persist(
                {
                    "message": str(e),
                    "slots": [],
                    "chips": [],
                    "phase": "confirm_booking",
                    "manual_form": False,
                    "context": ctx.to_state(),
                },
                ctx,
            )
        cs = await session.get(ConsultationSession, ctx.pending_session_id)
        prof = await session.get(User, cs.professor_id) if cs else None
        prof_name = f"{prof.first_name} {prof.last_name}" if prof else ctx.professor or "the professor"
        date_str = cs.session_date.isoformat() if cs else "?"
        time_str = (
            f"{cs.time_from.strftime('%H:%M')}–{cs.time_to.strftime('%H:%M')}" if cs else ""
        )
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

    return None


async def _register_preparation_vote(
    session: AsyncSession,
    student_id: int,
    course_id: int,
    professor_id: int,
    ctx: ParsedContext,
) -> dict[str, Any]:
    today = utc_today()
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

    # Day-level waitlist (must run before join_waitlist:… so ISO dates are not parsed as session ids)
    if not structured and t_lower.startswith("join_day_waitlist:"):
        iso = text.split(":", 1)[1].strip()
        try:
            pref = date.fromisoformat(iso)
        except ValueError:
            return {
                "message": "Invalid date for waitlist.",
                "slots": [],
                "chips": [],
                "phase": "collect",
                "manual_form": False,
                "context": {},
            }
        conv = await get_or_create_conversation(session, user_id)
        ctx = ParsedContext.from_state(conv.state or {})
        if not ctx.professor_id or not ctx.consultation_type:
            return {
                "message": "Continue your booking first (professor and consultation type), then pick a waitlist option.",
                "slots": [],
                "chips": [],
                "phase": "collect",
                "manual_form": False,
                "context": ctx.to_state(),
            }
        try:
            ctype = ConsultationType(ctx.consultation_type)
        except ValueError:
            return {
                "message": "Invalid consultation type in context.",
                "slots": [],
                "chips": [],
                "phase": "collect",
                "manual_form": False,
                "context": ctx.to_state(),
            }
        if ctype == ConsultationType.graded_work_review:
            return {
                "message": "Day waitlist is not available for graded work review — wait for your professor to announce a session.",
                "slots": [],
                "chips": [],
                "phase": "done",
                "manual_form": False,
                "context": {},
            }
        try:
            msg, _pos = await waitlist_service.add_day_waitlist(
                session,
                student_id=user_id,
                professor_id=int(ctx.professor_id),
                course_id=ctx.course_id,
                consultation_type=ctype,
                preferred_date=pref,
                any_slot_on_day=True,
            )
        except ValueError as ve:
            await session.flush()
            return {
                "message": str(ve),
                "slots": [],
                "chips": [],
                "phase": "waitlist_offer",
                "manual_form": False,
                "context": ctx.to_state(),
            }
        await session.flush()
        return {
            "message": msg,
            "slots": [],
            "chips": [],
            "phase": "done",
            "manual_form": False,
            "context": {},
        }

    # Join waitlist for a specific session
    if not structured and t_lower.startswith("join_waitlist:"):
        try:
            session_id = int(text.split(":", 1)[1].strip())
        except (ValueError, IndexError):
            return {"message": "Invalid waitlist request.", "slots": [], "chips": [], "phase": "collect", "manual_form": False, "context": {}}

        try:
            msg, _pos = await waitlist_service.add_session_waitlist(session, student_id=user_id, session_id=session_id)
        except ValueError as e:
            detail = str(e)
            if "not found" in detail.lower():
                return {"message": "Session not found.", "slots": [], "chips": [], "phase": "collect", "manual_form": False, "context": {}}
            return {"message": detail, "slots": [], "chips": [], "phase": "collect", "manual_form": False, "context": {}}
        await session.flush()
        return {
            "message": msg,
            "slots": [],
            "chips": [],
            "phase": "done",
            "manual_form": False,
            "context": {},
        }

    conv = await get_or_create_conversation(session, user_id)
    state = dict(conv.state or {})

    if not structured:
        sched_resp = await _handle_scheduling_commands(session, user, conv, text)
        if sched_resp is not None:
            return sched_resp

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
            "manual_form": False,
            "context": snap.to_state(),
        }

    if structured:
        # One-shot fields from the client: do not persist; exam-notice flow has no free-text topic.
        _skip = {"exam_session_booking", "target_session_id"}
        merged = {
            **state,
            **{k: v for k, v in structured.items() if v is not None and k not in _skip},
        }
        if structured.get("exam_session_booking"):
            merged.pop("task", None)
            merged.pop("anonymous_question", None)
        state = await _sanitize_state_dict(session, merged)
        conv.state = state
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

        # Task/topic collection phase — the user's message IS the task description
        if prev_phase == "task_collect" and prev_snap.consultation_type == ConsultationType.general.value:
            if _is_boilerplate_booking_message(text):
                ctx = prev_snap
                ctx.failed_parse_count = int(state.get("failed_parse_count") or 0) + 1
            else:
                prev_snap.task = text.strip()[:500] or prev_snap.task
                ctx = prev_snap
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
        elif not structured and prev_phase == "group_join_offer":
            ctx = prev_snap
            if _message_is_scheduling_transport(text):
                ctx.failed_parse_count = int(state.get("failed_parse_count") or 0)
            else:
                ctx.failed_parse_count = int(state.get("failed_parse_count") or 0) + 1

        elif (
            not structured
            and prev_phase
            in ("pick_date", "pick_time", "confirm_booking", "waitlist_offer", "pick_prep_exam")
            and not _message_is_scheduling_transport(text)
        ):
            # Free text during slot picking: do not keep stale professor/course from JSON state.
            ctx = await parse_first_message(session, text, user_id)
            extracted = bool(
                ctx.professor_id
                or ctx.consultation_type
                or ctx.course_id
                or ctx.task
                or (ctx.anonymous_question and len(ctx.anonymous_question) > 10)
            )
            ctx.failed_parse_count = 0 if extracted else (int(state.get("failed_parse_count") or 0) + 1)
        elif not structured and prev_phase == "collect" and _is_boilerplate_booking_message(text):
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
            ctx = await process_reply(session, prev_snap, text, user_id)
            delta = await parse_first_message(session, text, user_id)
            extracted = _extracted_any(prev_snap, delta)
            ctx.failed_parse_count = 0 if extracted else (int(state.get("failed_parse_count") or 0) + 1)

    # Stray free text while a group-join offer is showing — do not merge into topic or re-run slot logic.
    if (
        not structured
        and ctx.phase == "group_join_offer"
        and ctx.group_join_session_id
        and not _message_is_scheduling_transport(text)
        and text.strip()
    ):
        conv.state = await _sanitize_state_dict(session, {**ctx.to_state()})
        await session.flush()
        cs_gr = await session.get(ConsultationSession, ctx.group_join_session_id)
        msg_gr = (
            await _group_join_offer_message(session, cs_gr, ctx) if cs_gr else "Choose an option below."
        )
        if ctx.failed_parse_count >= 2:
            msg_gr = 'Please use the buttons: "Yes, join that session" or "No, pick a different time."'
        chips_gr = [
            {
                "id": ctx.group_join_session_id,
                "label": "Yes, join that session",
                "action": f"join_group_session:{ctx.group_join_session_id}",
            },
            {"id": 0, "label": "No, pick a different time", "action": "join_group_session:skip"},
        ]
        return {
            "message": msg_gr,
            "slots": [],
            "chips": chips_gr,
            "phase": "group_join_offer",
            "manual_form": False,
            "context": conv.state,
        }

    # Thesis-specific business rules
    if ctx.consultation_type == ConsultationType.thesis.value:
        thesis_resp = await _handle_thesis_flow(session, ctx, user)
        if thesis_resp is not None:
            return await _persist_response_state(session, conv, thesis_resp, ctx.to_state())

    # Determine next question (may auto-fill professor/course on ctx)
    nq = await determine_next_question(session, ctx, user_id)
    await _apply_topic_professor_cleanup(session, ctx)
    if nq:
        conv_state = await _sanitize_state_dict(
            session, {**ctx.to_state(), "failed_parse_count": ctx.failed_parse_count}
        )
        conv.state = conv_state
        await session.flush()
        hint = (
            "I wasn't able to understand your request. Try writing something like: "
            "'I want a consultation with prof. Marković about databases, I have a question about SQL joins.'"
        )
        msg = hint if ctx.failed_parse_count >= 2 and len(text.strip()) < 5 else nq
        return {
            "message": msg,
            "manual_form": False,
            "phase": "collect",
            "context": conv.state,
        }

    ctype = ConsultationType(ctx.consultation_type)  # type: ignore[arg-type]

    prep_pick = await _maybe_preparation_exam_disambiguation(session, conv, ctx, user_id)
    if prep_pick is not None:
        return prep_pick

    # Preparation vote registration: kept for Phase 2, not called in Phase 1
    # if ctype == ConsultationType.preparation and ctx.professor_id and ctx.course_id:
    #     vote_resp = await _register_preparation_vote(
    #         session, user_id, ctx.course_id, ctx.professor_id, ctx
    #     )
    #     return await _persist_response_state(session, conv, vote_resp, ctx.to_state())

    slots, slot_err = await _slots_for_booking_ctx(session, user_id, ctx)
    if slot_err:
        conv.state = await _sanitize_state_dict(
            session, {**ctx.to_state(), "failed_parse_count": ctx.failed_parse_count}
        )
        await session.flush()
        return {"message": slot_err, "manual_form": False, "phase": "collect", "context": conv.state}

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

        if ctype == ConsultationType.preparation:
            return await _persist_response_state(session, conv, {
                "message": "No preparation session has been announced for this course yet. "
                           "When your professor sends a prep notice, use the button on your home page to book.",
                "slots": [],
                "chips": [],
                "phase": "done",
                "manual_form": False,
                "context": ctx.to_state(),
            }, ctx.to_state())

        # Full session waitlist + day-level waitlist (general / thesis)
        if ctx.professor_id:
            full_sessions = await slot_service.get_full_sessions(
                session,
                professor_id=ctx.professor_id,
                course_id=ctx.course_id,
                ctype=ctype,
                next_weeks=3,
                student_id=user_id,
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
                return await _persist_response_state(
                    session,
                    conv,
                    {
                        "message": "All listed times are full. Join the waitlist for a specific slot below.",
                        "slots": [],
                        "chips": chips,
                        "phase": "waitlist_offer",
                        "manual_form": False,
                        "context": {**ctx.to_state(), "phase": "waitlist_offer"},
                    },
                    ctx.to_state(),
                )

        if (
            ctx.professor_id
            and ctype in (ConsultationType.general, ConsultationType.thesis)
        ):
            day_dates = await slot_service.iter_dates_for_professor_availability(
                session,
                professor_id=int(ctx.professor_id),
                course_id=ctx.course_id,
                ctype=ctype,
                student_id=user_id,
                next_weeks=3,
                max_dates=3,
            )
            if day_dates:
                return await _persist_response_state(
                    session,
                    conv,
                    {
                        "message": (
                            "No bookable times in the next 3 weeks. "
                            "These are the next days when this professor holds consultations — "
                            "pick one to join the waitlist; we will notify you if a slot opens."
                        ),
                        "slots": [],
                        "chips": _day_waitlist_chips(day_dates[:3]),
                        "phase": "waitlist_offer",
                        "manual_form": False,
                        "context": {**ctx.to_state(), "phase": "waitlist_offer"},
                    },
                    ctx.to_state(),
                )

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

        return await _persist_response_state(session, conv, {
            "message": "No free slots in the next 3 weeks.",
            "slots": [],
            "chips": [],
            "phase": "done",
            "manual_form": False,
            "context": ctx.to_state(),
        }, ctx.to_state())

    if ctype == ConsultationType.general:
        peer = await _find_peer_general_group_booking(session, student_id=user_id, ctx=ctx)
        if peer is not None:
            cs_peer, _bk = peer
            ctx.phase = "group_join_offer"
            ctx.group_join_session_id = cs_peer.id
            ctx.pending_session_id = None
            ctx.picked_date = None
            msg = await _group_join_offer_message(session, cs_peer, ctx)
            conv.state = await _sanitize_state_dict(
                session, {**ctx.to_state(), "failed_parse_count": 0}
            )
            await session.flush()
            return {
                "message": msg,
                "slots": [],
                "chips": [
                    {
                        "id": cs_peer.id,
                        "label": "Yes, join that session",
                        "action": f"join_group_session:{cs_peer.id}",
                    },
                    {
                        "id": 0,
                        "label": "No, pick a different time",
                        "action": "join_group_session:skip",
                    },
                ],
                "phase": "group_join_offer",
                "manual_form": False,
                "context": conv.state,
            }

    date_chips = await _slots_to_date_chips_row(session, slots, ctx.consultation_type)
    ctx.picked_date = None
    ctx.pending_session_id = None
    ctx.group_join_session_id = None
    ctx.phase = "pick_date"
    conv.state = await _sanitize_state_dict(
        session, {**ctx.to_state(), "phase": "pick_date", "failed_parse_count": 0}
    )
    await session.flush()
    date_msg = (
        "Here are preparation session dates (each label shows the related exam when applicable). Pick a day:"
        if ctx.consultation_type == ConsultationType.preparation.value
        else "Here are days with free slots in the next few weeks. Pick a date first:"
    )
    return {
        "message": date_msg,
        "slots": date_chips,
        "chips": [],
        "phase": "pick_date",
        "manual_form": False,
        "context": conv.state,
    }
