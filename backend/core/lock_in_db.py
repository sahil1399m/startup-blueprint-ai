"""
lock_in_db.py — PostgreSQL persistence for LOCK IN feature & AI Accountability Agent.
Matches history_db.py pattern exactly (psycopg2, same _conn()).
"""

import psycopg2
import psycopg2.extras
import json
import os
import logging
from datetime import datetime, date, timedelta, timezone
import zoneinfo
from typing import Optional, Dict, Any, List

log = logging.getLogger(__name__)


from contextlib import contextmanager

def _get_secret(key: str, default: str = None) -> str:
    val = os.environ.get(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default


@contextmanager
def _conn():
    conn = psycopg2.connect(
        host=_get_secret("DB_HOST"),
        port=_get_secret("DB_PORT", "5432"),
        database=_get_secret("DB_NAME"),
        user=_get_secret("DB_USER"),
        password=_get_secret("DB_PASSWORD"),
        sslmode="require",
        connect_timeout=10,
    )
    try:
        with conn:
            yield conn
    finally:
        conn.close()


_initialized = False

def init_tables() -> None:
    global _initialized
    if _initialized:
        return
    with _conn() as c:
        cur = c.cursor()

        # Legacy Phase 1 tables (kept intact for backwards compatibility)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS lock_in_profiles (
            id              SERIAL PRIMARY KEY,
            blueprint_id    INTEGER,
            user_email      TEXT,
            founder_data    JSONB,
            created_at      TIMESTAMPTZ DEFAULT now()
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS lock_in_roadmaps (
            id                  SERIAL PRIMARY KEY,
            profile_id          INTEGER REFERENCES lock_in_profiles(id) ON DELETE CASCADE,
            blueprint_id        INTEGER,
            user_email          TEXT,
            market_research     JSONB,
            competitor_intel    JSONB,
            roadmap             JSONB,
            created_at          TIMESTAMPTZ DEFAULT now()
        );
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS lock_in_tasks (
            id          SERIAL PRIMARY KEY,
            roadmap_id  INTEGER REFERENCES lock_in_roadmaps(id) ON DELETE CASCADE,
            task_id     TEXT,
            status      TEXT DEFAULT 'pending',
            notes       TEXT DEFAULT '',
            updated_at  TIMESTAMPTZ DEFAULT now()
        );
        """)

        # ── PHASE 2 TABLES ───────────────────────────────────────────────────

        # 1. Projects table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS lockin_projects (
            id              SERIAL PRIMARY KEY,
            user_id         TEXT NOT NULL,
            user_email      TEXT NOT NULL,
            blueprint_id    INTEGER NOT NULL,
            roadmap_data    JSONB NOT NULL,
            start_date      DATE DEFAULT CURRENT_DATE,
            target_date     DATE,
            status          TEXT DEFAULT 'active',
            created_at      TIMESTAMPTZ DEFAULT now(),
            updated_at      TIMESTAMPTZ DEFAULT now(),
            UNIQUE(user_id, blueprint_id)
        );
        """)

        # 2. Normalized Tasks table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS lockin_tasks (
            id              SERIAL PRIMARY KEY,
            project_id      INTEGER REFERENCES lockin_projects(id) ON DELETE CASCADE,
            task_id         TEXT NOT NULL,
            week_number     INTEGER DEFAULT 1,
            title           TEXT NOT NULL,
            description     TEXT DEFAULT '',
            category        TEXT DEFAULT 'ops',
            priority        TEXT DEFAULT 'should',
            hours           INTEGER DEFAULT 2,
            status          TEXT DEFAULT 'pending',
            deadline        DATE,
            completed_at    TIMESTAMPTZ,
            updated_at      TIMESTAMPTZ DEFAULT now(),
            UNIQUE(project_id, task_id)
        );
        """)

        # 3. Preferences table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS lockin_preferences (
            id                      SERIAL PRIMARY KEY,
            project_id              INTEGER REFERENCES lockin_projects(id) ON DELETE CASCADE UNIQUE,
            user_id                 TEXT NOT NULL,
            email_enabled           BOOLEAN DEFAULT TRUE,
            daily_reminder_enabled  BOOLEAN DEFAULT TRUE,
            deadline_alert_enabled  BOOLEAN DEFAULT TRUE,
            weekly_report_enabled   BOOLEAN DEFAULT TRUE,
            recovery_enabled        BOOLEAN DEFAULT TRUE,
            reminder_time           TEXT DEFAULT '09:00',
            timezone                TEXT DEFAULT 'Asia/Kolkata',
            updated_at              TIMESTAMPTZ DEFAULT now()
        );
        """)

        # 4. Gmail OAuth Connections table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS gmail_connections (
            id              SERIAL PRIMARY KEY,
            user_id         TEXT NOT NULL UNIQUE,
            user_email      TEXT NOT NULL,
            google_email    TEXT NOT NULL,
            access_token    TEXT NOT NULL,
            refresh_token   TEXT,
            token_expiry    TIMESTAMPTZ,
            status          TEXT DEFAULT 'active',
            created_at      TIMESTAMPTZ DEFAULT now(),
            updated_at      TIMESTAMPTZ DEFAULT now()
        );
        """)

        # 5. Notifications history & idempotency tracking
        cur.execute("""
        CREATE TABLE IF NOT EXISTS lockin_notifications (
            id                  SERIAL PRIMARY KEY,
            project_id          INTEGER REFERENCES lockin_projects(id) ON DELETE CASCADE,
            user_id             TEXT NOT NULL,
            notification_type   TEXT NOT NULL,
            task_id             TEXT DEFAULT '',
            subject             TEXT NOT NULL,
            status              TEXT DEFAULT 'sent',
            provider_message_id TEXT DEFAULT '',
            local_date          DATE,
            sent_at             TIMESTAMPTZ DEFAULT now(),
            error               TEXT DEFAULT ''
        );
        """)

        # Migration: ensure local_date column exists if table was previously created
        cur.execute("""
        ALTER TABLE lockin_notifications ADD COLUMN IF NOT EXISTS local_date DATE;
        """)

        # 6. HITL Agent Actions & Recommendations
        cur.execute("""
        CREATE TABLE IF NOT EXISTS lockin_agent_actions (
            id                  SERIAL PRIMARY KEY,
            project_id          INTEGER REFERENCES lockin_projects(id) ON DELETE CASCADE,
            user_id             TEXT NOT NULL,
            action_type         TEXT NOT NULL,
            title               TEXT NOT NULL,
            description         TEXT NOT NULL,
            details             JSONB DEFAULT '{}'::jsonb,
            status              TEXT DEFAULT 'pending',
            requires_approval   BOOLEAN DEFAULT FALSE,
            created_at          TIMESTAMPTZ DEFAULT now(),
            approved_at         TIMESTAMPTZ,
            executed_at         TIMESTAMPTZ,
            rejected_at         TIMESTAMPTZ
        );
        """)

        c.commit()
    _initialized = True


# ══════════════════════════════════════════════════════════════════════════════
# PROJECT & TASK SYNCHRONIZATION
# ══════════════════════════════════════════════════════════════════════════════

def sync_project(user_id: str, user_email: str, blueprint_id: int, roadmap_data: dict, completed_task_ids: list[str]) -> dict:
    """
    Syncs roadmap and task completion state from frontend to backend.
    Ensures the backend agent has the complete roadmap and live completion states.
    """
    init_tables()
    roadmap_json = json.dumps(roadmap_data)
    completed_set = set(completed_task_ids or [])

    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 1. Upsert project
        cur.execute("""
            INSERT INTO lockin_projects (user_id, user_email, blueprint_id, roadmap_data, updated_at)
            VALUES (%s, %s, %s, %s, now())
            ON CONFLICT (user_id, blueprint_id)
            DO UPDATE SET roadmap_data = EXCLUDED.roadmap_data, updated_at = now()
            RETURNING id, user_id, user_email, blueprint_id, start_date, target_date, status, created_at, updated_at;
        """, (user_id, user_email, blueprint_id, roadmap_json))
        project = dict(cur.fetchone())
        project_id = project["id"]

        # 2. Sync individual tasks from roadmap weeks in a single batch
        weeks = roadmap_data.get("weeks", [])
        task_tuples = []
        for w in weeks:
            week_num = w.get("week", 1)
            for t in w.get("tasks", []):
                t_id = str(t.get("id", ""))
                if not t_id:
                    continue
                t_title = t.get("task", "") or t.get("title", "")
                t_desc = t.get("details", "") or t.get("description", "")
                t_cat = t.get("category", "ops")
                t_pri = t.get("priority", "should")
                t_hrs = int(t.get("hours", 2) or 2)
                
                is_completed = t_id in completed_set
                status = "completed" if is_completed else "pending"
                task_tuples.append((
                    project_id, t_id, week_num, t_title, t_desc, t_cat, t_pri, t_hrs, status, is_completed
                ))

        if task_tuples:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO lockin_tasks (project_id, task_id, week_number, title, description, category, priority, hours, status, completed_at, updated_at)
                VALUES %s
                ON CONFLICT (project_id, task_id)
                DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    category = EXCLUDED.category,
                    priority = EXCLUDED.priority,
                    hours = EXCLUDED.hours,
                    status = EXCLUDED.status,
                    completed_at = CASE WHEN EXCLUDED.status = 'completed' AND lockin_tasks.completed_at IS NULL THEN now()
                                        WHEN EXCLUDED.status = 'pending' THEN NULL
                                        ELSE lockin_tasks.completed_at END,
                    updated_at = now();
                """,
                task_tuples,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, CASE WHEN %s THEN now() ELSE NULL END, now())"
            )

        # 3. Ensure default preferences exist
        cur.execute("""
            INSERT INTO lockin_preferences (project_id, user_id)
            VALUES (%s, %s)
            ON CONFLICT (project_id) DO NOTHING;
        """, (project_id, user_id))

        c.commit()

    return project


