import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import initialize_database
from .routers import books, code, curriculum, progress, quiz, tutor


@asynccontextmanager
async def lifespan(_: FastAPI):
    curriculum_data = json.loads((Path(__file__).parent / "data" / "curriculum.json").read_text())
    initialize_database(curriculum_data)
    yield


app = FastAPI(title="GRIND API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3001"], allow_methods=["*"], allow_headers=["*"])
for router in (curriculum.router, tutor.router, quiz.router, progress.router, code.router, books.router):
    app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
