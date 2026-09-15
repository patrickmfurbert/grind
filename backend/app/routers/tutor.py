import json
import logging
import re
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..database import connection
from ..services.openrouter import complete_json, stream_chat
from ..services.rag import retrieve_passages
from .progress import apply_mastery_delta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tutor", tags=["tutor"])

# Minimum length (in words) for a user message to count as a real attempt at
# demonstrating understanding, rather than a quick question or acknowledgement.
MIN_SUBSTANTIVE_WORDS = 50

PROMPT = """You are a Socratic tutor for Pat, a Software Engineer II who builds Java/Spring Boot microservices at Paychex using MongoDB, Kafka, Dapr, OpenShift, Kong, Jenkins, Gradle, Splunk, and OpenTelemetry. Pat transitioned from clinical nursing. Start from why, use useful visual or real-world analogies, make Pat defend answers, ask follow-up questions about failures and trade-offs, and get harder with demonstrated mastery. Current concept: {concept}. Mastery: {mastery}/5.{book_context}"""

# Phase 6 ("Algorithm Patterns") uses a distinct tutoring flow from the rest of the
# curriculum: instead of open-ended Socratic dialogue throughout, the tutor explains the
# pattern, then hands Pat a concrete problem and steps back for a timed think period,
# then walks the solution together asking WHY at each step (never just "what's next").
ALGO_PATTERN_PROMPT = """You are a Socratic tutor for Pat, a Software Engineer II at Paychex, working through the "Algorithm Patterns" phase (owning core interview patterns cold, not memorizing solutions). Current pattern: {concept}. Mastery: {mastery}/5.{book_context}

Follow this flow strictly:
1. First explain WHY this pattern exists and what category of problem it solves, and how to recognize it (don't just define it).
2. Then present ONE concrete problem for Pat to solve, and explicitly tell Pat to take about 5 minutes to think it through before responding — do not give hints or the approach yet.
3. Once Pat responds (attempt, partial idea, or "ready"), walk through the solution together step by step, asking "why does this step work?" or "why not the alternative?" at every step — never just state the next line of the answer.
4. Push Pat to state the time/space complexity and to name at least one situation where this pattern would NOT be the right choice."""

# Teach-back flips the usual roles (the "protege effect"): Pat explains the concept to
# the tutor instead of the tutor explaining it, which surfaces gaps Pat wouldn't notice
# just recognizing/recalling the material passively.
TEACH_BACK_PROMPT = """You are running a "teach-back" session for Pat, a Software Engineer II who builds Java/Spring Boot microservices at Paychex. Pat is going to explain the concept below to you as if teaching it to a student. Do NOT explain the concept yourself or supply the answer. Instead, listen, ask skeptical follow-up questions, probe for hand-waved details, missed trade-offs, and edge cases/failure scenarios, and point out any specific gaps or imprecise reasoning. Only acknowledge Pat has covered it well once the key ideas and trade-offs have actually been demonstrated soundly. Current concept: {concept}. Mastery: {mastery}/5.{book_context}"""

# Phase 6 teach-back is framed specifically as explaining to a junior engineer, which
# pushes Pat to justify the pattern in practical, mentoring terms rather than abstractly.
TEACH_BACK_ALGO_PROMPT = """You are playing a junior backend engineer at Paychex who Pat (a Software Engineer II) is mentoring. Pat is going to explain the algorithm pattern below to you as if you're a junior engineer who has never seen it. Do NOT explain the pattern yourself or supply the answer. Ask the kind of questions a curious junior engineer would ask: "why not just use a simple loop/hash map instead?", "what would break if the input weren't sorted?", "when would this NOT be the right tool?" Push back on hand-waved reasoning and probe for the WHY behind every claim, not just the mechanics. Current pattern: {concept}. Mastery: {mastery}/5.{book_context}"""

BOOK_CONTEXT_TEMPLATE = """

Relevant passages from Pat's uploaded books (cite the title/page when you draw on these):
{passages}"""

# Mastery is evaluated and applied entirely in code (see _score_mastery/apply_mastery_delta
# below), never by the model narrating its own grade — without this instruction models
# reliably imitate the quiz UI unprompted (e.g. "Mastery level: 5/5 — well done!") right
# after giving an explanation the learner never actually had to defend.
NEVER_SELF_GRADE_NOTE = "\n\nNever state a mastery level, score, or grade yourself in your reply (for example, do not write \"Mastery level: X/5\" or declare that Pat has \"demonstrated mastery\"). Mastery is tracked by the system based on Pat's own responses, not your narration of them."

