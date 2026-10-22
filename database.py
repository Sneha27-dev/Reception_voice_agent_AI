"""
database.py
-----------
All SQLite logic lives here so the rest of the app never writes raw SQL.
Two required tools are implemented as plain functions:

    save_call(record)   -> stores one CallRecord, returns the saved record
    list_calls()         -> returns all stored CallRecord objects

Plus an optional third tool:

    search_calls(...)    -> filter by name / intent / callback number / date
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional

from models import CallRecord

DB_PATH = Path(__file__).parent / "data" / "calls.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    caller_name     TEXT NOT NULL,
    intent          TEXT NOT NULL,
    callback_number TEXT NOT NULL,
    transcript      TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


class DatabaseError(Exception):
    """Raised for any problem talking to SQLite, so callers only need to
    catch one exception type instead of sqlite3's various subclasses."""


@contextmanager
def _get_connection():
    """Yields a SQLite connection, always making sure the data/ folder
    exists and the connection is closed afterwards."""
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise DatabaseError(f"Could not connect to database: {exc}") from exc


def init_db() -> None:
    """Creates the calls table if it does not already exist. Safe to call
    every time the app starts."""
    try:
        with _get_connection() as conn:
            conn.execute(SCHEMA)
            conn.commit()
    except sqlite3.Error as exc:
        raise DatabaseError(f"Could not initialize database: {exc}") from exc


def save_call(record: CallRecord) -> CallRecord:
    """Stores a new call record. Never overwrites existing rows - every
    processed call becomes its own row, even for a repeat caller."""
    if not record.transcript or not record.transcript.strip():
        raise DatabaseError("Refusing to save a call with an empty transcript.")

    try:
        with _get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO calls (caller_name, intent, callback_number, transcript)
                VALUES (?, ?, ?, ?)
                """,
                (record.caller_name, record.intent, record.callback_number, record.transcript),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM calls WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            return _row_to_record(row)
    except sqlite3.Error as exc:
        raise DatabaseError(f"Failed to save call record: {exc}") from exc


def list_calls() -> List[CallRecord]:
    """Returns every stored call, most recent first."""
    try:
        with _get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM calls ORDER BY id DESC"
            ).fetchall()
            return [_row_to_record(r) for r in rows]
    except sqlite3.Error as exc:
        raise DatabaseError(f"Failed to list calls: {exc}") from exc


def search_calls(
    caller_name: Optional[str] = None,
    intent: Optional[str] = None,
    callback_number: Optional[str] = None,
    date: Optional[str] = None,
) -> List[CallRecord]:
    """Optional third tool. Any combination of filters can be supplied;
    text filters use partial (LIKE) matching, date matches the
    YYYY-MM-DD prefix of created_at."""
    clauses = []
    params: list = []

    if caller_name:
        clauses.append("caller_name LIKE ?")
        params.append(f"%{caller_name}%")
    if intent:
        clauses.append("intent LIKE ?")
        params.append(f"%{intent}%")
    if callback_number:
        clauses.append("callback_number LIKE ?")
        params.append(f"%{callback_number}%")
    if date:
        clauses.append("substr(created_at, 1, 10) = ?")
        params.append(date)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    try:
        with _get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM calls {where_sql} ORDER BY id DESC", params
            ).fetchall()
            return [_row_to_record(r) for r in rows]
    except sqlite3.Error as exc:
        raise DatabaseError(f"Failed to search calls: {exc}") from exc


def _row_to_record(row: sqlite3.Row) -> CallRecord:
    return CallRecord(
        id=row["id"],
        caller_name=row["caller_name"],
        intent=row["intent"],
        callback_number=row["callback_number"],
        transcript=row["transcript"],
        created_at=row["created_at"],
    )
