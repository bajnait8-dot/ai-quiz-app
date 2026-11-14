"""SQLite persistence for generated quizzes and their evaluations.

A single-process SQLite database replaces LangGraph's in-memory checkpointer so
quizzes survive restarts and can be opened through a shareable /quiz/<id> link.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from core.config import settings

_write_lock = threading.Lock()
_local = threading.local()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS quizzes (
    quiz_id       TEXT PRIMARY KEY,
    topic         TEXT NOT NULL,
    intensity     TEXT NOT NULL,
    length        INTEGER NOT NULL,
    questions     TEXT NOT NULL,
    related_topics TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evaluations (
    quiz_id              TEXT PRIMARY KEY REFERENCES quizzes(quiz_id) ON DELETE CASCADE,
    topic                TEXT NOT NULL,
    score                REAL NOT NULL,
    correct_indexes      TEXT NOT NULL,
    incorrect_indexes    TEXT NOT NULL,
    selected_options     TEXT NOT NULL,
    improvement_tips     TEXT NOT NULL,
    links                TEXT NOT NULL,
    created_at           TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connection() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            settings.database_path,
            check_same_thread=False,
            timeout=30,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn


@contextmanager
def _cursor() -> Iterator[sqlite3.Cursor]:
    conn = _connection()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def init_db() -> None:
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    with _write_lock, _cursor() as cur:
        cur.executescript(_SCHEMA)


def _row_to_quiz(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "quiz_id": row["quiz_id"],
        "topic": row["topic"],
        "intensity": row["intensity"],
        "length": row["length"],
        "questions": json.loads(row["questions"]),
        "related_topics": json.loads(row["related_topics"]),
        "created_at": row["created_at"],
    }


def _row_to_evaluation(row: sqlite3.Row) -> dict[str, Any]:
    raw_score = float(row["score"])
    score: int | float = int(raw_score) if raw_score.is_integer() else raw_score
    return {
        "quiz_id": row["quiz_id"],
        "topic": row["topic"],
        "score": score,
        "correct_answers_index": json.loads(row["correct_indexes"]),
        "incorrect_answers_index": json.loads(row["incorrect_indexes"]),
        "selected_options": json.loads(row["selected_options"]),
        "improvement_tips": row["improvement_tips"],
        "links": json.loads(row["links"]),
        "created_at": row["created_at"],
    }


def save_quiz(quiz: dict[str, Any]) -> None:
    with _write_lock, _cursor() as cur:
        cur.execute(
            """
            INSERT OR REPLACE INTO quizzes
                (quiz_id, topic, intensity, length, questions, related_topics, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                quiz["quiz_id"],
                quiz["topic"],
                quiz["intensity"],
                int(quiz["length"]),
                json.dumps(quiz["questions"]),
                json.dumps(quiz.get("related_topics") or []),
                _now(),
            ),
        )


def get_quiz(quiz_id: str) -> dict[str, Any] | None:
    with _write_lock, _cursor() as cur:
        cur.execute("SELECT * FROM quizzes WHERE quiz_id = ?", (quiz_id,))
        row = cur.fetchone()
    return _row_to_quiz(row) if row else None


def save_evaluation(quiz_id: str, evaluation: dict[str, Any]) -> None:
    with _write_lock, _cursor() as cur:
        cur.execute(
            """
            INSERT OR REPLACE INTO evaluations
                (quiz_id, topic, score, correct_indexes, incorrect_indexes,
                 selected_options, improvement_tips, links, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                quiz_id,
                evaluation["topic"],
                float(evaluation["score"]),
                json.dumps(evaluation["correct_answers_index"]),
                json.dumps(evaluation["incorrect_answers_index"]),
                json.dumps(evaluation.get("selected_options") or []),
                evaluation["improvement_tips"],
                json.dumps(evaluation.get("links") or []),
                _now(),
            ),
        )


def get_evaluation(quiz_id: str) -> dict[str, Any] | None:
    with _write_lock, _cursor() as cur:
        cur.execute("SELECT * FROM evaluations WHERE quiz_id = ?", (quiz_id,))
        row = cur.fetchone()
    return _row_to_evaluation(row) if row else None


def count_quizzes() -> int:
    with _write_lock, _cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM quizzes")
        row = cur.fetchone()
    return int(row["total"]) if row else 0
