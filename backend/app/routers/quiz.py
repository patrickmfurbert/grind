import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import connection
from ..services.openrouter import complete_json
from ..services.rag import retrieve
from ..services.spaced_repetition import schedule_review
from .progress import apply_mastery_delta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quiz", tags=["quiz"])

# Comprehension questions are recognition-based (good for fast, frequent review and
# catching specific misconceptions via distractors); application/connection questions
# require producing an explanation from memory, which retains better but can't be
# auto-graded, so those stay free-response and get LLM-evaluated on submit.
QUIZ_TYPE_GUIDANCE = {
    "comprehension": "Write 2-3 multiple_choice questions that test recognition of core facts and definitions. Distractors should reflect plausible misconceptions, not random wrong answers.",
    "application": "Write 2 free_response questions that ask the learner to apply the concept to a concrete scenario or trade-off decision.",
    "connection": "Write 2 free_response questions that ask the learner to relate this concept to others they've studied, or draw an analogy.",
}

GENERATE_PROMPT = """You write quiz questions for a spaced-repetition learning app. Generate quiz questions for this concept:

Title: {title}
Description: {description}
{book_context}
{guidance}

Respond with ONLY a JSON object of this exact shape, no other text:
{{"questions": [{{"type": "multiple_choice", "prompt": "...", "options": ["...", "...", "...", "..."], "correct_answer": "..."}}, {{"type": "free_response", "prompt": "...", "correct_answer": "A model answer covering the key point(s), used only for grading."}}]}}

"type" must be either "multiple_choice" or "free_response". "options" is required (and must include "correct_answer" verbatim as one of the entries) for multiple_choice, and omitted for free_response."""

GRADE_PROMPT = """You are grading a learner's free-response answer for a spaced-repetition quiz.

Concept: {concept}
Question: {prompt}
Model answer: {correct_answer}
Learner's answer: {answer}

Score the learner's answer from 0-5 (5 = fully correct and well-reasoned, 3 = partially correct, 0 = incorrect or blank), and give one or two sentences of specific feedback on what's missing or wrong.

Respond with ONLY a JSON object of this exact shape, no other text:
{{"score": 0, "explanation": "..."}}"""


class GenerateRequest(BaseModel):
    concept_id: str
    quiz_type: str
    use_book_rag: bool = False


class SubmitRequest(BaseModel):
    concept_id: str
    question_id: str
    answer: str
    quiz_type: str = "comprehension"


@router.post("/generate")
async def generate(payload: GenerateRequest):
    with connection() as conn:
        concept = conn.execute("SELECT title, description FROM concepts WHERE id=?", (payload.concept_id,)).fetchone()
    if not concept:
        raise HTTPException(404, f"Unknown concept: {payload.concept_id}")

    book_context = ""
    if payload.use_book_rag:
        passages = await retrieve(concept["title"])
        if passages:
            book_context = f"\nRelevant book passages:\n{passages}\n"

    guidance = QUIZ_TYPE_GUIDANCE.get(payload.quiz_type, QUIZ_TYPE_GUIDANCE["comprehension"])
    prompt = GENERATE_PROMPT.format(title=concept["title"], description=concept["description"] or "", book_context=book_context, guidance=guidance)

    try:
        generated = await complete_json([{"role": "user", "content": prompt}], model_key="quiz_gen")
        raw_questions = generated["questions"]
        if not raw_questions:
            raise ValueError("model returned zero questions")
    except Exception:
        logger.exception("Quiz generation failed for concept %s", payload.concept_id)
        raise HTTPException(502, "Quiz generation is temporarily unavailable. Please try again.")

    questions = []
    with connection() as conn:
        for question in raw_questions:
            question_id = str(uuid.uuid4())
            question_type = question.get("type", "free_response")
            options = question.get("options")
            conn.execute(
                "INSERT INTO quiz_questions(id, concept_id, quiz_type, question_type, prompt, options, correct_answer) VALUES(?,?,?,?,?,?,?)",
                (question_id, payload.concept_id, payload.quiz_type, question_type, question["prompt"], json.dumps(options) if options else None, question.get("correct_answer")),
            )
            questions.append({"id": question_id, "type": question_type, "prompt": question["prompt"], "options": options})
    return {"questions": questions}


@router.post("/submit")
async def submit(payload: SubmitRequest):
    with connection() as conn:
        stored = conn.execute("SELECT * FROM quiz_questions WHERE id=?", (payload.question_id,)).fetchone()

    if stored and stored["question_type"] == "multiple_choice":
        correct = payload.answer.strip() == (stored["correct_answer"] or "").strip()
        score = 5 if correct else 1
        explanation = "Correct!" if correct else f"Not quite — the correct answer is: {stored['correct_answer']}"
    else:
        prompt_text = stored["prompt"] if stored else "Explain this concept."
        model_answer = stored["correct_answer"] if stored else ""
        try:
            graded = await complete_json(
                [{"role": "user", "content": GRADE_PROMPT.format(concept=payload.concept_id, prompt=prompt_text, correct_answer=model_answer, answer=payload.answer)}],
                model_key="evaluation",
            )
            score = max(0, min(5, int(graded["score"])))
            explanation = graded["explanation"]
        except Exception:
            # Grading is best-effort — if the evaluation model is unreachable/errors, fall
            # back to a neutral pass so a flaky LLM call doesn't block the review flow.
            logger.exception("Free-response grading failed for question %s", payload.question_id)
            score, explanation = 3, "Couldn't automatically grade this answer right now; treated as a partial pass."
        correct = score >= 3

    with connection() as conn:
        state = conn.execute("SELECT * FROM spaced_repetition WHERE concept_id=?", (payload.concept_id,)).fetchone()
        review = schedule_review(score, *(state[key] for key in ("interval_days", "ease_factor", "repetitions")) if state else ())
        conn.execute(
            "INSERT INTO quiz_results(concept_id,quiz_type,question_id,question_type,answer,correct,score) VALUES(?,?,?,?,?,?,?)",
            (payload.concept_id, payload.quiz_type, payload.question_id, stored["question_type"] if stored else None, payload.answer, correct, score),
        )
        conn.execute("""INSERT INTO spaced_repetition(concept_id,next_review,interval_days,ease_factor,repetitions) VALUES(?,?,?,?,?)
                     ON CONFLICT(concept_id) DO UPDATE SET next_review=excluded.next_review, interval_days=excluded.interval_days, ease_factor=excluded.ease_factor, repetitions=excluded.repetitions""",
                     (payload.concept_id, review.next_review.isoformat(), review.interval_days, review.ease_factor, review.repetitions))
        mastery_level = apply_mastery_delta(conn, payload.concept_id, correct)

    return {"correct": correct, "score": score, "explanation": explanation, "mastery_level": mastery_level, "next_review_date": review.next_review.isoformat()}


@router.get("/due-today")
def due_today():
    with connection() as conn:
        rows = conn.execute("""SELECT c.* FROM concepts c JOIN spaced_repetition s ON c.id=s.concept_id
                            WHERE s.next_review <= ?""", (datetime.now().isoformat(),)).fetchall()
    return {"concepts": [dict(row) for row in rows]}
