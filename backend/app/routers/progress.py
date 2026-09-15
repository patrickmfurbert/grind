from datetime import date, timedelta

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..database import connection

router = APIRouter(prefix="/progress", tags=["progress"])


class MasteryUpdate(BaseModel):
    concept_id: str
    mastery_level: int = Field(ge=0, le=5)


@router.get("/summary")
def summary():
    with connection() as conn:
        overall = conn.execute("SELECT COUNT(*) count, COALESCE(SUM(mastery_level), 0) score FROM concepts").fetchone()
        phases = conn.execute("SELECT phase, AVG(mastery_level) mastery FROM concepts GROUP BY phase").fetchall()
        studied = {r["day"] for r in conn.execute("SELECT DISTINCT date(started_at) day FROM sessions").fetchall()}
        streak = 0
        current = date.today()
        while current.isoformat() in studied:
            streak += 1
            current -= timedelta(days=1)
    return {"overall_pct": round(100 * overall["score"] / max(1, overall["count"] * 5)), "by_phase": [dict(r) for r in phases], "streak": streak, "time_spent": 0}


@router.post("/mastery")
def update_mastery(payload: MasteryUpdate):
    with connection() as conn:
        conn.execute("UPDATE concepts SET mastery_level=?, last_studied=CURRENT_TIMESTAMP WHERE id=?", (payload.mastery_level, payload.concept_id))
    return {"updated": True}


@router.get("/weak-spots")
def weak_spots(limit: int = 5):
    """Concepts the learner has studied but hasn't mastered yet, ranked by how often
    they get answered wrong first (so a frequently-missed pattern surfaces above one
    that's merely never been reviewed), then by mastery/recency — surfaces where to
    focus instead of only showing what's due today by the SM-2 schedule."""
    with connection() as conn:
        rows = conn.execute(
            """SELECT c.*, COALESCE(w.wrong_count, 0) AS wrong_count
               FROM concepts c
               LEFT JOIN (
                   SELECT concept_id, COUNT(*) AS wrong_count
                   FROM quiz_results WHERE correct = 0
                   GROUP BY concept_id
               ) w ON w.concept_id = c.id
               WHERE c.last_studied IS NOT NULL AND c.mastery_level < 5
               ORDER BY wrong_count DESC, c.mastery_level ASC, c.last_studied ASC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return {"concepts": [dict(row) for row in rows]}


def apply_mastery_delta(conn, concept_id: str, correct: bool) -> int:
    """Nudges a concept's mastery_level by +1 (capped at 5) on a correct/passing quiz
    answer, or -1 (floored at 0) otherwise. Used by quiz submission so mastery is
    quiz-driven rather than self-reported. Returns the new mastery_level."""
    row = conn.execute("SELECT mastery_level FROM concepts WHERE id=?", (concept_id,)).fetchone()
    current = row["mastery_level"] if row else 0
    updated = min(5, current + 1) if correct else max(0, current - 1)
    conn.execute("UPDATE concepts SET mastery_level=?, last_studied=CURRENT_TIMESTAMP WHERE id=?", (updated, concept_id))
    return updated
