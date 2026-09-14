import json
import logging
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..database import connection
from ..services.openrouter import stream_chat
from ..services.rag import retrieve_passages

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tutor", tags=["tutor"])

PROMPT = """You are a Socratic tutor for Pat, a Software Engineer II who builds Java/Spring Boot microservices at Paychex using MongoDB, Kafka, Dapr, OpenShift, Kong, Jenkins, Gradle, Splunk, and OpenTelemetry. Pat transitioned from clinical nursing. Start from why, use useful visual or real-world analogies, make Pat defend answers, ask follow-up questions about failures and trade-offs, and get harder with demonstrated mastery. Current concept: {concept}. Mastery: {mastery}/5.{book_context}"""

BOOK_CONTEXT_TEMPLATE = """

Relevant passages from Pat's uploaded books (cite the title/page when you draw on these):
{passages}"""


class ChatRequest(BaseModel):
    concept_id: str
    message: str
    conversation_history: list[dict[str, str]] = []


@router.post("/chat")
async def chat(payload: ChatRequest):
    with connection() as conn:
        concept = conn.execute("SELECT title, mastery_level FROM concepts WHERE id=?", (payload.concept_id,)).fetchone()
    name, mastery = (concept["title"], concept["mastery_level"]) if concept else (payload.concept_id, 0)

    # Retrieve on the concept name rather than the student's raw answer: it stays a
    # consistent, on-topic query regardless of how the student phrases their response,
    # so the tutor reliably grounds itself in the right book passages every turn.
    book_passages = await retrieve_passages(name)
    passages_text = "\n\n".join(f"[{passage['title']}, p. {passage['page']}]\n{passage['text']}" for passage in book_passages)
    book_context = BOOK_CONTEXT_TEMPLATE.format(passages=passages_text) if book_passages else ""
    # Deduplicate by (title, page) — the top-4 chunks can include more than one chunk
    # from the same page, but the citation UI only needs to show each source once.
    sources = list({(passage["title"], passage["page"]): {"title": passage["title"], "page": passage["page"]} for passage in book_passages}.values())

    messages = [{"role": "system", "content": PROMPT.format(concept=name, mastery=mastery, book_context=book_context)}, *payload.conversation_history, {"role": "user", "content": payload.message}]

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

