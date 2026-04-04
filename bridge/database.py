import sqlite3
import json
import logging
from datetime import datetime, timezone
from config import DB_PATH

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS calls (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id          TEXT    NOT NULL UNIQUE,
                caller_number    TEXT,
                started_at       DATETIME NOT NULL,
                ended_at         DATETIME,
                duration_seconds INTEGER,
                transcript       TEXT,    -- JSON array of {role, text} objects
                summary          TEXT     -- GPT-generated one-line summary
            );

            CREATE TABLE IF NOT EXISTS turns (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id     TEXT    NOT NULL REFERENCES calls(call_id),
                turn_index  INTEGER NOT NULL,
                role        TEXT    NOT NULL CHECK(role IN ('caller','assistant')),
                text        TEXT    NOT NULL,
                created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_calls_started ON calls(started_at);
            CREATE INDEX IF NOT EXISTS idx_turns_call    ON turns(call_id);
        """)
    logger.info("Database initialised at %s", DB_PATH)


def start_call(call_id: str, caller_number: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO calls (call_id, caller_number, started_at) VALUES (?, ?, ?)",
            (call_id, caller_number, datetime.now(timezone.utc).isoformat()),
        )


def add_turn(call_id: str, turn_index: int, role: str, text: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO turns (call_id, turn_index, role, text) VALUES (?, ?, ?, ?)",
            (call_id, turn_index, role, text),
        )


def end_call(call_id: str, transcript: list[dict], summary: str) -> None:
    ended_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        row = conn.execute(
            "SELECT started_at FROM calls WHERE call_id = ?", (call_id,)
        ).fetchone()

        duration = None
        if row:
            started = datetime.fromisoformat(row["started_at"])
            ended   = datetime.fromisoformat(ended_at)
            duration = int((ended - started).total_seconds())

        conn.execute(
            """
            UPDATE calls
               SET ended_at         = ?,
                   duration_seconds = ?,
                   transcript       = ?,
                   summary          = ?
             WHERE call_id = ?
            """,
            (ended_at, duration, json.dumps(transcript), summary, call_id),
        )
    logger.info("Call %s ended — %ss, %d turns", call_id, duration, len(transcript))
