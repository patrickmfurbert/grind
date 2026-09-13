from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..database import connection
from ..services.spaced_repetition import schedule_review

router = APIRouter(prefix="/quiz", tags=["quiz"])


class GenerateRequest(BaseModel):
    concept_id: str
    quiz_type: str
    use_book_rag: bool = False


class SubmitRequest(BaseModel):
    concept_id: str
    question_id: str
    answer: str
    quiz_type: str = "comprehension"
    score: int = Field(ge=0, le=5)


@router.post("/generate")
def generate(payload: GenerateRequest):
    return {"questions": [{"id": f"{payload.concept_id}-why", "type": payload.quiz_type, "prompt": "Explain why this concept exists, then name a trade-off it creates."}]}


@router.post("/submit")
def submit(payload: SubmitRequest):
    with connection() as conn:
        state = conn.execute("SELECT * FROM spaced_repetition WHERE concept_id=?", (payload.concept_id,)).fetchone()
        review = schedule_review(payload.score, *(state[key] for key in ("interval_days", "ease_factor", "repetitions")) if state else ())
        conn.execute("INSERT INTO quiz_results(concept_id,quiz_type,question_id,answer,correct,score) VALUES(?,?,?,?,?,?)", (payload.concept_id, payload.quiz_type, payload.question_id, payload.answer, payload.score >= 3, payload.score))
        conn.execute("""INSERT INTO spaced_repetition(concept_id,next_review,interval_days,ease_factor,repetitions) VALUES(?,?,?,?,?)
                     ON CONFLICT(concept_id) DO UPDATE SET next_review=excluded.next_review, interval_days=excluded.interval_days, ease_factor=excluded.ease_factor, repetitions=excluded.repetitions""",
                     (payload.concept_id, review.next_review.isoformat(), review.interval_days, review.ease_factor, review.repetitions))
    return {"correct": payload.score >= 3, "explanation": "Review your answer against the concept's trade-offs.", "next_review_date": review.next_review.isoformat()}


@router.get("/due-today")
def due_today():
    with connection() as conn:
        rows = conn.execute("""SELECT c.* FROM concepts c JOIN spaced_repetition s ON c.id=s.concept_id
                            WHERE s.next_review <= ?""", (datetime.now().isoformat(),)).fetchall()
    return {"concepts": [dict(row) for row in rows]}
