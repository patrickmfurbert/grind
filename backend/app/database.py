import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS concepts (
 id TEXT PRIMARY KEY, phase TEXT NOT NULL, title TEXT NOT NULL, description TEXT,
 prerequisites TEXT NOT NULL DEFAULT '[]', mastery_level INTEGER DEFAULT 0 CHECK(mastery_level BETWEEN 0 AND 5),
 last_studied TIMESTAMP, total_time_seconds INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS quiz_results (
 id INTEGER PRIMARY KEY AUTOINCREMENT, concept_id TEXT NOT NULL, quiz_type TEXT NOT NULL,
 question_id TEXT NOT NULL, answer TEXT, correct BOOLEAN, score INTEGER,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(concept_id) REFERENCES concepts(id)
);
CREATE TABLE IF NOT EXISTS spaced_repetition (
 concept_id TEXT PRIMARY KEY, next_review TIMESTAMP, interval_days INTEGER DEFAULT 1,
 ease_factor REAL DEFAULT 2.5, repetitions INTEGER DEFAULT 0, FOREIGN KEY(concept_id) REFERENCES concepts(id)
);
CREATE TABLE IF NOT EXISTS books (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, filename TEXT NOT NULL, phase TEXT,
 chunks_indexed INTEGER DEFAULT 0, upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 processing_status TEXT DEFAULT 'pending'
);
CREATE TABLE IF NOT EXISTS sessions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, concept_id TEXT NOT NULL, started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 ended_at TIMESTAMP, duration_seconds INTEGER, mastery_before INTEGER, mastery_after INTEGER,
 FOREIGN KEY(concept_id) REFERENCES concepts(id)
);
"""


@contextmanager
def connection():
    database = Path(get_settings().sqlite_db_path)
    database.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def initialize_database(curriculum: list[dict]) -> None:
    with connection() as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            """INSERT OR IGNORE INTO concepts(id, phase, title, description, prerequisites)
               VALUES (:id, :phase, :title, :description, :prerequisites)""",
            [{**concept, "prerequisites": json.dumps(concept.get("prerequisites", []))} for concept in curriculum],
        )
