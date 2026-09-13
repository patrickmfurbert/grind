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