def get_project(user_id: str, blueprint_id: int) -> dict | None:
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT * FROM lockin_projects 
            WHERE user_id = %s AND blueprint_id = %s;
        """, (user_id, blueprint_id))
        row = cur.fetchone()
        if not row:
            return None
        res = dict(row)
        if isinstance(res.get("roadmap_data"), str):
            res["roadmap_data"] = json.loads(res["roadmap_data"])
        return res


def get_project_by_id(project_id: int) -> dict | None:
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM lockin_projects WHERE id = %s;", (project_id,))
        row = cur.fetchone()
        if not row:
            return None
        res = dict(row)
        if isinstance(res.get("roadmap_data"), str):
            res["roadmap_data"] = json.loads(res["roadmap_data"])
        return res


def get_project_tasks(project_id: int) -> list[dict]:
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT * FROM lockin_tasks 
            WHERE project_id = %s 
            ORDER BY week_number ASC, id ASC;
        """, (project_id,))
        return [dict(r) for r in cur.fetchall()]


# ══════════════════════════════════════════════════════════════════════════════
# PREFERENCES
# ══════════════════════════════════════════════════════════════════════════════

def get_preferences(project_id: int, user_id: str = None) -> dict:
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if user_id:
            cur.execute("""
                SELECT * FROM lockin_preferences 
                WHERE project_id = %s AND user_id = %s;
            """, (project_id, user_id))
        else:
            cur.execute("SELECT * FROM lockin_preferences WHERE project_id = %s;", (project_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
        
        # Default preferences if not found
        return {
            "project_id": project_id,
            "email_enabled": True,
            "daily_reminder_enabled": True,
            "deadline_alert_enabled": True,
            "weekly_report_enabled": True,
            "recovery_enabled": True,
            "reminder_time": "09:00",
            "timezone": "Asia/Kolkata"
        }


def update_preferences(project_id: int, user_id: str, prefs: dict) -> dict:
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            INSERT INTO lockin_preferences (
                project_id, user_id, email_enabled, daily_reminder_enabled,
                deadline_alert_enabled, weekly_report_enabled, recovery_enabled,
                reminder_time, timezone, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
            )
            ON CONFLICT (project_id)
            DO UPDATE SET
                email_enabled = EXCLUDED.email_enabled,
                daily_reminder_enabled = EXCLUDED.daily_reminder_enabled,
                deadline_alert_enabled = EXCLUDED.deadline_alert_enabled,
                weekly_report_enabled = EXCLUDED.weekly_report_enabled,
                recovery_enabled = EXCLUDED.recovery_enabled,
                reminder_time = EXCLUDED.reminder_time,
                timezone = EXCLUDED.timezone,
                updated_at = now()
            RETURNING *;
        """, (
            project_id, user_id,
            prefs.get("email_enabled", True),
            prefs.get("daily_reminder_enabled", True),
            prefs.get("deadline_alert_enabled", True),
            prefs.get("weekly_report_enabled", True),
            prefs.get("recovery_enabled", True),
            prefs.get("reminder_time", "09:00"),
            prefs.get("timezone", "Asia/Kolkata")
        ))
        row = cur.fetchone()
        c.commit()
        return dict(row)


# ══════════════════════════════════════════════════════════════════════════════
# GMAIL OAUTH CONNECTIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_gmail_connection(user_id: str) -> dict | None:
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, user_id, user_email, google_email, access_token, refresh_token, token_expiry, status, created_at, updated_at
            FROM gmail_connections
            WHERE user_id = %s;
        """, (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def save_gmail_connection(user_id: str, user_email: str, google_email: str, access_token: str, refresh_token: str, token_expiry, status: str = "active") -> dict:
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            INSERT INTO gmail_connections (user_id, user_email, google_email, access_token, refresh_token, token_expiry, status, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (user_id)
            DO UPDATE SET
                user_email = EXCLUDED.user_email,
                google_email = EXCLUDED.google_email,
                access_token = EXCLUDED.access_token,
                refresh_token = COALESCE(EXCLUDED.refresh_token, gmail_connections.refresh_token),
                token_expiry = EXCLUDED.token_expiry,
                status = EXCLUDED.status,
                updated_at = now()
            RETURNING *;
        """, (user_id, user_email, google_email, access_token, refresh_token, token_expiry, status))
        row = cur.fetchone()
        c.commit()
        return dict(row)


def update_gmail_access_token(user_id: str, access_token: str, token_expiry) -> None:
    init_tables()
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            UPDATE gmail_connections 
            SET access_token = %s, token_expiry = %s, status = 'active', updated_at = now()
            WHERE user_id = %s;
        """, (access_token, token_expiry, user_id))
        c.commit()


def mark_gmail_connection_revoked(user_id: str, status: str = "revoked") -> None:
    init_tables()
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            UPDATE gmail_connections 
            SET status = %s, updated_at = now()
            WHERE user_id = %s;
        """, (status, user_id))
        c.commit()


def disconnect_gmail(user_id: str) -> bool:
    init_tables()
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            UPDATE gmail_connections 
            SET status = 'disconnected', updated_at = now()
            WHERE user_id = %s;
        """, (user_id,))
        c.commit()
    return True


# ══════════════════════════════════════════════════════════════════════════════
# DETERMINISTIC MOMENTUM & STREAK SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

def calculate_momentum_and_streak(project_id: int, user_tz_str: str = "Asia/Kolkata") -> Dict[str, Any]:
    """
    Deterministically computes user execution streak, active days, and momentum classification
    strictly from database records without any LLM hallucination.

    Streak Rules:
      1. A day is active if the user completed >= 1 roadmap task on that local calendar day.
      2. Duplicate task completions on the same date count as 1 active day (no streak inflation).
      3. Current streak counts consecutive local days. If today has 0 tasks completed yet,
         the streak from yesterday is preserved until the local day ends.
      4. Longest streak is the maximum consecutive active day sequence in project history.
    """
    init_tables()
    try:
        user_tz = zoneinfo.ZoneInfo(user_tz_str)
    except Exception:
        user_tz = zoneinfo.ZoneInfo("UTC")

    local_now = datetime.now(user_tz)
    today_local = local_now.date()
    yesterday_local = today_local - timedelta(days=1)
    start_of_this_week = today_local - timedelta(days=today_local.weekday()) # Monday
    start_of_last_week = start_of_this_week - timedelta(days=7)

    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Load all tasks
        cur.execute("""
            SELECT id, task_id, week_number, title, status, completed_at, updated_at
            FROM lockin_tasks
            WHERE project_id = %s;
        """, (project_id,))
        tasks = [dict(r) for r in cur.fetchall()]

    total_tasks = len(tasks)
    completed_tasks = [t for t in tasks if t.get("status") == "completed"]

    # Map completed tasks to local dates
    tasks_by_date: Dict[date, List[dict]] = {}
    for t in completed_tasks:
        comp_at = t.get("completed_at") or t.get("updated_at")
        if not comp_at:
            continue
        if isinstance(comp_at, datetime):
            # Ensure timezone conversion
            if comp_at.tzinfo is None:
                comp_at = comp_at.replace(tzinfo=timezone.utc)
            task_local_date = comp_at.astimezone(user_tz).date()
        elif isinstance(comp_at, date):
            task_local_date = comp_at
        else:
            try:
                task_local_date = date.fromisoformat(str(comp_at)[:10])
            except Exception:
                continue

        tasks_by_date.setdefault(task_local_date, []).append(t)

    active_dates = sorted(tasks_by_date.keys())
    active_date_set = set(active_dates)
    active_days = len(active_dates)

    # 1. Tasks completed today & this week
    tasks_completed_today = len(tasks_by_date.get(today_local, []))
    tasks_completed_this_week = sum(
        len(tasks_by_date.get(d, []))
        for d in active_dates
        if start_of_this_week <= d <= today_local
    )
    tasks_completed_last_week = sum(
        len(tasks_by_date.get(d, []))
        for d in active_dates
        if start_of_last_week <= d < start_of_this_week
    )

    # 2. Current Streak (preserves yesterday's streak if today is not completed yet)
    if today_local in active_date_set:
        streak = 0
        check_day = today_local
        while check_day in active_date_set:
            streak += 1
            check_day = check_day - timedelta(days=1)
        current_streak = streak
    elif yesterday_local in active_date_set:
        streak = 0
        check_day = yesterday_local
        while check_day in active_date_set:
            streak += 1
            check_day = check_day - timedelta(days=1)
        current_streak = streak
    else:
        current_streak = 0

    # 3. Longest Streak
    if not active_dates:
        longest_streak = 0
    else:
        longest = 1
        current_run = 1
        for i in range(1, len(active_dates)):
            if active_dates[i] == active_dates[i - 1] + timedelta(days=1):
                current_run += 1
                if current_run > longest:
                    longest = current_run
            else:
                current_run = 1
        longest_streak = max(longest, current_streak)

    # 4. Weekly completion percentage & progress trend
    if tasks_completed_last_week > 0:
        diff_pct = round(((tasks_completed_this_week - tasks_completed_last_week) / tasks_completed_last_week) * 100)
        progress_trend = f"{'+' if diff_pct >= 0 else ''}{diff_pct}% vs last week"
    elif tasks_completed_this_week > 0:
        progress_trend = f"+{tasks_completed_this_week} this week"
    else:
        progress_trend = "Steady pace"

    # 5. Deterministic Momentum Classification
    if total_tasks > 0 and len(completed_tasks) == total_tasks:
        momentum_state = "ROADMAP_COMPLETED"
    elif current_streak >= 3 and (tasks_completed_today > 0 or tasks_completed_this_week >= 4):
        momentum_state = "MOMENTUM_RISING"
    elif current_streak >= 1 and today_local not in active_date_set and local_now.hour >= 17:
        momentum_state = "STREAK_AT_RISK"
    elif longest_streak > 0 and current_streak == 0 and (not active_dates or (today_local - active_dates[-1]).days > 1):
        momentum_state = "STREAK_BROKEN"
    elif tasks_completed_this_week == 0 and (today_local - start_of_this_week).days >= 3:
        momentum_state = "MOMENTUM_FALLING"
    else:
        momentum_state = "MOMENTUM_STABLE"

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "tasks_completed_today": tasks_completed_today,
        "tasks_completed_this_week": tasks_completed_this_week,
        "tasks_completed_last_week": tasks_completed_last_week,
        "active_days": active_days,
        "progress_trend": progress_trend,
        "momentum_state": momentum_state,
        "today_local": today_local.isoformat(),
        "has_completed_today": today_local in active_date_set,
    }


# ══════════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS HISTORY & IDEMPOTENCY
# ══════════════════════════════════════════════════════════════════════════════

def record_notification(
    project_id: int,
    user_id: str,
    notification_type: str,
    subject: str,
    status: str = "sent",
    task_id: str = "",
    provider_message_id: str = "",
    local_date: Optional[str] = None,
    error: str = ""
) -> int:
    init_tables()
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            INSERT INTO lockin_notifications (project_id, user_id, notification_type, task_id, subject, status, provider_message_id, local_date, sent_at, error)
            VALUES (%s, %s, %s, %s, %s, %s, %s, COALESCE(%s::date, CURRENT_DATE), now(), %s)
            RETURNING id;
        """, (project_id, user_id, notification_type, task_id, subject, status, provider_message_id, local_date, error))
        nid = cur.fetchone()[0]
        c.commit()
    return nid


def has_notification_been_sent_today(project_id: int, notification_type: str, local_date_str: str, user_tz_str: str = "Asia/Kolkata") -> bool:
    """
    Idempotency check: returns True if a notification of `notification_type` was already successfully sent
    for `project_id` on the given local date (formatted YYYY-MM-DD) in the user's timezone.
    """
    init_tables()
    with _conn() as c:
        cur = c.cursor()
        cur.execute("""
            SELECT id FROM lockin_notifications
            WHERE project_id = %s 
              AND notification_type = %s 
              AND status = 'sent'
              AND (
                  local_date = %s::date
                  OR (sent_at AT TIME ZONE %s)::date = %s::date
              );
        """, (project_id, notification_type, local_date_str, user_tz_str, local_date_str))
        row = cur.fetchone()
        return row is not None


def get_notifications(project_id: int, user_id: str, limit: int = 20) -> list[dict]:
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT id, project_id, notification_type, task_id, subject, status, sent_at, error
            FROM lockin_notifications
            WHERE project_id = %s AND user_id = %s
            ORDER BY sent_at DESC
            LIMIT %s;
        """, (project_id, user_id, limit))
        return [dict(r) for r in cur.fetchall()]


