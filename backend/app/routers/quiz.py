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
    "pattern_recognition": "Write 2-3 multiple_choice questions. Each must describe a realistic backend-engineering problem scenario (e.g. rate limiting, log analysis, service reachability, cache eviction, scheduling, telemetry cleanup) WITHOUT mentioning the pattern name or showing any code, then ask which algorithm pattern applies and why. Options should be plausible alternative patterns; the explanation for the correct choice should come out during grading/feedback, not in the question itself.",
}

# Phase 6 ("Algorithm Patterns") quizzes get extra guidance appended on top of the
# base quiz-type guidance, so the same comprehension/application/connection question
# types are still generated, but framed around interview-pattern mastery specifically.
PHASE_6_APPLICATION_GUIDANCE = "\nFrame each scenario as a real backend engineering problem (e.g. rate limiting, log analysis, service reachability, cache eviction, scheduling, telemetry cleanup) — not an abstract puzzle."
PHASE_6_CONNECTION_GUIDANCE = "\nAt least one question should ask the learner to connect this pattern to their own backend/production experience (e.g. at Paychex) — where might this exact pattern have shown up in real systems they've worked on?"

GENERATE_PROMPT = """You write quiz questions for a spaced-repetition learning app. Generate quiz questions for this concept:

Title: {title}
Description: {description}
{book_context}
{guidance}
{recent_prompts}

Respond with ONLY a JSON object of this exact shape, no other text:
{{"questions": [{{"type": "multiple_choice", "prompt": "...", "options": ["...", "...", "...", "..."], "correct_answer": "..."}}, {{"type": "free_response", "prompt": "...", "correct_answer": "A model answer covering the key point(s), used only for grading."}}]}}

"type" must be either "multiple_choice" or "free_response". "options" is required (and must include "correct_answer" verbatim as one of the entries) for multiple_choice, and omitted for free_response."""

# Interleaved questions are a single, quick recognition check on a *different*, weaker
# concept mixed into the current quiz — interleaving forces discrimination between
# concepts instead of blocked, single-topic practice, which research shows improves
# long-term retention over blocked practice alone.
INTERLEAVE_GUIDANCE = "Write exactly 1 multiple_choice question that tests recognition of a core fact about this concept. Distractors should reflect plausible misconceptions."

GRADE_PROMPT = """You are grading a learner's free-response answer for a spaced-repetition quiz.

Concept: {concept}
Question: {prompt}
Model answer: {correct_answer}
Learner's answer: {answer}

Score the learner's answer from 0-5 (5 = fully correct and well-reasoned, 3 = partially correct, 0 = incorrect or blank). Give one or two sentences of feedback explaining the score. Then separately name the single most important specific idea, trade-off, or detail the learner is missing or got wrong — or null if their answer was already fully correct.

Respond with ONLY a JSON object of this exact shape, no other text:
{{"score": 0, "explanation": "...", "gap": "..." }}

"gap" must be null when the answer was fully correct."""

HINT_PROMPT = """You are giving a scaffolded hint for a spaced-repetition quiz question. Do NOT reveal the answer or state it outright — nudge the learner's thinking with a leading question, a partial clue, or a smaller related question they can reason from.

Concept: {concept}
Question: {prompt}
Model answer (for your reference only — never state this directly): {correct_answer}

Respond with ONLY a JSON object of this exact shape, no other text:
{{"hint": "..."}}"""


class GenerateRequest(BaseModel):
    concept_id: str
    quiz_type: str
    use_book_rag: bool = False
    include_interleaved: bool = True


class SubmitRequest(BaseModel):
    question_id: str
    answer: str


class HintRequest(BaseModel):
    question_id: str


# How many of the most recently generated prompts (for this concept + quiz type) to
# feed back to the LLM so it can rotate to new questions instead of repeating itself.
RECENT_PROMPT_LIMIT = 8


