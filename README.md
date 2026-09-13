# GRIND

Personal, mobile-first learning platform for distributed systems, backend engineering, AI/ML, CI/CD, Kubernetes, observability, and system design. It couples Socratic tutoring with a concept map, spaced repetition, RAG-backed PDFs, and executable code experiments.

## Run locally

1. Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY`.
2. Create the Python environment: `python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt`.
3. Start the API: `.venv/bin/uvicorn backend.app.main:app --reload --port 8001`.
4. In another shell, run `npm --prefix frontend install && npm --prefix frontend run dev`.

The frontend is at `http://localhost:3001`; API documentation is at `http://localhost:8001/docs`.

## Tests

Backend: `pip install -r backend/requirements.txt && pytest -q` (27 tests covering curriculum, progress, quiz/SM-2, code execution, book upload, and tutor streaming with mocked OpenRouter calls).

Frontend: `npm --prefix frontend test` (27 Vitest + React Testing Library tests covering components, hooks, and the Zustand store).

Both suites run in CI on every push/PR via `.github/workflows/test.yml`; deploy only runs after tests pass.

## Services

Run Ollama with `nomic-embed-text` and Qdrant before uploading PDFs. `scripts/setup_qdrant.sh` starts the Qdrant container; `scripts/install.sh` performs the host setup on Z420.