# ══════════════════════════════════════════════════════════════════════════════
# AGENT ACTIONS & HUMAN-IN-THE-LOOP (HITL)
# ══════════════════════════════════════════════════════════════════════════════

def create_agent_action(project_id: int, user_id: str, action_type: str, title: str, description: str, details: dict = None, requires_approval: bool = False) -> int:
    init_tables()
    details_json = json.dumps(details or {})
    status = "pending" if requires_approval else "completed"
    executed_at_sql = "now()" if not requires_approval else "NULL"

    with _conn() as c:
        cur = c.cursor()
        cur.execute(f"""
            INSERT INTO lockin_agent_actions (project_id, user_id, action_type, title, description, details, status, requires_approval, created_at, executed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now(), {executed_at_sql})
            RETURNING id;
        """, (project_id, user_id, action_type, title, description, details_json, status, requires_approval))
        action_id = cur.fetchone()[0]
        c.commit()
    return action_id


def get_agent_actions(project_id: int, user_id: str, limit: int = 20) -> list[dict]:
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT * FROM lockin_agent_actions
            WHERE project_id = %s AND user_id = %s
            ORDER BY created_at DESC
            LIMIT %s;
        """, (project_id, user_id, limit))
        rows = cur.fetchall()
        res = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("details"), str):
                try:
                    d["details"] = json.loads(d["details"])
                except Exception:
                    pass
            res.append(d)
        return res


def get_pending_recommendations(project_id: int, user_id: str) -> list[dict]:
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT * FROM lockin_agent_actions
            WHERE project_id = %s AND user_id = %s AND requires_approval = TRUE AND status = 'pending'
            ORDER BY created_at DESC;
        """, (project_id, user_id))
        rows = cur.fetchall()
        res = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("details"), str):
                try:
                    d["details"] = json.loads(d["details"])
                except Exception:
                    pass
            res.append(d)
        return res


