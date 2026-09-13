import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..database import connection
from ..services.openrouter import stream_chat

router = APIRouter(prefix="/tutor", tags=["tutor"])

PROMPT = """You are a Socratic tutor for Pat, a Software Engineer II who builds Java/Spring Boot microservices at Paychex using MongoDB, Kafka, Dapr, OpenShift, Kong, Jenkins, Gradle, Splunk, and OpenTelemetry. Pat transitioned from clinical nursing. Start from why, use useful visual or real-world analogies, make Pat defend answers, ask follow-up questions about failures and trade-offs, and get harder with demonstrated mastery. Current concept: {concept}. Mastery: {mastery}/5."""


class ChatRequest(BaseModel):
    concept_id: str
    message: str
    conversation_history: list[dict[str, str]] = []


@router.post("/chat")
async def chat(payload: ChatRequest):
    with connection() as conn:
        concept = conn.execute("SELECT title, mastery_level FROM concepts WHERE id=?", (payload.concept_id,)).fetchone()
    name, mastery = (concept["title"], concept["mastery_level"]) if concept else (payload.concept_id, 0)
    messages = [{"role": "system", "content": PROMPT.format(concept=name, mastery=mastery)}, *payload.conversation_history, {"role": "user", "content": payload.message}]

    async def events():
        async for token in stream_chat(messages):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
