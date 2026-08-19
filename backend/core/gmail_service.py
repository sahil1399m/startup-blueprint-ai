"""
gmail_service.py — Robust, secure Google OAuth 2.0 and Gmail API client for LOCK IN AI.

Handles:
  1. Google OAuth consent URL generation (offline access, gmail.send scope)
  2. Authorization code exchange & server-side token persistence
  3. Automatic token refresh before expiry
  4. Sending RFC 2822 MIME emails via Gmail REST API (https://gmail.googleapis.com/gmail/v1/users/me/messages/send)
  5. Disconnection and revoked credential error handling
"""

import base64
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import logging
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
import httpx

from config import get_settings
from lock_in_db import (
    get_gmail_connection,
    save_gmail_connection,
    update_gmail_access_token,
    mark_gmail_connection_revoked,
    disconnect_gmail as db_disconnect_gmail
)

log = logging.getLogger(__name__)

# Scopes: Send emails only + profile email for displaying connected account
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email"
]

GOOGLE_AUTH_ENDPOINT  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL   = "https://www.googleapis.com/oauth2/v2/userinfo"
GMAIL_SEND_ENDPOINT   = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def is_gmail_configured() -> bool:
    """Check if Google OAuth client credentials are configured in settings or environment."""
    settings = get_settings()
    client_id = settings.GOOGLE_CLIENT_ID or os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = settings.GOOGLE_CLIENT_SECRET or os.getenv("GOOGLE_CLIENT_SECRET", "")
    return bool(client_id and client_secret)


def build_google_auth_url(user_id: str, state_token: str, redirect_uri: str = None) -> str:
    """
    Constructs the Google OAuth 2.0 consent URL for server-side offline access.
    """
    settings = get_settings()
    client_id = settings.GOOGLE_CLIENT_ID or os.getenv("GOOGLE_CLIENT_ID", "")
    r_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI

    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID is not configured. Please set it in .env")

    params = {
        "client_id": client_id,
        "redirect_uri": r_uri,
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",  # Ensures refresh_token is returned
        "state": state_token,
        "include_granted_scopes": "true",
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"


async def exchange_oauth_code(code: str, redirect_uri: str = None) -> dict:
    """
    Exchanges the authorization code for access and refresh tokens, and fetches the user's Google email.
    """
    settings = get_settings()
    client_id = settings.GOOGLE_CLIENT_ID or os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = settings.GOOGLE_CLIENT_SECRET or os.getenv("GOOGLE_CLIENT_SECRET", "")
    r_uri = redirect_uri or settings.GOOGLE_REDIRECT_URI

    if not client_id or not client_secret:
        raise ValueError("Google OAuth credentials (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET) missing.")

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": r_uri,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(GOOGLE_TOKEN_ENDPOINT, data=data)
        if resp.status_code != 200:
            log.error(f"Google token exchange failed: {resp.text}")
            raise RuntimeError(f"Failed to exchange Google OAuth code: {resp.text}")
        
        token_data = resp.json()
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Retrieve the connected Google email address
        headers = {"Authorization": f"Bearer {access_token}"}
        userinfo_resp = await client.get(GOOGLE_USERINFO_URL, headers=headers)
        google_email = ""
        if userinfo_resp.status_code == 200:
            google_email = userinfo_resp.json().get("email", "")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expiry": token_expiry,
            "google_email": google_email,
        }


async def get_valid_access_token(user_id: str, force_refresh: bool = False) -> str:
    """
    Retrieves a valid access token for the given user, refreshing it if expired or forced.
    Raises RuntimeError if credentials are revoked or missing.
    """
    log.info(f"[GMAIL] Loading connection for user {user_id}")
    conn = get_gmail_connection(user_id)
    if not conn or conn.get("status") != "active":
        raise RuntimeError(f"No active Gmail connection found for user {user_id}.")

    google_email = conn.get("google_email") or conn.get("user_email") or "unknown"
    log.info(f"[GMAIL] Google account: {google_email}")

    access_token = conn.get("access_token")
    refresh_token = conn.get("refresh_token")
    token_expiry = conn.get("token_expiry")

    now = datetime.now(timezone.utc)
    # If token expiry exists and is valid for at least 90 more seconds, reuse it (unless forced refresh)
    if not force_refresh and access_token and token_expiry:
        if isinstance(token_expiry, str):
            try:
                token_expiry = datetime.fromisoformat(token_expiry)
            except Exception:
                token_expiry = now
        if token_expiry.tzinfo is None:
            token_expiry = token_expiry.replace(tzinfo=timezone.utc)

        if token_expiry > now + timedelta(seconds=90):
            return access_token

    if not refresh_token:
        log.warning(f"[GMAIL] No refresh token for user {user_id}. Marking REAUTH_REQUIRED.")
        mark_gmail_connection_revoked(user_id, "reauth_required")
        raise RuntimeError("Gmail token expired and no refresh token available. Reconnection required.")

    # Refresh the access token via Google OAuth 2.0 endpoint
    log.info(f"[GMAIL] Access token expired or refresh requested → refreshing via Google OAuth for user {user_id}")
    settings = get_settings()
    client_id = settings.GOOGLE_CLIENT_ID or os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = settings.GOOGLE_CLIENT_SECRET or os.getenv("GOOGLE_CLIENT_SECRET", "")

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(GOOGLE_TOKEN_ENDPOINT, data=data)
        if resp.status_code != 200:
            err_msg = resp.text
            log.error(f"[GMAIL] Failed to refresh Google token for user {user_id}: {err_msg}")
            if "invalid_grant" in err_msg or resp.status_code in (400, 401):
                mark_gmail_connection_revoked(user_id, "reauth_required")
                raise RuntimeError("Gmail authorization was revoked or expired. Please reconnect Gmail.")
            raise RuntimeError(f"Could not refresh Gmail token: {err_msg}")

        refreshed = resp.json()
        new_access_token = refreshed.get("access_token")
        new_expires_in = refreshed.get("expires_in", 3600)
        new_expiry = now + timedelta(seconds=new_expires_in)

        update_gmail_access_token(user_id, new_access_token, new_expiry)
        log.info(f"[GMAIL] Access token refreshed successfully for user {user_id}")
        return new_access_token


