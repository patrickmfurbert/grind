def test_upload_rejects_non_pdf_content_type(client):
    response = client.post(
        "/books/upload",
        files={"file": ("notes.txt", b"just text", "text/plain")},
        data={"title": "Notes"},
    )
    assert response.status_code == 415


def test_list_books_starts_empty(client):
    response = client.get("/books")
    assert response.status_code == 200
    assert response.json() == {"books": []}


def test_upload_pdf_creates_processing_record(client, monkeypatch):
    async def fake_index_book(book_id, path, title):
        return None

    monkeypatch.setattr("backend.app.routers.books.index_book", fake_index_book)

    response = client.post(
        "/books/upload",
        files={"file": ("kleppmann.pdf", b"%PDF-1.4 fake", "application/pdf")},
        data={"title": "Designing Data-Intensive Applications", "phase": "Phase 1"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["book_id"]
    assert body["chunks_indexed"] == 0

    books = client.get("/books").json()["books"]
    assert len(books) == 1
    assert books[0]["title"] == "Designing Data-Intensive Applications"