def approve_agent_action(action_id: int, user_id: str) -> dict | None:
    """
    Approves a recommendation and applies the proposed changes to the project's roadmap in the DB.
    """
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT * FROM lockin_agent_actions
            WHERE id = %s AND user_id = %s AND status = 'pending';
        """, (action_id, user_id))
        action = cur.fetchone()
        if not action:
            return None
        
        action = dict(action)
        details = action.get("details")
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except Exception:
                details = {}

        project_id = action["project_id"]
        
        # If the recommendation contains modified roadmap structure or moved tasks, apply it
        modified_roadmap = details.get("modified_roadmap")
        if modified_roadmap and isinstance(modified_roadmap, dict):
            cur.execute("""
                UPDATE lockin_projects
                SET roadmap_data = %s, updated_at = now()
                WHERE id = %s AND user_id = %s;
            """, (json.dumps(modified_roadmap), project_id, user_id))
            
            # Update weeks in lockin_tasks if task movement was specified
            for move in details.get("moved_tasks", []):
                t_id = move.get("task_id")
                to_week = move.get("to_week")
                if t_id and to_week:
                    cur.execute("""
                        UPDATE lockin_tasks
                        SET week_number = %s, updated_at = now()
                        WHERE project_id = %s AND task_id = %s;
                    """, (to_week, project_id, t_id))

        # Mark action as approved & executed
        cur.execute("""
            UPDATE lockin_agent_actions
            SET status = 'approved', approved_at = now(), executed_at = now()
            WHERE id = %s
            RETURNING *;
        """, (action_id,))
        updated_action = dict(cur.fetchone())
        c.commit()

        # Log an activity entry for the approval
        create_agent_action(
            project_id=project_id,
            user_id=user_id,
            action_type="recommendation_applied",
            title=f"Applied Recommendation: {action['title']}",
            description="User approved and applied the AI recovery recommendation.",
            details={"original_action_id": action_id},
            requires_approval=False
        )

        return updated_action


def reject_agent_action(action_id: int, user_id: str) -> dict | None:
    """
    Rejects a recommendation without making any changes to the roadmap.
    """
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            UPDATE lockin_agent_actions
            SET status = 'rejected', rejected_at = now()
            WHERE id = %s AND user_id = %s AND status = 'pending'
            RETURNING *;
        """, (action_id, user_id))
        row = cur.fetchone()
        if not row:
            return None
        c.commit()
        res = dict(row)
        
        # Log activity entry for the rejection
        create_agent_action(
            project_id=res["project_id"],
            user_id=user_id,
            action_type="recommendation_rejected",
            title=f"Kept Current Roadmap: {res['title']}",
            description="User decided to maintain their current roadmap schedule.",
            details={"original_action_id": action_id},
            requires_approval=False
        )
        return res