# Reinforces the Socratic contract: an explanation alone never counts as demonstrated
# understanding, so every explanation must be followed by asking the learner to restate
# it in their own words before any credit is possible.
EXPLAIN_BACK_NOTE = "\n\nAfter you give any explanation, always ask Pat to explain that idea back in their own words (or apply it to a concrete case) before treating it as understood — do not just move on or assume it landed."

# Shown when the learner's latest message was a question or too short to have
# demonstrated anything — nudges the tutor to ask for a deeper answer instead of
# treating the exchange as a completed teaching moment.
ENGAGE_MORE_NOTE = "\n\nPat's last message was a question or too brief to demonstrate real understanding of anything yet. Do not treat this as Pat having learned or shown mastery of the concept. Answer briefly if it was a genuine question, then explicitly ask Pat to explain the idea back in their own words, in some depth, before moving on."

# Used for a single, non-streaming judgment of whether a substantive user response
# actually demonstrates understanding, separate from (and after) the tutor's own reply.
MASTERY_EVAL_PROMPT = """You are grading whether a learner's message demonstrates genuine understanding of a concept during a Socratic tutoring conversation. Judge the substance of their reasoning, not phrasing — a hedge, partial understanding, or a wrong-but-reasoned attempt should be scored on what it actually shows, not penalized for not being a "perfect" answer.

Concept: {concept}
The tutor's previous message (explanation or challenge): {prior_turn}
Learner's response: {response}

Score the learner's demonstrated understanding from 0-5 (5 = explained the concept accurately, in their own words, with correct reasoning and no hand-waving; 3 = partial or mixed understanding; 0 = no real understanding shown, evasive, or off-topic).

Respond with ONLY a JSON object of this exact shape, no other text:
{{"score": 0, "explanation": "..."}}"""


def _is_substantive_response(message: str) -> bool:
    """A response only counts as a real attempt at demonstrating understanding if it
    isn't a question and has some real length to it — a quick "ok" or "why is that?"
    never demonstrates anything, no matter what came before it."""
    stripped = message.strip()
    if not stripped or stripped.endswith("?"):
        return False
    return len(re.findall(r"\S+", stripped)) >= MIN_SUBSTANTIVE_WORDS


def _can_evaluate_mastery(conversation_history: list[dict[str, str]], message: str) -> bool:
    """Turn tracker: mastery can only be evaluated once the minimum exchange has
    happened — tutor explains/challenges (the immediately preceding turn), THEN Pat
    responds substantively. A fresh session (no prior turn) or a trivial/question
    response never qualifies, regardless of mastery level or phase."""
    if not conversation_history or conversation_history[-1]["role"] != "assistant":
        return False
    return _is_substantive_response(message)


class ChatRequest(BaseModel):
    concept_id: str
    message: str
    conversation_history: list[dict[str, str]] = []
    mode: Literal["learn", "teach_back"] = "learn"


