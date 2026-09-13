import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..database import connection

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


@router.get("/phases")
def phases():
    with connection() as conn:
        rows = conn.execute("SELECT * FROM concepts ORDER BY phase, title").fetchall()
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        item = dict(row)
        item["prerequisites"] = json.loads(item["prerequisites"])
        grouped.setdefault(item["phase"], []).append(item)
    return {"phases": [{"name": name, "concepts": concepts} for name, concepts in grouped.items()]}


@router.get("/concept/{concept_id}")
def concept(concept_id: str):
    with connection() as conn:
        row = conn.execute("SELECT * FROM concepts WHERE id = ?", (concept_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Concept not found")
    item = dict(row)
    item["prerequisites"] = json.loads(item["prerequisites"])
    return item
