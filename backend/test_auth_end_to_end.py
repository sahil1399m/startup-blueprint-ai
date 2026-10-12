"""
test_auth_end_to_end.py — Comprehensive automated test suite for authentication.

Tests:
  1. Successful email registration
  2. Duplicate email registration rejected with 400
  3. Successful email login
  4. Invalid credentials rejected with 401
  5. Profile retrieval (/api/auth/me) with valid token
  6. Token persistence & validation via auth_middleware
  7. Protected endpoint rejection with 401 for unauthenticated request
  8. Google OAuth URL generation (/api/auth/google/url)
  9. Google OAuth callback success (new user)
  10. Google OAuth callback success (existing user linking)
  11. Google OAuth callback failure (invalid/expired code)
  12. Logout endpoint (/api/auth/logout)
"""

import os
import sys
import uuid
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

# Setup path
BACKEND_DIR = os.path.dirname(__file__)
CORE_DIR = os.path.join(BACKEND_DIR, "core")
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, CORE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from routes.auth import router as auth_router, create_access_token
from auth_middleware import _decode_token

# Mount auth_router on clean FastAPI app for fast, isolated test execution
app = FastAPI()
app.include_router(auth_router)

client = TestClient(app)


class TestAuthenticationEndToEnd(unittest.TestCase):

    def setUp(self):
        # Use valid domain so external validators accept email format
        self.test_email = f"test_{uuid.uuid4().hex[:8]}@ventureiq.ai"
        self.test_password = "StrongPassword123!"
        self.test_name = "Alex Founder"

    # ── 1. REGISTRATION TESTS ──────────────────────────────────────────────────

    def test_01_successful_registration(self):
        """Test that registering a new user succeeds and returns access_token + user data."""
        resp = client.post(
            "/api/auth/register",
            json={
                "name": self.test_name,
                "email": self.test_email,
                "password": self.test_password,
            },
        )
        self.assertEqual(resp.status_code, 201, f"Registration failed: {resp.text}")
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertTrue(len(data["access_token"]) > 20, "Access token should be a valid non-empty JWT")
        self.assertIn("user", data)
        self.assertEqual(data["user"]["email"].lower(), self.test_email.lower())
        self.assertEqual(data["user"]["name"], self.test_name)

        # Verify token is decodable
        payload = _decode_token(data["access_token"])
        self.assertEqual(payload["email"].lower(), self.test_email.lower())

    def test_02_duplicate_registration_rejected(self):
        """Test that duplicate registration with same email returns 400 with user-friendly error."""
        # First registration
        r1 = client.post(
            "/api/auth/register",
            json={
                "name": self.test_name,
                "email": self.test_email,
                "password": self.test_password,
            },
        )
        self.assertEqual(r1.status_code, 201)

        # Duplicate registration
        r2 = client.post(
            "/api/auth/register",
            json={
                "name": "Different Name",
                "email": self.test_email,
                "password": "AnotherPassword456!",
            },
        )
        self.assertEqual(r2.status_code, 400)
        self.assertIn("already exists", r2.json()["detail"].lower())

    # ── 2. LOGIN TESTS ────────────────────────────────────────────────────────

    def test_03_successful_login(self):
        """Test that existing user can log in with valid credentials."""
        # Register first
        client.post(
            "/api/auth/register",
            json={
                "name": self.test_name,
                "email": self.test_email,
                "password": self.test_password,
            },
        )

        # Login
        resp = client.post(
            "/api/auth/login",
            json={
                "email": self.test_email,
                "password": self.test_password,
            },
        )
        self.assertEqual(resp.status_code, 200, f"Login failed: {resp.text}")
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertTrue(len(data["access_token"]) > 20)
        self.assertEqual(data["user"]["email"].lower(), self.test_email.lower())

    def test_04_invalid_credentials_rejected(self):
        """Test that wrong password produces 401 Unauthorized without breaking."""
        # Register first
        client.post(
            "/api/auth/register",
            json={
                "name": self.test_name,
                "email": self.test_email,
                "password": self.test_password,
            },
        )

        # Wrong password
        resp = client.post(
            "/api/auth/login",
            json={
                "email": self.test_email,
                "password": "WrongPassword999!",
            },
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn("invalid", resp.json()["detail"].lower())

    # ── 3. PROFILE & PERSISTENCE TESTS ────────────────────────────────────────

    def test_05_auth_me_persistence(self):
        """Test that /api/auth/me returns current user profile with valid token."""
        token = create_access_token(
            user_id="test-uuid-12345",
            email="persistence_test@ventureiq.ai",
            name="Persistence User",
        )
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["email"], "persistence_test@ventureiq.ai")

    def test_06_unauthenticated_request_rejected(self):
        """Test that accessing protected endpoint without token returns 401/403."""
        resp = client.get("/api/auth/me")
        self.assertIn(resp.status_code, (401, 403))

    # ── 4. GOOGLE OAUTH TESTS ─────────────────────────────────────────────────

    def test_07_google_auth_url_generation(self):
        """Test generating Google OAuth authorization URL."""
        resp = client.get("/api/auth/google/url?redirect_uri=http://localhost:5173/auth/callback")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("url", data)
        self.assertIn("state", data)
        self.assertIn("accounts.google.com", data["url"])
        self.assertIn("openid", data["url"])
        self.assertIn("email", data["url"])
        self.assertIn("profile", data["url"])
        # Verify Gmail scope is NOT in auth URL
        self.assertNotIn("gmail.send", data["url"])

    @patch("routes.auth.httpx.AsyncClient")
    def test_08_google_oauth_callback_new_user(self, mock_async_client):
        """Test Google OAuth code exchange creates new user and returns JWT."""
        mock_google_token = MagicMock()
        mock_google_token.status_code = 200
        mock_google_token.json.return_value = {"access_token": "mock_google_access_token"}

        mock_google_userinfo = MagicMock()
        mock_google_userinfo.status_code = 200
        dynamic_sub = f"google-sub-{uuid.uuid4().hex[:8]}"
        mock_google_userinfo.json.return_value = {
            "sub": dynamic_sub,
            "email": f"google_{uuid.uuid4().hex[:6]}@ventureiq.ai",
            "email_verified": True,
            "name": "Google Founder",
            "picture": "https://example.com/avatar.jpg",
        }

        mock_instance = MagicMock()
        mock_instance.post = AsyncMock(return_value=mock_google_token)
        mock_instance.get = AsyncMock(return_value=mock_google_userinfo)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.return_value = mock_instance

        resp = client.post(
            "/api/auth/google",
            json={
                "code": "mock_authorization_code_123",
                "redirect_uri": "http://localhost:5173/auth/callback",
            },
        )
        self.assertEqual(resp.status_code, 200, f"Google auth failed: {resp.text}")
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertTrue(len(data["access_token"]) > 20)
        self.assertEqual(data["user"]["name"], "Google Founder")

    @patch("routes.auth.httpx.AsyncClient")
    def test_09_google_oauth_callback_existing_user(self, mock_async_client):
        """Test Google OAuth code exchange links with existing user account."""
        # Pre-register email user
        existing_email = f"link_{uuid.uuid4().hex[:6]}@ventureiq.ai"
        client.post(
            "/api/auth/register",
            json={
                "name": "Existing Account",
                "email": existing_email,
                "password": "Password123!",
            },
        )

        mock_google_token = MagicMock()
        mock_google_token.status_code = 200
        mock_google_token.json.return_value = {"access_token": "mock_google_access_token"}

        dynamic_sub_linked = f"google-sub-linked-{uuid.uuid4().hex[:8]}"
        mock_google_userinfo = MagicMock()
        mock_google_userinfo.status_code = 200
        mock_google_userinfo.json.return_value = {
            "sub": dynamic_sub_linked,
            "email": existing_email,
            "email_verified": True,
            "name": "Existing Account",
            "picture": "https://example.com/pic.jpg",
        }

        mock_instance = MagicMock()
        mock_instance.post = AsyncMock(return_value=mock_google_token)
        mock_instance.get = AsyncMock(return_value=mock_google_userinfo)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.return_value = mock_instance

        resp = client.post(
            "/api/auth/google",
            json={
                "code": "mock_code_for_existing_user",
                "redirect_uri": "http://localhost:5173/auth/callback",
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["user"]["email"].lower(), existing_email.lower())

    @patch("routes.auth.httpx.AsyncClient")
    def test_10_google_oauth_failure_handling(self, mock_async_client):
        """Test Google OAuth code exchange failure (expired or invalid code) returns 400."""
        mock_google_token = MagicMock()
        mock_google_token.status_code = 400
        mock_google_token.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Code was already redeemed or expired",
        }

        mock_instance = MagicMock()
        mock_instance.post = AsyncMock(return_value=mock_google_token)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.return_value = mock_instance

        resp = client.post(
            "/api/auth/google",
            json={
                "code": "expired_or_invalid_code",
                "redirect_uri": "http://localhost:5173/auth/callback",
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("failed", resp.json()["detail"].lower())

    # ── 5. LOGOUT TESTS ───────────────────────────────────────────────────────

    def test_11_logout_endpoint(self):
        """Test logout endpoint returns 204 No Content for authenticated user."""
        token = create_access_token(
            user_id="test-logout-uuid",
            email="logout_test@ventureiq.ai",
            name="Logout User",
        )
        resp = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 204)


if __name__ == "__main__":
    unittest.main()