def _recent_prompts_note(conn, concept_id: str, quiz_type: str) -> str:
    recent = conn.execute(
        "SELECT prompt FROM quiz_questions WHERE concept_id=? AND quiz_type=? ORDER BY created_at DESC LIMIT ?",
        (concept_id, quiz_type, RECENT_PROMPT_LIMIT),
    ).fetchall()
    if not recent:
        return ""
    seen = "\n".join(f"- {row['prompt']}" for row in recent)
    return f"\nThe learner has already seen these questions recently — write different ones, not close rewordings:\n{seen}\n"


async def _generate_questions(conn, concept_id: str, title: str, description: str, quiz_type: str, guidance: str, book_context: str = "") -> list[dict]:
    """Calls the LLM for one concept and persists each returned question into
    quiz_questions, keyed by concept_id (used both for the main concept and, when
    interleaving, for a second concept mixed into the same quiz)."""
    recent_prompts = _recent_prompts_note(conn, concept_id, quiz_type)
    prompt = GENERATE_PROMPT.format(title=title, description=description or "", book_context=book_context, guidance=guidance, recent_prompts=recent_prompts)
    generated = await complete_json([{"role": "user", "content": prompt}], model_key="quiz_gen")
    raw_questions = generated["questions"]
    if not raw_questions:
        raise ValueError("model returned zero questions")

    questions = []
    for question in raw_questions:
        question_id = str(uuid.uuid4())
        question_type = question.get("type", "free_response")
        options = question.get("options")
        conn.execute(
            "INSERT INTO quiz_questions(id, concept_id, quiz_type, question_type, prompt, options, correct_answer) VALUES(?,?,?,?,?,?,?)",
            (question_id, concept_id, quiz_type, question_type, question["prompt"], json.dumps(options) if options else None, question.get("correct_answer")),
        )
        questions.append({"id": question_id, "type": question_type, "prompt": question["prompt"], "options": options, "concept_id": concept_id, "concept_title": title})
    return questions


def _pick_interleave_concept(conn, exclude_id: str):
    """Picks the weakest, previously-studied concept other than the one being quizzed,
    to mix a single recall question from into the current quiz (interleaved practice)."""
    return conn.execute(
        "SELECT id, title, description FROM concepts WHERE id != ? AND last_studied IS NOT NULL ORDER BY mastery_level ASC, last_studied ASC LIMIT 1",
        (exclude_id,),
    ).fetchone()


@router.post("/generate")
async def generate(payload: GenerateRequest):
    with connection() as conn:
        concept = conn.execute("SELECT title, description, phase FROM concepts WHERE id=?", (payload.concept_id,)).fetchone()
        if not concept:
            raise HTTPException(404, f"Unknown concept: {payload.concept_id}")

    book_context = ""
    if payload.use_book_rag:
        passages = await retrieve(concept["title"])
        if passages:
            book_context = f"\nRelevant book passages:\n{passages}\n"

    guidance = QUIZ_TYPE_GUIDANCE.get(payload.quiz_type, QUIZ_TYPE_GUIDANCE["comprehension"])
    if concept["phase"] == "Phase 6":
        if payload.quiz_type == "application":
            guidance += PHASE_6_APPLICATION_GUIDANCE
        elif payload.quiz_type == "connection":
            guidance += PHASE_6_CONNECTION_GUIDANCE

    try:
        with connection() as conn:
            questions = await _generate_questions(conn, payload.concept_id, concept["title"], concept["description"], payload.quiz_type, guidance, book_context)
    except Exception:
        logger.exception("Quiz generation failed for concept %s", payload.concept_id)
        raise HTTPException(502, "Quiz generation is temporarily unavailable. Please try again.")

    if payload.include_interleaved:
        try:
            with connection() as conn:
                weak = _pick_interleave_concept(conn, payload.concept_id)
                if weak:
                    interleaved = await _generate_questions(conn, weak["id"], weak["title"], weak["description"], "comprehension", INTERLEAVE_GUIDANCE)
                    questions += interleaved
        except Exception:
            # Interleaving is a bonus on top of the main quiz — if it fails, the
            # learner still gets their primary quiz rather than a hard failure.
            logger.exception("Interleaved question generation failed (concept excluded: %s)", payload.concept_id)

    return {"questions": questions}


