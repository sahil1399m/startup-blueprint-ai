"""
routes/auth.py — Authentication endpoints.

POST /api/auth/register    → email+password registration
POST /api/auth/login       → email+password login → JWT
GET  /api/auth/google/url  → generate Google OAuth authorization URL
POST /api/auth/google      → Google OAuth code exchange → JWT
GET  /api/auth/me          → current user profile (protected)
POST /api/auth/logout      → invalidate session
"""

from __future__ import annotations
import json
import logging
import os
import secrets
import sys
import time
import urllib.parse
from typing import Any, Dict, Optional

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth_middleware import get_current_user
from config import get_settings
from models.auth import (
    GoogleAuthUrlResponse,
    GoogleCallbackRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

# Ensure core/ is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
import auth_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()

SUPA_BASE = f"{settings.SUPABASE_URL}/auth/v1"
SUPA_HEADERS = {
    "apikey": settings.SUPABASE_KEY,
    "Content-Type": "application/json",
}


def _supabase_headers(access_token: str | None = None) -> Dict[str, str]:
    h = dict(SUPA_HEADERS)
    if access_token:
        h["Authorization"] = f"Bearer {access_token}"
    return h


def create_access_token(user_id: str, email: str, name: Optional[str] = None) -> str:
    """Generate a valid Supabase-compatible JWT signed with SUPABASE_JWT_SECRET."""
    now = int(time.time())
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "email": email,
        "app_metadata": {"provider": "email", "providers": ["email"]},
        "user_metadata": {"name": name} if name else {},
        "iat": now,
        "exp": now + (3600 * 24 * 7),  # 7 days
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


def _build_user_out(user_data: Dict[str, Any], count: int = 0) -> UserOut:
    meta = user_data.get("user_metadata") or user_data.get("raw_user_meta_data") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}
    return UserOut(
        id=str(user_data.get("id", "")),
        email=user_data.get("email", ""),
        name=meta.get("name") or meta.get("full_name"),
        blueprints_generated=count,
        created_at=str(user_data.get("created_at") or "")[:10],
    )


async def _get_blueprint_count(user_id_or_email: str) -> int:
    """Fetch blueprint count from database — graceful fallback to 0."""
    try:
        from history_db import get_blueprint_count_for_user
        return get_blueprint_count_for_user(user_id_or_email)
    except Exception:
        return 0


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    """
    Register a new user with name, email, and password.
    Ensures user is auto-confirmed and returns a full valid session token immediately.
    """
    email = body.email.strip().lower()

    # 1. Check for duplicate registration first
    existing = auth_db.get_user_by_email(email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in.",
        )

    user_out_data = None
    access_token = ""

    # 2. Attempt registration via Supabase Auth
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{SUPA_BASE}/signup",
                headers=SUPA_HEADERS,
                json={
                    "email": email,
                    "password": body.password,
                    "data": {"name": body.name, "full_name": body.name},
                },
            )

        if resp.status_code in (200, 201):
            data = resp.json()
            user = data.get("user") or data
            user_id = str(user.get("id", ""))
            session = data.get("session") or {}
            token = session.get("access_token", "")

            # Auto-confirm in database so email confirmation does not block future logins
            auth_db.confirm_user_email(user_id)

            if not token:
                # If Supabase did not return a session (e.g. mailer confirmation setting), issue JWT directly
                token = create_access_token(user_id=user_id, email=email, name=body.name)

            user_out_data = user
            access_token = token
        else:
            err = resp.json()
            err_msg = str(err.get("msg") or err.get("message") or "")
            log.warning(f"Supabase /signup returned {resp.status_code}: {err_msg}")

            # If duplicate in Supabase
            if "already registered" in err_msg.lower() or "unique" in err_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An account with this email address already exists. Please sign in.",
                )

            # If Supabase email rate limit or error, fall back to direct database creation
            created = auth_db.create_email_user(name=body.name, email=email, password=body.password)
            if not created:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=err_msg or "Registration failed. Please try again.",
                )
            user_out_data = created
            access_token = create_access_token(user_id=str(created["id"]), email=email, name=body.name)

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Registration error: {e}")
        # Direct DB fallback on unexpected connection errors
        created = auth_db.create_email_user(name=body.name, email=email, password=body.password)
        if not created:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration failed. Please try again.")
        user_out_data = created
        access_token = create_access_token(user_id=str(created["id"]), email=email, name=body.name)

    return TokenResponse(
        access_token=access_token,
        user=_build_user_out(user_out_data),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """
    Login with email + password. Returns a verified Supabase JWT.
    Handles auto-confirming unconfirmed accounts seamlessly.
    """
    email = body.email.strip().lower()

    # 1. Attempt Supabase Auth login
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{SUPA_BASE}/token?grant_type=password",
            headers=SUPA_HEADERS,
            json={"email": email, "password": body.password},
        )

    if resp.status_code == 200:
        data = resp.json()
        user = data.get("user", {})
        token = data.get("access_token", "")
        count = await _get_blueprint_count(email)

        # Ensure confirmed in database
        auth_db.confirm_user_email(user.get("id", ""))

        return TokenResponse(
            access_token=token,
            user=_build_user_out(user, count),
        )

    # 2. Check if user exists in database (fallback for unconfirmed users or DB-created users)
    err = resp.json() if resp.status_code != 500 else {}
    error_desc = err.get("error_description") or err.get("message") or ""

    user_db = auth_db.get_user_by_email(email)
    if user_db:
        # Check password against database
        if auth_db.verify_user_password(user_db, body.password):
            user_id = str(user_db["id"])
            auth_db.confirm_user_email(user_id)
            meta = user_db.get("raw_user_meta_data") or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            name = meta.get("name") or meta.get("full_name")
            token = create_access_token(user_id=user_id, email=email, name=name)
            count = await _get_blueprint_count(email)

            return TokenResponse(
                access_token=token,
                user=_build_user_out(user_db, count),
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
    )


