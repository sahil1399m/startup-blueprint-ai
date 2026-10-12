"""
core/auth_db.py — Database helper functions for PostgreSQL auth.users.

Manages direct database operations for user registration, login fallback,
email confirmation, and Google OAuth user creation/retrieval.
"""

from __future__ import annotations
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import bcrypt
import psycopg2
import psycopg2.extras

log = logging.getLogger(__name__)


def _conn():
    host = os.environ.get("DB_HOST")
    port = os.environ.get("DB_PORT", "5432")
    database = os.environ.get("DB_NAME", "postgres")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")

    if not host or not user or not password:
        raise RuntimeError("Database credentials missing for auth_db")

    return psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        sslmode="require",
        connect_timeout=10,
    )


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Look up a user in auth.users by email."""
    normalized_email = email.strip().lower()
    try:
        with _conn() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                """
                SELECT id, email, encrypted_password, email_confirmed_at, raw_user_meta_data, raw_app_meta_data, created_at
                FROM auth.users
                WHERE LOWER(email) = %s AND deleted_at IS NULL
                LIMIT 1;
                """,
                (normalized_email,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception as e:
        log.error(f"Error fetching user by email {normalized_email}: {e}")
        return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Look up a user in auth.users by UUID."""
    try:
        uuid_obj = uuid.UUID(str(user_id))
    except (ValueError, AttributeError):
        return None
    try:
        with _conn() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                """
                SELECT id, email, encrypted_password, email_confirmed_at, raw_user_meta_data, raw_app_meta_data, created_at
                FROM auth.users
                WHERE id = %s AND deleted_at IS NULL
                LIMIT 1;
                """,
                (str(uuid_obj),),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception as e:
        log.error(f"Error fetching user by id {user_id}: {e}")
        return None


def confirm_user_email(user_id_or_email: str) -> bool:
    """Ensure user's email is confirmed so subsequent logins succeed."""
    try:
        is_uuid = False
        try:
            uuid.UUID(str(user_id_or_email))
            is_uuid = True
        except (ValueError, AttributeError):
            is_uuid = False

        with _conn() as conn:
            cur = conn.cursor()
            if is_uuid:
                cur.execute(
                    """
                    UPDATE auth.users
                    SET email_confirmed_at = COALESCE(email_confirmed_at, NOW()),
                        updated_at = NOW()
                    WHERE id = %s AND email_confirmed_at IS NULL;
                    """,
                    (user_id_or_email,),
                )
                cur.execute(
                    """
                    UPDATE auth.identities
                    SET identity_data = jsonb_set(identity_data, '{email_verified}', 'true'::jsonb),
                        updated_at = NOW()
                    WHERE user_id = %s;
                    """,
                    (user_id_or_email,),
                )
            else:
                cur.execute(
                    """
                    UPDATE auth.users
                    SET email_confirmed_at = COALESCE(email_confirmed_at, NOW()),
                        updated_at = NOW()
                    WHERE LOWER(email) = LOWER(%s) AND email_confirmed_at IS NULL;
                    """,
                    (user_id_or_email,),
                )
                cur.execute(
                    """
                    UPDATE auth.identities
                    SET identity_data = jsonb_set(identity_data, '{email_verified}', 'true'::jsonb),
                        updated_at = NOW()
                    WHERE LOWER(identity_data->>'email') = LOWER(%s);
                    """,
                    (user_id_or_email,),
                )
            conn.commit()
            return True
    except Exception as e:
        log.error(f"Error confirming user email: {e}")
        return False