@router.post("/chat")
async def chat(payload: ChatRequest):
    with connection() as conn:
        concept = conn.execute("SELECT title, mastery_level, phase FROM concepts WHERE id=?", (payload.concept_id,)).fetchone()
    name, mastery = (concept["title"], concept["mastery_level"]) if concept else (payload.concept_id, 0)
    is_algo_phase = concept["phase"] == "Phase 6" if concept else False
    eligible_for_mastery = bool(concept) and _can_evaluate_mastery(payload.conversation_history, payload.message)

    # Retrieve on the concept name rather than the student's raw answer: it stays a
    # consistent, on-topic query regardless of how the student phrases their response,
    # so the tutor reliably grounds itself in the right book passages every turn.
    book_passages = await retrieve_passages(name)
    passages_text = "\n\n".join(f"[{passage['title']}, p. {passage['page']}]\n{passage['text']}" for passage in book_passages)
    book_context = BOOK_CONTEXT_TEMPLATE.format(passages=passages_text) if book_passages else ""
    # Deduplicate by (title, page) — the top-4 chunks can include more than one chunk
    # from the same page, but the citation UI only needs to show each source once.
    sources = list({(passage["title"], passage["page"]): {"title": passage["title"], "page": passage["page"]} for passage in book_passages}.values())

    if payload.mode == "teach_back":
        template = TEACH_BACK_ALGO_PROMPT if is_algo_phase else TEACH_BACK_PROMPT
    else:
        template = ALGO_PATTERN_PROMPT if is_algo_phase else PROMPT
    system_prompt = template.format(concept=name, mastery=mastery, book_context=book_context) + NEVER_SELF_GRADE_NOTE + EXPLAIN_BACK_NOTE
    if not eligible_for_mastery:
        system_prompt += ENGAGE_MORE_NOTE
    messages = [{"role": "system", "content": system_prompt}, *payload.conversation_history, {"role": "user", "content": payload.message}]

    async def _evaluate_mastery() -> tuple[bool, int]:
        """Grades Pat's just-submitted response (not the tutor's upcoming reply) against
        the tutor's prior turn, and applies a real mastery delta only when the exchange
        earned it. Returns (mastery_updated, mastery_level)."""
        prior_turn = payload.conversation_history[-1]["content"]
        graded = await complete_json(
            [{"role": "user", "content": MASTERY_EVAL_PROMPT.format(concept=name, prior_turn=prior_turn, response=payload.message)}],
            model_key="evaluation",
        )
        score = max(0, min(5, int(graded["score"])))
        with connection() as conn:
            new_level = apply_mastery_delta(conn, payload.concept_id, score >= 3)
        return True, new_level

    async def events():
        try:
            async for token in stream_chat(messages):
                yield f"data: {json.dumps({'token': token})}\n\n"
            if sources:
                yield f"data: {json.dumps({'sources': sources})}\n\n"
        except Exception:
            # The stream's HTTP status is already 200 by the time a mid-stream error
            # happens (headers are flushed on the first yield), so this can't surface
            # as an HTTP error status — send an SSE error event the frontend can render.
            logger.exception("Tutor chat stream failed for concept %s", payload.concept_id)
            yield f"data: {json.dumps({'error': 'The tutor is unavailable right now. Please try again.'})}\n\n"

        mastery_updated, mastery_level = False, mastery
        if eligible_for_mastery:
            try:
                mastery_updated, mastery_level = await _evaluate_mastery()
            except Exception:
                # Mastery evaluation is a bonus judgment on top of the conversation — if
                # the evaluation model is unreachable/errors, the chat itself still
                # succeeded, so we just report no mastery change rather than fail the turn.
                logger.exception("Mastery evaluation failed for concept %s", payload.concept_id)
        yield f"data: {json.dumps({'mastery_updated': mastery_updated, 'mastery_level': mastery_level})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


class MessagePayload(BaseModel):
    concept_id: str
    session_id: str
    role: Literal["user", "assistant"]
    content: str


def _latest_session_id(conn, concept_id: str) -> str | None:
    row = conn.execute(
        "SELECT session_id FROM sessions WHERE concept_id=? AND session_id IS NOT NULL ORDER BY started_at DESC, id DESC LIMIT 1",
        (concept_id,),
    ).fetchone()
    return row["session_id"] if row else None


@router.get("/history/{concept_id}")
def get_history(concept_id: str):
    """Returns the most recent study session's full conversation for a concept, so the
    Study page can restore it after a navigation/unmount. If the concept has no prior
    session, a new one is started (and stored in `sessions`) so subsequent POST
    /tutor/message calls have a session_id to attach to."""
    with connection() as conn:
        session_id = _latest_session_id(conn, concept_id)
        if session_id is None:
            session_id = str(uuid4())
            conn.execute("INSERT INTO sessions (session_id, concept_id) VALUES (?, ?)", (session_id, concept_id))
            return {"session_id": session_id, "messages": []}
        rows = conn.execute(
            "SELECT role, content FROM conversation_messages WHERE concept_id=? AND session_id=? ORDER BY id",
            (concept_id, session_id),
        ).fetchall()
    return {"session_id": session_id, "messages": [dict(row) for row in rows]}


@router.post("/message")
def save_message(payload: MessagePayload):
    """Persists a single chat turn (called by the frontend right after a user message is
    sent, and again once the assistant's streamed reply finishes) so the conversation
    survives navigating away from the Study page."""
    with connection() as conn:
        conn.execute(
            "INSERT INTO conversation_messages (concept_id, session_id, role, content) VALUES (?, ?, ?, ?)",
            (payload.concept_id, payload.session_id, payload.role, payload.content),
        )
    return {"saved": True}


@router.delete("/history/{concept_id}")
def clear_history(concept_id: str):
    """Clears all saved conversation turns and sessions for a concept, so Pat can
    restart it from scratch; the next GET /tutor/history call will start a fresh
    session_id since none remain."""
    with connection() as conn:
        conn.execute("DELETE FROM conversation_messages WHERE concept_id=?", (concept_id,))
        conn.execute("DELETE FROM sessions WHERE concept_id=?", (concept_id,))
    return {"cleared": True}

