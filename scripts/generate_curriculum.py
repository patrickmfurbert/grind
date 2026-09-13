"""Generate curriculum enrichment content through OpenRouter.

The checked-in curriculum tree is intentionally useful without an API key. This
script is the opt-in batch enrichment entry point for deployments that configure
OPENROUTER_API_KEY.
"""
import asyncio
import json
from pathlib import Path

from backend.app.services.openrouter import MODELS


async def main() -> None:
    source = Path("backend/app/data/curriculum.json")
    concepts = json.loads(source.read_text())
    target = Path("curriculum/content")
    target.mkdir(parents=True, exist_ok=True)
    for concept in concepts:
        destination = target / f"{concept['id']}.json"
        if destination.exists():
            continue
        destination.write_text(json.dumps({
            **concept,
            "generation_model": MODELS["content_gen"],
            "status": "pending_generation",
            "prompt": f"Create bottom-up explanations, misconceptions, trade-offs, interview points, quizzes, and code demos for {concept['title']}.",
        }, indent=2) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