@router.post("/submit")
async def submit(payload: SubmitRequest):
    with connection() as conn:
        stored = conn.execute("SELECT * FROM quiz_questions WHERE id=?", (payload.question_id,)).fetchone()
    if not stored:
        raise HTTPException(404, f"Unknown question: {payload.question_id}")

    concept_id, quiz_type = stored["concept_id"], stored["quiz_type"]
    gap = None

    if stored["question_type"] == "multiple_choice":
        correct = payload.answer.strip() == (stored["correct_answer"] or "").strip()
        score = 5 if correct else 1
        explanation = "Correct!" if correct else f"Not quite — the correct answer is: {stored['correct_answer']}"
    else:
        try:
            graded = await complete_json(
                [{"role": "user", "content": GRADE_PROMPT.format(concept=concept_id, prompt=stored["prompt"], correct_answer=stored["correct_answer"] or "", answer=payload.answer)}],
                model_key="evaluation",
            )
            score = max(0, min(5, int(graded["score"])))
            explanation = graded["explanation"]
            gap = graded.get("gap")
        except Exception:
            # Grading is best-effort — if the evaluation model is unreachable/errors, fall
            # back to a neutral pass so a flaky LLM call doesn't block the review flow.
            logger.exception("Free-response grading failed for question %s", payload.question_id)
            score, explanation = 3, "Couldn't automatically grade this answer right now; treated as a partial pass."
        correct = score >= 3

    with connection() as conn:
        state = conn.execute("SELECT * FROM spaced_repetition WHERE concept_id=?", (concept_id,)).fetchone()
        review = schedule_review(score, *(state[key] for key in ("interval_days", "ease_factor", "repetitions")) if state else ())
        conn.execute(
            "INSERT INTO quiz_results(concept_id,quiz_type,question_id,question_type,answer,correct,score) VALUES(?,?,?,?,?,?,?)",
            (concept_id, quiz_type, payload.question_id, stored["question_type"], payload.answer, correct, score),
        )
        conn.execute("""INSERT INTO spaced_repetition(concept_id,next_review,interval_days,ease_factor,repetitions) VALUES(?,?,?,?,?)
                     ON CONFLICT(concept_id) DO UPDATE SET next_review=excluded.next_review, interval_days=excluded.interval_days, ease_factor=excluded.ease_factor, repetitions=excluded.repetitions""",
                     (concept_id, review.next_review.isoformat(), review.interval_days, review.ease_factor, review.repetitions))
        mastery_level = apply_mastery_delta(conn, concept_id, correct)

    return {
        "correct": correct,
        "score": score,
        "explanation": explanation,
        "gap": gap,
        "mastery_level": mastery_level,
        "concept_id": concept_id,
        "next_review_date": review.next_review.isoformat(),
    }


@router.post("/hint")
async def hint(payload: HintRequest):
    with connection() as conn:
        stored = conn.execute("SELECT * FROM quiz_questions WHERE id=?", (payload.question_id,)).fetchone()
        if not stored:
            raise HTTPException(404, f"Unknown question: {payload.question_id}")
        concept = conn.execute("SELECT title FROM concepts WHERE id=?", (stored["concept_id"],)).fetchone()

    concept_title = concept["title"] if concept else stored["concept_id"]
    try:
        result = await complete_json(
            [{"role": "user", "content": HINT_PROMPT.format(concept=concept_title, prompt=stored["prompt"], correct_answer=stored["correct_answer"] or "")}],
            model_key="quiz_gen",
        )
        return {"hint": result["hint"]}
    except Exception:
        logger.exception("Hint generation failed for question %s", payload.question_id)
        raise HTTPException(502, "Couldn't generate a hint right now. Please try again.")


@router.get("/due-today")
def due_today():
    with connection() as conn:
        rows = conn.execute("""SELECT c.* FROM concepts c JOIN spaced_repetition s ON c.id=s.concept_id
                            WHERE s.next_review <= ?""", (datetime.now().isoformat(),)).fetchall()
    return {"concepts": [dict(row) for row in rows]}