@router.get("/google/url", response_model=GoogleAuthUrlResponse)
async def get_google_auth_url(
    redirect_uri: Optional[str] = Query(None, description="Frontend callback URL")
):
    """
    Generate Google OAuth 2.0 authorization URL with requested scopes (openid, email, profile).
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GOOGLE_CLIENT_ID is not configured on the server.",
        )

    callback_url = redirect_uri or f"{settings.FRONTEND_URL}/auth/callback"
    state_token = secrets.token_urlsafe(24)

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "state": state_token,
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    return GoogleAuthUrlResponse(url=auth_url, state=state_token)


@router.post("/google", response_model=TokenResponse)
async def google_oauth(body: GoogleCallbackRequest):
    """
    Exchange a Google OAuth authorization code for verified user session and JWT.
    Validates with Google token & userinfo endpoints, persists user in database,
    and returns session.
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth credentials are not fully configured on the server.",
        )

    redirect_uri = body.redirect_uri or f"{settings.FRONTEND_URL}/auth/callback"

    # 1. Exchange authorization code with Google OAuth endpoint
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": body.code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    if token_resp.status_code != 200:
        err = token_resp.json()
        log.error(f"Google token exchange failed: {err}")
        err_msg = err.get("error_description") or err.get("error") or "Failed to exchange Google authorization code"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {err_msg}",
        )

    token_data = token_resp.json()
    google_access_token = token_data.get("access_token")
    if not google_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google did not return an access token.",
        )

    # 2. Fetch verified user profile from Google
    async with httpx.AsyncClient(timeout=10) as client:
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {google_access_token}"},
        )

    if userinfo_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve Google user profile.",
        )

    userinfo = userinfo_resp.json()
    email = userinfo.get("email")
    email_verified = userinfo.get("email_verified", False)
    name = userinfo.get("name") or userinfo.get("given_name") or email.split("@")[0]
    google_sub = userinfo.get("sub", "")
    avatar_url = userinfo.get("picture", "")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account did not provide an email address.",
        )

    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google email address is not verified. Please verify your Google email first.",
        )

    # 3. Create or retrieve user in database
    user_record = auth_db.create_or_get_google_user(
        email=email,
        name=name,
        google_sub=google_sub,
        avatar_url=avatar_url,
    )
    user_id = str(user_record["id"])

    # 4. Generate standard Supabase JWT
    access_token = create_access_token(user_id=user_id, email=email, name=name)
    count = await _get_blueprint_count(email)

    return TokenResponse(
        access_token=access_token,
        user=_build_user_out(user_record, count),
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: Dict = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    user_id = current_user["id"]
    email = current_user["email"]
    count = await _get_blueprint_count(email)

    name = None
    # 1. Check database for user metadata
    user_db = auth_db.get_user_by_id(user_id) or auth_db.get_user_by_email(email)
    if user_db:
        meta = user_db.get("raw_user_meta_data") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        name = meta.get("name") or meta.get("full_name")

    # 2. Fallback to Supabase API if needed
    if not name and current_user.get("_token"):
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                resp = await c.get(
                    f"{SUPA_BASE}/user",
                    headers=_supabase_headers(current_user["_token"]),
                )
                if resp.status_code == 200:
                    supa_user = resp.json()
                    meta = supa_user.get("user_metadata") or supa_user.get("raw_user_meta_data") or {}
                    name = meta.get("name") or meta.get("full_name")
        except Exception:
            pass

    return UserOut(
        id=user_id,
        email=email,
        name=name,
        blueprints_generated=count,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: Dict = Depends(get_current_user)):
    """
    Session invalidation. Clears server-side tracking if applicable.
    """
    log.info(f"User {current_user['email']} logged out.")
    return None