"""
mentor_db.py — PostgreSQL (Supabase) persistence for Mentor conversations.
"""

import psycopg2
import psycopg2.extras
import json
import os
import logging
from datetime import datetime

log = logging.getLogger(__name__)


# ── Secret Resolution (works locally AND on Streamlit Cloud) ──────────────────

def _get_secret(key: str, default: str = None) -> str:
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val:
            return str(val)
    except Exception:
        pass
    return os.environ.get(key, default)


# ── Connection ─────────────────────────────────────────────────────────────────

def _conn() -> psycopg2.extensions.connection:
    host = _get_secret("DB_HOST")
    if not host:
        raise RuntimeError(
            "DB_HOST is not set. Add it to Streamlit Cloud secrets or your .env file."
        )
    return psycopg2.connect(
        host=host,
        port=_get_secret("DB_PORT", "5432"),
        database=_get_secret("DB_NAME"),
        user=_get_secret("DB_USER"),
        password=_get_secret("DB_PASSWORD"),
        sslmode="require",
        connect_timeout=10,
    )


# ── Schema ─────────────────────────────────────────────────────────────────────

_db_initialized = False


def init_mentor_db() -> None:
    global _db_initialized
    if _db_initialized:
        return
    try:
        with _conn() as c:
            cur = c.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS mentor_sessions (
                id          SERIAL PRIMARY KEY,
                session_id  TEXT    NOT NULL UNIQUE,
                blueprint_id INTEGER,
                user_email  TEXT,
                sector      TEXT,
                stage       TEXT,
                created_at  TEXT    NOT NULL,
                last_active TEXT    NOT NULL
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS mentor_messages (
                id          SERIAL PRIMARY KEY,
                session_id  TEXT    NOT NULL REFERENCES mentor_sessions(session_id) ON DELETE CASCADE,
                role        TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                intent      TEXT,
                citations   TEXT,
                tools_used  TEXT,
                timestamp   TEXT    NOT NULL
            );
            """)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS mentor_blueprint_chat (
                id SERIAL PRIMARY KEY,
                blueprint_id INTEGER NOT NULL,
                user_email TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                intent TEXT DEFAULT '',
                citations JSONB DEFAULT '[]',
                tools_used JSONB DEFAULT '[]',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """)
            c.commit()
        _db_initialized = True
        log.info("[MENTOR] Database initialized successfully")
    except Exception as e:
        log.warning(f"[MENTOR] DB init failed (non-fatal): {e}")
        _db_initialized = True  # Prevent retry loops


# ── Write ──────────────────────────────────────────────────────────────────────

def save_mentor_session(*, session_id, blueprint_id, user_email, sector, stage) -> None:
    init_mentor_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            INSERT INTO mentor_sessions
                (session_id, blueprint_id, user_email, sector, stage, created_at, last_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE SET last_active = EXCLUDED.last_active
        """, (session_id, blueprint_id, user_email, sector, stage, now, now))
        c.commit()


def save_mentor_message(*, session_id, role, content, intent="",
                        citations=None, tools_used=None) -> None:
    init_mentor_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Normalize citations: if they are dicts (after Pydantic normalization), serialize them
    # If they are strings, serialize as-is
    citations_json = json.dumps(citations or [])
    tools_json = json.dumps(tools_used or [])
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            INSERT INTO mentor_messages
                (session_id, role, content, intent, citations, tools_used, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            session_id, role, content, intent,
            citations_json,
            tools_json,
            now,
        ))
        cur.execute(
            "UPDATE mentor_sessions SET last_active=%s WHERE session_id=%s",
            (now, session_id)
        )
        c.commit()


# ── Read ───────────────────────────────────────────────────────────────────────

def get_mentor_messages(session_id: str) -> list[dict]:
    init_mentor_db()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT role, content, intent, citations, tools_used, timestamp
            FROM mentor_messages
            WHERE session_id = %s
            ORDER BY id ASC
        """, (session_id,))
        result = []
        for r in cur.fetchall():
            result.append({
                "role":       r["role"],
                "content":    r["content"],
                "intent":     r["intent"] or "",
                "citations":  json.loads(r["citations"] or "[]"),
                "tools_used": json.loads(r["tools_used"] or "[]"),
                "timestamp":  r["timestamp"],
            })
        return result


def get_sessions_for_blueprint(blueprint_id: int) -> list[dict]:
    """List all sessions for a given blueprint_id."""
    init_mentor_db()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT * FROM mentor_sessions
            WHERE blueprint_id = %s
            ORDER BY last_active DESC
        """, (blueprint_id,))
        return [dict(r) for r in cur.fetchall()]


def get_sessions_for_user(user_email: str) -> list[dict]:
    init_mentor_db()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT * FROM mentor_sessions
            WHERE user_email = %s
            ORDER BY last_active DESC
        """, (user_email,))
        return [dict(r) for r in cur.fetchall()]


def delete_session(session_id: str, user_email: str = "") -> None:
    """
    Delete a mentor session and all its messages (CASCADE).
    If user_email is provided, only deletes if owned by that user.
    """
    init_mentor_db()
    with _conn() as c:
        cur = c.cursor()
        if user_email:
            cur.execute(
                "DELETE FROM mentor_sessions WHERE session_id = %s AND user_email = %s",
                (session_id, user_email)
            )
        else:
            cur.execute(
                "DELETE FROM mentor_sessions WHERE session_id = %s",
                (session_id,)
            )
        c.commit()


# ── Blueprint-level chat (alternative persistence) ─────────────────────────────

def save_bp_message(blueprint_id: int, user_email: str, role: str, content: str,
                    intent: str = "", citations: list = None, tools_used: list = None):
    """Save a single chat message linked to a blueprint_id."""
    if citations is None:
        citations = []
    if tools_used is None:
        tools_used = []
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO mentor_blueprint_chat
                (blueprint_id, user_email, role, content, intent, citations, tools_used)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (blueprint_id, user_email, role, content, intent,
              json.dumps(citations), json.dumps(tools_used)))
        conn.commit()


def load_bp_messages(blueprint_id: int, user_email: str) -> list:
    """Load all chat messages for a given blueprint."""
    with _conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT role, content, intent, citations, tools_used
            FROM mentor_blueprint_chat
            WHERE blueprint_id = %s AND user_email = %s
            ORDER BY created_at ASC
        """, (blueprint_id, user_email))
        rows = cur.fetchall()
        return [
            {
                "role": r[0], "content": r[1], "intent": r[2],
                "citations": json.loads(r[3] if r[3] else "[]"),
                "tools_used": json.loads(r[4] if r[4] else "[]"),
            }
            for r in rows
        ]


# ── Init on import ─────────────────────────────────────────────────────────────
try:
    init_mentor_db()
except Exception as _init_err:
    log.warning(f"[MENTOR] DB init on import failed (non-fatal): {_init_err}")
