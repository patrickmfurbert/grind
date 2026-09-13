import uuid
from pathlib import Path

import fitz
from qdrant_client.models import PointStruct

from .embeddings import embed
from .qdrant import index_chunks


def chunk_text(text: str, size: int = 2_000, overlap: int = 250) -> list[str]:
    return [text[start:start + size] for start in range(0, len(text), size - overlap) if text[start:start + size].strip()]


async def process_pdf(path: Path, book_id: str, title: str) -> int:
    document = fitz.open(path)
    chunks = [(page.number + 1, chunk) for page in document for chunk in chunk_text(page.get_text())]
    if not chunks:
        return 0
    vectors = await embed([text for _, text in chunks])
    index_chunks([PointStruct(id=str(uuid.uuid4()), vector=vector, payload={"book_id": book_id, "title": title, "page": page, "text": text}) for (page, text), vector in zip(chunks, vectors)], len(vectors[0]))
    return len(chunks)
