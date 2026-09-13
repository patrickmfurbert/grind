import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from ..config import get_settings
from ..database import connection
from ..services.pdf_processor import process_pdf

router = APIRouter(prefix="/books", tags=["books"])


async def index_book(book_id: str, path: Path, title: str) -> None:
    try:
        count = await process_pdf(path, book_id, title)
        with connection() as conn:
            conn.execute("UPDATE books SET chunks_indexed=?, processing_status='ready' WHERE id=?", (count, book_id))
    except Exception:
        with connection() as conn:
            conn.execute("UPDATE books SET processing_status='failed' WHERE id=?", (book_id,))


@router.post("/upload")
async def upload(background_tasks: BackgroundTasks, file: UploadFile = File(...), title: str = Form(...), phase: str | None = Form(None)):
    if file.content_type != "application/pdf":
        raise HTTPException(415, "Only PDF uploads are supported")
    book_id = str(uuid.uuid4())
    directory = get_settings().upload_path
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{book_id}.pdf"
    with path.open("wb") as destination:
        shutil.copyfileobj(file.file, destination)
    with connection() as conn:
        conn.execute("INSERT INTO books(id,title,filename,phase,processing_status) VALUES(?,?,?,?,?)", (book_id, title, file.filename or path.name, phase, "processing"))
    background_tasks.add_task(index_book, book_id, path, title)
    return {"book_id": book_id, "chunks_indexed": 0}


@router.get("")
def list_books():
    with connection() as conn:
        rows = conn.execute("SELECT * FROM books ORDER BY upload_date DESC").fetchall()
    return {"books": [dict(row) for row in rows]}