def create_email_user(name: str, email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Directly create a user with email + password in auth.users.
    Used when Supabase signup rate-limits or as direct creation.
    Auto-confirms the email so session can be established immediately.
    """
    normalized_email = email.strip().lower()
    user_id = str(uuid.uuid4())
    salt = bcrypt.gensalt()
    encrypted_pw = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    now = datetime.utcnow()

    raw_user_meta = json.dumps({"name": name, "full_name": name})
    raw_app_meta = json.dumps({"provider": "email", "providers": ["email"]})

    try:
        with _conn() as conn:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(
                """
                INSERT INTO auth.users (
                    id, aud, role, email, encrypted_password, email_confirmed_at,
                    raw_user_meta_data, raw_app_meta_data, created_at, updated_at
                )
                VALUES (%s, 'authenticated', 'authenticated', %s, %s, NOW(), %s, %s, NOW(), NOW())
                RETURNING id, email, email_confirmed_at, raw_user_meta_data, created_at;
                """,
                (user_id, normalized_email, encrypted_pw, raw_user_meta, raw_app_meta),
            )
            row = cur.fetchone()

            # Also insert corresponding identity
            identity_id = str(uuid.uuid4())
            identity_data = json.dumps({
                "sub": user_id,
                "email": normalized_email,
                "email_verified": True,
            })
            cur.execute(
                """
                INSERT INTO auth.identities (
                    id, provider_id, user_id, identity_data, provider, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, 'email', NOW(), NOW());
                """,
                (identity_id, user_id, user_id, identity_data),
            )
            conn.commit()
            return dict(row) if row else None
    except Exception as e:
        log.error(f"Error creating email user in database: {e}")
        return None


def verify_user_password(user_record: Dict[str, Any], password: str) -> bool:
    """Verify raw password against bcrypt encrypted_password."""
    encrypted_pw = user_record.get("encrypted_password")
    if not encrypted_pw:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), encrypted_pw.encode("utf-8"))
    except Exception as e:
        log.error(f"Password verification error: {e}")
        return False


def create_or_get_google_user(
    email: str,
    name: str,
    google_sub: str,
    avatar_url: str = "",
) -> Dict[str, Any]:
    """
    Retrieve an existing user by Google sub or email, or create a new user for Google OAuth.
    Always ensures email_confirmed_at is set since Google has verified the email.
    """
    normalized_email = email.strip().lower()

    # 1. First check if a user with this google_sub already exists (subsequent Google login)
    if google_sub:
        try:
            with _conn() as conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(
                    """
                    SELECT user_id FROM auth.identities
                    WHERE provider_id = %s AND provider = 'google'
                    LIMIT 1;
                    """,
                    (google_sub,),
                )
                id_row = cur.fetchone()
                if id_row:
                    user_record = get_user_by_id(str(id_row["user_id"]))
                    if user_record:
                        confirm_user_email(str(user_record["id"]))
                        return user_record
        except Exception as e:
            log.warning(f"Error checking identity by google_sub: {e}")

    # 2. Check if a user with this email already exists (account linking)
    existing = get_user_by_email(normalized_email)

    if existing:
        user_id = str(existing["id"])
        # Ensure email is confirmed
        confirm_user_email(user_id)

        # Update metadata with name/avatar if empty
        meta = existing.get("raw_user_meta_data") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        if not meta.get("name") and name:
            meta["name"] = name
            meta["full_name"] = name
        if not meta.get("avatar_url") and avatar_url:
            meta["avatar_url"] = avatar_url

        try:
            with _conn() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE auth.users
                    SET raw_user_meta_data = %s, updated_at = NOW()
                    WHERE id = %s;
                    """,
                    (json.dumps(meta), user_id),
                )
                # Link google identity if not exists
                cur.execute(
                    """
                    SELECT id FROM auth.identities
                    WHERE user_id = %s AND provider = 'google';
                    """,
                    (user_id,),
                )
                if not cur.fetchone():
                    identity_id = str(uuid.uuid4())
                    identity_data = json.dumps({
                        "sub": google_sub,
                        "email": normalized_email,
                        "email_verified": True,
                    })
                    cur.execute(
                        """
                        INSERT INTO auth.identities (
                            id, provider_id, user_id, identity_data, provider, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, 'google', NOW(), NOW());
                        """,
                        (identity_id, google_sub, user_id, identity_data),
                    )
                conn.commit()
        except Exception as e:
            log.warning(f"Error updating existing Google user metadata: {e}")

        existing["raw_user_meta_data"] = meta
        return existing

    # Create new Google user
    user_id = str(uuid.uuid4())
    raw_user_meta = json.dumps({
        "name": name,
        "full_name": name,
        "avatar_url": avatar_url,
    })
    raw_app_meta = json.dumps({
        "provider": "google",
        "providers": ["google"],
    })

    with _conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            INSERT INTO auth.users (
                id, aud, role, email, email_confirmed_at,
                raw_user_meta_data, raw_app_meta_data, created_at, updated_at
            )
            VALUES (%s, 'authenticated', 'authenticated', %s, NOW(), %s, %s, NOW(), NOW())
            RETURNING id, email, email_confirmed_at, raw_user_meta_data, created_at;
            """,
            (user_id, normalized_email, raw_user_meta, raw_app_meta),
        )
        row = cur.fetchone()

        identity_id = str(uuid.uuid4())
        identity_data = json.dumps({
            "sub": google_sub,
            "email": normalized_email,
            "email_verified": True,
        })
        cur.execute(
            """
            INSERT INTO auth.identities (
                id, provider_id, user_id, identity_data, provider, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, 'google', NOW(), NOW());
            """,
            (identity_id, google_sub, user_id, identity_data),
        )
        conn.commit()
        return dict(row)
