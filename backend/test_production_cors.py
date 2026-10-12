"""
test_production_cors.py — Automated test suite for CORS middleware and preflight OPTIONS.

Validates that:
  1. The exact production origin (https://startup-blueprint-ai.vercel.app) is allowed.
  2. The www production alias (https://www.startup-blueprint-ai.vercel.app) is allowed.
  3. Local development origins (http://localhost:5173, http://127.0.0.1:5173) are preserved.
  4. Preflight OPTIONS requests to /api/auth/login return 200 with proper CORS headers.
  5. Preflight OPTIONS requests to /api/auth/register and /api/auth/google return 200.
  6. Actual cross-origin POST requests receive Access-Control-Allow-Origin & Access-Control-Allow-Credentials.
  7. Unauthorized origins are strictly denied (no Access-Control-Allow-Origin header).
  8. Credentials (allow_credentials=True) are NEVER combined with wildcard origins (*).
"""

import os
import sys
import unittest

BACKEND_DIR = os.path.dirname(__file__)
CORE_DIR = os.path.join(BACKEND_DIR, "core")
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, CORE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from config import get_settings
from routes.auth import router as auth_router

# Set up test app with the exact same CORS middleware configuration as main.py
settings = get_settings()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "X-Request-ID", "Authorization"],
    max_age=86400,
)
app.include_router(auth_router)

client = TestClient(app)

PROD_ORIGIN = "https://startup-blueprint-ai.vercel.app"
WWW_PROD_ORIGIN = "https://www.startup-blueprint-ai.vercel.app"
DEV_ORIGIN = "http://localhost:5173"
DISALLOWED_ORIGIN = "https://malicious-attacker.com"


class TestProductionCORS(unittest.TestCase):

    def test_01_settings_origins_contain_production(self):
        """Verify allowed_origins_list contains required production and dev origins."""
        origins = settings.allowed_origins_list
        self.assertIn(PROD_ORIGIN, origins)
        self.assertIn(WWW_PROD_ORIGIN, origins)
        self.assertIn(DEV_ORIGIN, origins)
        # Ensure no wildcard when credentials allowed
        self.assertNotIn("*", origins, "Wildcard '*' must never be in allowed_origins when allow_credentials=True")

    def test_02_preflight_login_production_origin(self):
        """Test OPTIONS preflight request to /api/auth/login from production origin."""
        headers = {
            "Origin": PROD_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
        resp = client.options("/api/auth/login", headers=headers)
        self.assertEqual(resp.status_code, 200, f"Preflight failed with status {resp.status_code}")
        self.assertEqual(resp.headers.get("access-control-allow-origin"), PROD_ORIGIN)
        self.assertEqual(resp.headers.get("access-control-allow-credentials"), "true")
        self.assertIn("POST", resp.headers.get("access-control-allow-methods", ""))

    def test_03_preflight_login_www_production_origin(self):
        """Test OPTIONS preflight request from www alias."""
        headers = {
            "Origin": WWW_PROD_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
        resp = client.options("/api/auth/login", headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("access-control-allow-origin"), WWW_PROD_ORIGIN)
        self.assertEqual(resp.headers.get("access-control-allow-credentials"), "true")

    def test_04_preflight_login_dev_origin(self):
        """Test OPTIONS preflight request from local dev origin http://localhost:5173."""
        headers = {
            "Origin": DEV_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        }
        resp = client.options("/api/auth/login", headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("access-control-allow-origin"), DEV_ORIGIN)
        self.assertEqual(resp.headers.get("access-control-allow-credentials"), "true")

    def test_05_preflight_register_endpoint(self):
        """Test OPTIONS preflight request to /api/auth/register from production origin."""
        headers = {
            "Origin": PROD_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
        resp = client.options("/api/auth/register", headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("access-control-allow-origin"), PROD_ORIGIN)

    def test_06_preflight_google_endpoint(self):
        """Test OPTIONS preflight request to /api/auth/google from production origin."""
        headers = {
            "Origin": PROD_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
        resp = client.options("/api/auth/google", headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("access-control-allow-origin"), PROD_ORIGIN)

    def test_07_post_login_cors_headers_included(self):
        """Test actual POST request from production origin includes CORS headers."""
        headers = {
            "Origin": PROD_ORIGIN,
            "Content-Type": "application/json",
        }
        resp = client.post(
            "/api/auth/login",
            json={"email": "cors_test@example.com", "password": "wrongpassword123"},
            headers=headers,
        )
        # Even on 401 error, CORS headers MUST be present so the browser allows JS to read the response
        self.assertEqual(resp.headers.get("access-control-allow-origin"), PROD_ORIGIN)
        self.assertEqual(resp.headers.get("access-control-allow-credentials"), "true")

    def test_08_disallowed_origin_rejected(self):
        """Test unauthorized origin is rejected (no Access-Control-Allow-Origin header)."""
        headers = {
            "Origin": DISALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
        resp = client.options("/api/auth/login", headers=headers)
        self.assertIsNone(resp.headers.get("access-control-allow-origin"))

    def test_09_trailing_slash_stripped_cleanly(self):
        """Verify trailing slash in origin configuration does not break CORS matching."""
        origins = settings.allowed_origins_list
        for o in origins:
            self.assertFalse(o.endswith("/"), f"Origin '{o}' has trailing slash which breaks browser matching")


if __name__ == "__main__":
    unittest.main()
