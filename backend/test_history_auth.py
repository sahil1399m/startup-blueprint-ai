"""
test_history_auth.py — Automated verification of cross-tenant history authorization.

Tests:
  TEST A: User A requests User A blueprint -> 200 PASS
  TEST B: User A requests User B blueprint -> 404 DENIED (resource existence masked)
  TEST C: User A exports User B blueprint  -> 404 DENIED
  TEST D: Unauthenticated request          -> 401 DENIED
  TEST E: User B requests User B blueprint -> 200 PASS
"""

import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import psycopg2
from main import app
from auth_middleware import get_current_user
import history_db

client = TestClient(app)

# Test User Fixtures
USER_A = {"id": "test_user_a_uuid", "email": "usera_auth_test@example.com", "role": "authenticated"}
USER_B = {"id": "test_user_b_uuid", "email": "userb_auth_test@example.com", "role": "authenticated"}


def setup_test_blueprints():
    """Create test blueprints for User A and User B in database."""
    history_db.init_db()
    
    bp_a_id = history_db.save_blueprint(
        title="User A AI FinTech SaaS",
        original_query="AI FinTech SaaS for automated invoice matching",
        rewritten_query="AI FinTech SaaS in India",
        sector="fintech",
        stage="MVP",
        business_model="B2B SaaS",
        market="India",
        confidence="High",
        user_email=USER_A["email"],
        sections={"bmc": {"value_prop": "Automated matching"}},
        sources=[{"name": "RBI Guidelines", "url": "https://rbi.org.in"}],
    )

    bp_b_id = history_db.save_blueprint(
        title="User B Agritech Drone Delivery",
        original_query="Autonomous drone delivery for rural agriculture",
        rewritten_query="Agritech drone logistics",
        sector="agritech",
        stage="Idea",
        business_model="B2B Hardware",
        market="India",
        confidence="Moderate",
        user_email=USER_B["email"],
        sections={"bmc": {"value_prop": "Pesticide spraying"}},
        sources=[{"name": "AgriTech India", "url": "https://agri.gov.in"}],
    )

    return bp_a_id, bp_b_id


def cleanup_test_blueprints(bp_a_id, bp_b_id):
    """Clean up test blueprints from database."""
    try:
        conn = history_db._conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM blueprints WHERE id IN (%s, %s);", (bp_a_id, bp_b_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Cleanup error: {e}")


def run_auth_tests():
    print("=" * 70)
    print("STARTING CROSS-TENANT HISTORY AUTHORIZATION TEST SUITE")
    print("=" * 70)

    bp_a_id, bp_b_id = setup_test_blueprints()
    passed = 0
    total = 5

    try:
        # -------------------------------------------------------------
        # TEST A: User A requests User A blueprint -> PASS
        # -------------------------------------------------------------
        print("\n[TEST A] User A requesting User A's own blueprint...", flush=True)
        app.dependency_overrides[get_current_user] = lambda: USER_A
        resp_a = client.get(f"/api/history/{bp_a_id}")
        assert resp_a.status_code == 200, f"Expected 200, got {resp_a.status_code}: {resp_a.text}"
        data_a = resp_a.json()
        assert data_a["id"] == bp_a_id
        assert data_a["user_email"] == USER_A["email"]
        print("  [PASS] User A successfully accessed own blueprint.", flush=True)
        passed += 1

        # -------------------------------------------------------------
        # TEST B: User A requests User B blueprint -> DENIED (404)
        # -------------------------------------------------------------
        print("\n[TEST B] User A requesting User B's blueprint (cross-tenant access)...", flush=True)
        app.dependency_overrides[get_current_user] = lambda: USER_A
        resp_b_by_a = client.get(f"/api/history/{bp_b_id}")
        assert resp_b_by_a.status_code == 404, f"Expected 404 Not Found, got {resp_b_by_a.status_code}: {resp_b_by_a.text}"
        print("  [PASS] Cross-tenant access strictly blocked with 404 (existence masked).", flush=True)
        passed += 1

        # -------------------------------------------------------------
        # TEST C: User A exports User B blueprint -> DENIED (404)
        # -------------------------------------------------------------
        print("\n[TEST C] User A attempting to export User B's blueprint...", flush=True)
        app.dependency_overrides[get_current_user] = lambda: USER_A
        resp_export_by_a = client.get(f"/api/history/{bp_b_id}/export")
        assert resp_export_by_a.status_code == 404, f"Expected 404 Not Found, got {resp_export_by_a.status_code}: {resp_export_by_a.text}"
        print("  [PASS] Cross-tenant export strictly blocked with 404.", flush=True)
        passed += 1

        # -------------------------------------------------------------
        # TEST D: Unauthenticated request -> DENIED (401/403)
        # -------------------------------------------------------------
        print("\n[TEST D] Unauthenticated request to history endpoint...", flush=True)
        app.dependency_overrides.pop(get_current_user, None)
        resp_unauth = client.get(f"/api/history/{bp_a_id}")
        assert resp_unauth.status_code in (401, 403), f"Expected 401/403, got {resp_unauth.status_code}: {resp_unauth.text}"
        print("  [PASS] Unauthenticated request rejected by auth middleware.", flush=True)
        passed += 1

        # -------------------------------------------------------------
        # TEST E: User B requests User B blueprint -> PASS
        # -------------------------------------------------------------
        print("\n[TEST E] User B requesting User B's own blueprint...", flush=True)
        app.dependency_overrides[get_current_user] = lambda: USER_B
        resp_b = client.get(f"/api/history/{bp_b_id}")
        assert resp_b.status_code == 200, f"Expected 200, got {resp_b.status_code}: {resp_b.text}"
        data_b = resp_b.json()
        assert data_b["id"] == bp_b_id
        assert data_b["user_email"] == USER_B["email"]
        print("  [PASS] User B successfully accessed own blueprint.", flush=True)
        passed += 1

    finally:
        app.dependency_overrides.pop(get_current_user, None)
        cleanup_test_blueprints(bp_a_id, bp_b_id)

    print("\n" + "=" * 70, flush=True)
    print(f"HISTORY AUTH TEST RESULT: {passed} / {total} TESTS PASSED", flush=True)
    print("=" * 70, flush=True)
    return passed == total


if __name__ == "__main__":
    success = run_auth_tests()
    sys.exit(0 if success else 1)
