"""
SQLite database layer for tracking sent emails.
Zero-config, file-based — swap for Postgres when you need to scale.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "emails.db")


def _get_conn() -> sqlite3.Connection:
    """Get a connection with row_factory set for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the sent_emails table if it doesn't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_emails (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL,
                session_id  TEXT NOT NULL,
                to_email    TEXT NOT NULL,
                subject     TEXT NOT NULL,
                body        TEXT NOT NULL,
                status      TEXT NOT NULL,
                error_message TEXT,
                sent_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sent_emails_user
            ON sent_emails(user_id)
        """)
        conn.commit()


def log_email(
    user_id: str,
    session_id: str,
    to_email: str,
    subject: str,
    body: str,
    status: str,
    error_message: str | None = None,
):
    """Insert a sent-email record."""
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO sent_emails
                (user_id, session_id, to_email, subject, body, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, session_id, to_email, subject, body, status, error_message),
        )
        conn.commit()


def get_emails(user_id: str) -> list[dict]:
    """Fetch all emails for a user, newest first."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sent_emails WHERE user_id = ? ORDER BY sent_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]
