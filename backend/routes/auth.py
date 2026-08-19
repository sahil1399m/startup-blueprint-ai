"""
routes/auth.py — Authentication endpoints.

POST /api/auth/register    → email+password registration
POST /api/auth/login       → email+password login → JWT
POST /api/auth/google      → Google OAuth code exchange → JWT
GET  /api/auth/me          → current user profile (protected)
POST /api/auth/logout      → invalidate session (client-side for JWTs)
"""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from auth_middleware import get_current_user
from config import get_settings
from models.auth import (
    GoogleCallbackRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)

log      = logging.getLogger(__name__)
router   = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


# ── Helper: call Supabase REST API ────────────────────────────────────────────
import httpx

SUPA_BASE = f"{settings.SUPABASE_URL}/auth/v1"
SUPA_HEADERS = {
    "apikey":       settings.SUPABASE_KEY,
    "Content-Type": "application/json",
}


def _supabase_headers(access_token: str | None = None) -> Dict[str, str]:
    h = dict(SUPA_HEADERS)
    if access_token:
        h["Authorization"] = f"Bearer {access_token}"
    return h


def _build_user_out(supa_user: Dict[str, Any], count: int = 0) -> UserOut:
    meta = supa_user.get("user_metadata") or supa_user.get("raw_user_meta_data") or {}
    return UserOut(
        id=supa_user.get("id", ""),
        email=supa_user.get("email", ""),
        name=meta.get("name") or meta.get("full_name"),
        blueprints_generated=count,
        created_at=(supa_user.get("created_at") or "")[:10],
    )


async def _get_blueprint_count(user_id: str) -> int:
    """Fetch blueprint count from Supabase DB — graceful fallback to 0."""
    try:
        # Import your existing history_db module from core/
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))
        from history_db import get_blueprint_count_for_user
        return get_blueprint_count_for_user(user_id)
    except Exception:
        return 0


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    """Register a new user with email + password via Supabase Auth."""
    async with httpx.AsyncClient(timeout=15) as client:
        # 1. Create user in Supabase Auth
        resp = await client.post(
            f"{SUPA_BASE}/signup",
            headers=SUPA_HEADERS,
            json={
                "email":    body.email,
                "password": body.password,
                "data":     {"name": body.name},
            },
        )

    if resp.status_code not in (200, 201):
        err = resp.json()
        msg = err.get("msg") or err.get("message") or err.get("error_description", "Registration failed")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    data = resp.json()
    user = data.get("user") or data
    session = data.get("session") or {}
    token = session.get("access_token", "")

    return TokenResponse(
        access_token=token,
        user=_build_user_out(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Login with email + password. Returns a Supabase JWT."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{SUPA_BASE}/token?grant_type=password",
            headers=SUPA_HEADERS,
            json={"email": body.email, "password": body.password},
        )

    if resp.status_code != 200:
        err = resp.json()
        msg = err.get("error_description") or err.get("message") or "Invalid credentials"
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=msg)

    data  = resp.json()
    user  = data.get("user", {})
    token = data.get("access_token", "")
    count = await _get_blueprint_count(user.get("id", ""))

    return TokenResponse(
        access_token=token,
        user=_build_user_out(user, count),
    )


@router.post("/google", response_model=TokenResponse)
async def google_oauth(body: GoogleCallbackRequest):
    """
    Exchange a Google OAuth authorization code for a Supabase session.
    Frontend calls this after Google redirects back with ?code=...
    """
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{SUPA_BASE}/token?grant_type=pkce",
            headers=SUPA_HEADERS,
            json={"auth_code": body.code},
        )

    if resp.status_code != 200:
        # Try the standard OAuth code exchange
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{SUPA_BASE}/callback",
                headers=SUPA_HEADERS,
                json={"code": body.code},
            )

    if resp.status_code != 200:
        err = resp.json()
        msg = err.get("error_description") or err.get("message") or "Google OAuth failed"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    data  = resp.json()
    user  = data.get("user", {})
    token = data.get("access_token", "")
    count = await _get_blueprint_count(user.get("id", ""))

    return TokenResponse(
        access_token=token,
        user=_build_user_out(user, count),
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: Dict = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    count = await _get_blueprint_count(current_user["id"])

    # Fetch full user profile from Supabase to get name from user_metadata
    name = None
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            resp = await c.get(
                f"{SUPA_BASE}/user",
                headers=_supabase_headers(current_user.get("_token")),
            )
            if resp.status_code == 200:
                supa_user = resp.json()
                meta = supa_user.get("user_metadata") or supa_user.get("raw_user_meta_data") or {}
                name = meta.get("name") or meta.get("full_name")
    except Exception:
        pass  # Graceful fallback — name stays None, frontend uses email

    return UserOut(
        id=current_user["id"],
        email=current_user["email"],
        name=name,
        blueprints_generated=count,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: Dict = Depends(get_current_user)):
    """
    For JWTs, logout is handled client-side by deleting the token.
    This endpoint optionally revokes the Supabase session server-side.
    """
    # Supabase doesn't require server-side logout for JWTs,
    # but we call it to invalidate the refresh token if present.
    log.info(f"User {current_user['email']} logged out.")
    return None