# ══════════════════════════════════════════════════════════════════════════════
# SCHEDULER HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_all_active_projects_for_scheduler() -> list[dict]:
    """
    Returns all active projects with preferences and active Gmail connections for background evaluation.
    """
    init_tables()
    with _conn() as c:
        cur = c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT 
                p.id AS project_id,
                p.user_id,
                p.user_email,
                p.blueprint_id,
                p.roadmap_data,
                p.start_date,
                p.target_date,
                p.status AS project_status,
                pref.email_enabled,
                pref.daily_reminder_enabled,
                pref.deadline_alert_enabled,
                pref.weekly_report_enabled,
                pref.recovery_enabled,
                pref.reminder_time,
                pref.timezone,
                g.google_email,
                g.status AS gmail_status
            FROM lockin_projects p
            JOIN lockin_preferences pref ON p.id = pref.project_id
            LEFT JOIN gmail_connections g ON p.user_id = g.user_id
            WHERE p.status = 'active' 
              AND pref.email_enabled = TRUE
              AND g.status = 'active'
              AND g.refresh_token IS NOT NULL;
        """)
        rows = cur.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("roadmap_data"), str):
                try:
                    d["roadmap_data"] = json.loads(d["roadmap_data"])
                except Exception:
                    d["roadmap_data"] = {}
            result.append(d)
        return result