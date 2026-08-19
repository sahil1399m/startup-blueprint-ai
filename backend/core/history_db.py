"""
history_db.py — PostgreSQL (Supabase) persistence for Blueprint History.

Schema
------
blueprints         — one row per blueprint (metadata)
blueprint_sections — named JSON content sections per blueprint
blueprint_sources  — source links per blueprint
"""

import psycopg2
import psycopg2.extras
import json
import os
from datetime import datetime

# ── Secret Resolution (works locally AND on Streamlit Cloud) ──────────────────

def _get_secret(key: str, default: str = None) -> str:
    """
    Priority:
    1. os.environ  (set by Streamlit Cloud from TOML secrets, or local .env loaded externally)
    2. st.secrets  (fallback direct read, only if streamlit is available)
    3. default
    """
    val = os.environ.get(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default


# ── Connection ────────────────────────────────────────────────────────────────

def _conn() -> psycopg2.extensions.connection:
    host = _get_secret("DB_HOST")
    port = _get_secret("DB_PORT", "5432")
    database = _get_secret("DB_NAME")
    user = _get_secret("DB_USER")
    password = _get_secret("DB_PASSWORD")

    if not host:
        raise RuntimeError(
            "DB_HOST is not set. Add it to Streamlit Cloud secrets or your .env file."
        )

    return psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        sslmode="require",
        connect_timeout=10,
    )


# ── Schema ────────────────────────────────────────────────────────────────────

_db_initialized = False  # module-level flag — init only once per process