async def send_gmail_email(user_id: str, to_email: str, subject: str, text_body: str, html_body: str = None) -> str:
    """
    Sends an email using the Gmail REST API (users.messages.send) on behalf of the connected user.
    Automatically retries with a fresh access token if a 401 Unauthorized is encountered.
    Returns the sent message ID.
    """
    log.info(f"[GMAIL] Sending scheduled notification to {to_email} (Subject: {subject})")
    access_token = await get_valid_access_token(user_id)
    conn = get_gmail_connection(user_id)
    sender_email = conn.get("google_email") if conn else "me"

    message = MIMEMultipart("alternative")
    message["to"] = to_email
    message["from"] = sender_email or "me"
    message["subject"] = subject

    # Plain text part
    message.attach(MIMEText(text_body, "plain", "utf-8"))
    
    # HTML part (if provided)
    if html_body:
        message.attach(MIMEText(html_body, "html", "utf-8"))

    raw_bytes = message.as_bytes()
    raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")

    payload = {"raw": raw_b64}

    async with httpx.AsyncClient(timeout=20.0) as client:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        resp = await client.post(GMAIL_SEND_ENDPOINT, headers=headers, json=payload)
        
        # If access token was rejected (401), attempt an immediate forced token refresh and retry once
        if resp.status_code == 401:
            log.warning(f"[GMAIL] Received 401 Unauthorized for user {user_id}. Attempting forced token refresh & retry...")
            try:
                fresh_access_token = await get_valid_access_token(user_id, force_refresh=True)
                retry_headers = {
                    "Authorization": f"Bearer {fresh_access_token}",
                    "Content-Type": "application/json",
                }
                resp = await client.post(GMAIL_SEND_ENDPOINT, headers=retry_headers, json=payload)
            except Exception as refresh_err:
                log.error(f"[GMAIL] Forced token refresh failed during 401 retry for user {user_id}: {refresh_err}")
                mark_gmail_connection_revoked(user_id, "reauth_required")
                raise RuntimeError(f"Gmail token expired/revoked: {refresh_err}")

        if resp.status_code not in (200, 201):
            log.error(f"[GMAIL] Gmail send API error ({resp.status_code}): {resp.text}")
            if resp.status_code in (401, 403):
                mark_gmail_connection_revoked(user_id, "reauth_required")
            raise RuntimeError(f"Gmail API error ({resp.status_code}): {resp.text}")

        res_json = resp.json()
        message_id = res_json.get("id", "sent")
        log.info(f"[GMAIL] Notification sent successfully to {to_email} (Msg ID: {message_id})")
        return message_id


async def send_test_email(user_id: str, to_email: str = None) -> dict:
    """
    Sends a test verification email to confirm Gmail connectivity.
    """
    conn = get_gmail_connection(user_id)
    if not conn or conn.get("status") != "active":
        raise RuntimeError("No active Gmail connection found for this user.")

    recipient = to_email or conn.get("google_email") or conn.get("user_email")
    if not recipient:
        raise ValueError("Recipient email address not available.")

    subject = "🔒 LOCK IN AI — Connection Successful"
    text_content = (
        "🔒 LOCK IN AI — Connection Successful\n\n"
        "Your LOCK IN AI accountability agent is now active and connected.\n\n"
        "Your personalized accountability emails, deadline alerts, and progress reports "
        "will be delivered according to your notification preferences.\n\n"
        "Stay locked in!\n"
        "— Your LOCK IN Accountability Agent"
    )

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f1f5f9; padding: 20px; }}
        .card {{ background: linear-gradient(135deg, #111827 0%, #1e1b4b 100%); border: 1px solid rgba(59,130,246,0.3); border-radius: 16px; padding: 32px; max-width: 580px; margin: 0 auto; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }}
        .header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }}
        .icon {{ font-size: 28px; }}
        .title {{ font-size: 22px; font-weight: 800; color: #60a5fa; margin: 0; }}
        .badge {{ display: inline-block; background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.3); color: #34d399; font-size: 12px; font-weight: 700; padding: 4px 12px; border-radius: 20px; margin-bottom: 16px; }}
        .text {{ font-size: 14px; line-height: 1.6; color: #cbd5e1; margin-bottom: 16px; }}
        .footer {{ font-size: 12px; color: #64748b; margin-top: 24px; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 16px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="badge">✓ Gmail Connected & Verified</div>
        <h2 class="title">🔒 LOCK IN AI Accountability Agent</h2>
        <p class="text">Your AI accountability agent is now active and linked with your Gmail account (<strong>{recipient}</strong>).</p>
        <p class="text">We'll help you execute your roadmap with daily missions, milestone deadline alerts, and weekly progress reviews.</p>
        <div class="footer">
          Sent by LOCK IN AI · Startup Execution Platform
        </div>
      </div>
    </body>
    </html>
    """

    msg_id = await send_gmail_email(user_id, recipient, subject, text_content, html_content)
    return {
        "status": "success",
        "recipient": recipient,
        "message_id": msg_id,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
