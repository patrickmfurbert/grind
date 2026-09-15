import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..database import connection

router = APIRouter(prefix="/curriculum", tags=["curriculum"])

_CURRICULUM_PATH = Path(__file__).parent.parent / "data" / "curriculum.json"


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


@router.get("/code-demos/{concept_id}")
def code_demos(concept_id: str):
    """Reads code_demos straight from curriculum.json (a static reference field, not
    stored in the concepts table) so Code Lab can offer a couple of pre-filled starter
    exercises for concepts that define them, e.g. Phase 6's algorithm patterns."""
    data = json.loads(_CURRICULUM_PATH.read_text())
    match = next((c for c in data if c["id"] == concept_id), None)
    if not match:
        raise HTTPException(404, "Concept not found")
    return {"code_demos": match.get("code_demos", [])}