def init_db() -> None:
    """
    Creates tables if they don't exist.
    Safe to call multiple times — runs only once per process due to the flag.
    Call this explicitly at app startup, NOT at import time.
    """
    global _db_initialized
    if _db_initialized:
        return
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS blueprints (
            id              SERIAL PRIMARY KEY,
            title           TEXT    NOT NULL,
            original_query  TEXT    NOT NULL,
            rewritten_query TEXT,
            sector          TEXT,
            stage           TEXT,
            business_model  TEXT,
            market          TEXT,
            confidence      TEXT,
            is_favorite     INTEGER DEFAULT 0,
            user_email      TEXT,
            timestamp       TEXT    NOT NULL
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS blueprint_sections (
            id           SERIAL PRIMARY KEY,
            blueprint_id INTEGER NOT NULL REFERENCES blueprints(id) ON DELETE CASCADE,
            section_name TEXT    NOT NULL,
            content      TEXT    NOT NULL
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS blueprint_sources (
            id           SERIAL PRIMARY KEY,
            blueprint_id INTEGER NOT NULL REFERENCES blueprints(id) ON DELETE CASCADE,
            source_name  TEXT,
            source_url   TEXT
        );
        """)
        c.commit()
    _db_initialized = True


# ── Write ─────────────────────────────────────────────────────────────────────

def save_blueprint(*, title, original_query, rewritten_query, sector, stage,
                   business_model, market, confidence, user_email,
                   sections: dict, sources: list) -> int:
    init_db()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as c:
        cur = c.cursor()
        cur.execute(
            """INSERT INTO blueprints
               (title,original_query,rewritten_query,sector,stage,
                business_model,market,confidence,user_email,timestamp)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               RETURNING id""",
            (title, original_query, rewritten_query, sector, stage,
             business_model, market, confidence, user_email, ts),
        )
        bp_id = cur.fetchone()[0]
        for name, content in sections.items():
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False)
            cur.execute(
                "INSERT INTO blueprint_sections (blueprint_id,section_name,content) VALUES (%s,%s,%s)",
                (bp_id, name, content),
            )
        for src in sources:
            cur.execute(
                "INSERT INTO blueprint_sources (blueprint_id,source_name,source_url) VALUES (%s,%s,%s)",
                (bp_id, src.get("name", ""), src.get("url", "")),
            )
        c.commit()
    return bp_id


# ── Read ──────────────────────────────────────────────────────────────────────

def list_blueprints(user_email=None) -> list:
    init_db()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if user_email:
            cur.execute(
                "SELECT * FROM blueprints WHERE user_email=%s ORDER BY id DESC",
                (user_email,),
            )
        else:
            cur.execute("SELECT * FROM blueprints ORDER BY id DESC")
        return [dict(r) for r in cur.fetchall()]


def get_blueprint(blueprint_id: int) -> dict | None:
    init_db()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM blueprints WHERE id=%s", (blueprint_id,))
        row = cur.fetchone()
        if row is None:
            return None
        bp = dict(row)
        cur.execute(
            "SELECT section_name,content FROM blueprint_sections WHERE blueprint_id=%s",
            (blueprint_id,),
        )
        bp["sections"] = {}
        for sr in cur.fetchall():
            content = sr["content"]
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                pass
            bp["sections"][sr["section_name"]] = content
        cur.execute(
            "SELECT source_name,source_url FROM blueprint_sources WHERE blueprint_id=%s",
            (blueprint_id,),
        )
        bp["sources"] = [{"name": r["source_name"], "url": r["source_url"]} for r in cur.fetchall()]
    return bp


def search_blueprints(query: str, user_email=None) -> list:
    init_db()
    like = f"%{query}%"
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if user_email:
            cur.execute(
                """SELECT * FROM blueprints
                   WHERE user_email=%s AND (title ILIKE %s OR original_query ILIKE %s)
                   ORDER BY id DESC""",
                (user_email, like, like),
            )
        else:
            cur.execute(
                "SELECT * FROM blueprints WHERE title ILIKE %s OR original_query ILIKE %s ORDER BY id DESC",
                (like, like),
            )
        return [dict(r) for r in cur.fetchall()]


# ── Delete ────────────────────────────────────────────────────────────────────

def delete_blueprint(blueprint_id: int, user_email: str = None) -> bool:
    """Delete a blueprint. If user_email is provided, only delete if owned by that user."""
    init_db()
    with _conn() as c:
        cur = c.cursor()
        if user_email:
            cur.execute(
                "DELETE FROM blueprints WHERE id=%s AND user_email=%s RETURNING id",
                (blueprint_id, user_email),
            )
        else:
            cur.execute(
                "DELETE FROM blueprints WHERE id=%s RETURNING id",
                (blueprint_id,),
            )
        deleted = cur.fetchone() is not None
        c.commit()
    return deleted


def delete_all_blueprints(user_email=None) -> None:
    init_db()
    with _conn() as c:
        cur = c.cursor()
        if user_email:
            cur.execute("DELETE FROM blueprints WHERE user_email=%s", (user_email,))
        else:
            cur.execute("DELETE FROM blueprints")
        c.commit()


# Alias used by routes/history.py
delete_all_blueprints_for_user = delete_all_blueprints


# ── Favourite ─────────────────────────────────────────────────────────────────

def toggle_favorite(blueprint_id: int) -> bool:
    init_db()
    with _conn() as c:
        cur = c.cursor()
        cur.execute("SELECT is_favorite FROM blueprints WHERE id=%s", (blueprint_id,))
        row = cur.fetchone()
        if row is None:
            return False
        new_val = 0 if row[0] else 1
        cur.execute("UPDATE blueprints SET is_favorite=%s WHERE id=%s", (new_val, blueprint_id))
        c.commit()
    return bool(new_val)


# ── Count ─────────────────────────────────────────────────────────────────────

def get_blueprint_count_for_user(user_id: str) -> int:
    """Return the number of blueprints for a given user (by email or ID)."""
    try:
        init_db()
        with _conn() as c:
            cur = c.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM blueprints WHERE user_email=%s",
                (user_id,),
            )
            return cur.fetchone()[0]
    except Exception:
        return 0

# ── NO init_db() call here — lazy init per function instead ──────────────────
