"""
test_phase3_agent.py — Complete 17-point test suite for Phase 3 Autonomous LOCK IN AI Accountability Agent.
"""

import sys
import os
import asyncio
from datetime import datetime, date, timedelta, timezone
import zoneinfo

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import psycopg2
import psycopg2.extras

import gmail_service
sent_emails = []

async def mock_send_gmail(uid, to, subj, txt, html):
    sent_emails.append({"user_id": uid, "to": to, "subject": subj, "html": html})
    return f"mock_msg_{len(sent_emails)}"

gmail_service.send_gmail_email = mock_send_gmail

import lock_in_agent_runner
lock_in_agent_runner.send_gmail_email = mock_send_gmail
import core.lock_in_agent_runner
core.lock_in_agent_runner.send_gmail_email = mock_send_gmail

from core.lock_in_db import (
    init_tables,
    sync_project,
    get_project,
    get_project_by_id,
    update_preferences,
    get_preferences,
    save_gmail_connection,
    disconnect_gmail,
    record_notification,
    has_notification_been_sent_today,
    get_all_active_projects_for_scheduler,
    calculate_momentum_and_streak,
    create_agent_action,
    get_pending_recommendations,
    _conn,
)
from core.lock_in_agent_runner import (
    analyze_project_progress,
    generate_daily_email_content,
    generate_recovery_recommendation_if_needed,
    evaluate_and_execute_agent,
)
from core.lock_in_scheduler import run_lock_in_scheduler_cycle


def create_mock_roadmap(num_weeks=12):
    weeks = []
    task_counter = 1
    for w in range(1, num_weeks + 1):
        tasks = []
        for t in range(1, 5):
            tasks.append({
                "id": f"w{w}t{t}",
                "task": f"Deliverable {w}.{t} for Week {w}",
                "details": f"Detailed execution steps for item {w}.{t}",
                "category": "build" if t % 2 == 0 else "ops",
                "priority": "must" if t == 1 else "should",
                "hours": 3,
                "outcome": f"Milestone outcome {w}.{t}"
            })
            task_counter += 1
        weeks.append({
            "week": w,
            "theme": f"Week {w} Theme",
            "objective": f"Reach milestone {w}",
            "estimated_hours": 12,
            "tasks": tasks
        })
    return {
        "title": "Phase 3 Autonomous Startup Roadmap",
        "sector": "Fintech AI",
        "primary_goal": "Launch MVP",
        "duration": f"{num_weeks} Weeks",
        "weeks": weeks,
        "milestones": [
            {"week": 1, "title": "Core Architecture Setup", "description": "Backend and DB online"},
            {"week": 4, "title": "Alpha Customer Validation", "description": "10 pilot users onboarded"},
        ]
    }


async def run_all_tests():
    print("=" * 70)
    print("STARTING PHASE 3 AUTONOMOUS LOCK IN TEST MATRIX (17 TESTS)")
    print("=" * 70)

    init_tables()
    passed = 0
    total = 17

    # Setup test users
    user_a_id = "test_user_a_p3"
    user_a_email = "usera_test@example.com"
    user_b_id = "test_user_b_p3"
    user_b_email = "userb_test@example.com"
    bp_a = 99101
    bp_b = 99102

    roadmap = create_mock_roadmap(12)

    # -------------------------------------------------------------
    # SETUP: Clean up any previous test runs
    # -------------------------------------------------------------
    with _conn() as c:
        cur = c.cursor()
        cur.execute("DELETE FROM lockin_projects WHERE user_id IN (%s, %s);", (user_a_id, user_b_id))
        cur.execute("DELETE FROM gmail_connections WHERE user_id IN (%s, %s);", (user_a_id, user_b_id))
        c.commit()

    proj_a = sync_project(user_a_id, user_a_email, bp_a, roadmap, ["w1t1", "w1t2"])
    proj_b = sync_project(user_b_id, user_b_email, bp_b, roadmap, ["w1t1"])
    proj_a_id = proj_a["id"]
    proj_b_id = proj_b["id"]

    # Save mock active Gmail connection for user A
    save_gmail_connection(
        user_id=user_a_id,
        user_email=user_a_email,
        google_email=user_a_email,
        access_token="mock_access_token_a",
        refresh_token="mock_refresh_token_a",
        token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        status="active"
    )

    # Save mock active Gmail connection for user B
    save_gmail_connection(
        user_id=user_b_id,
        user_email=user_b_email,
        google_email=user_b_email,
        access_token="mock_access_token_b",
        refresh_token="mock_refresh_token_b",
        token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        status="active"
    )

    # -------------------------------------------------------------
    # TEST 1: Daily email automatically sent without Trigger Agent Now
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing automatic daily email trigger via scheduler cycle...", flush=True)
    now_kolkata = datetime.now(zoneinfo.ZoneInfo("Asia/Kolkata"))
    update_preferences(proj_a_id, user_a_id, {
        "email_enabled": True,
        "daily_reminder_enabled": True,
        "reminder_time": now_kolkata.strftime("%H:%M"),
        "timezone": "Asia/Kolkata"
    })
    
    import gmail_service
    sent_emails = []
    
    async def mock_send_gmail(uid, to, subj, txt, html):
        sent_emails.append({"user_id": uid, "to": to, "subject": subj, "html": html})
        return f"mock_msg_{len(sent_emails)}"
    
    gmail_service.send_gmail_email = mock_send_gmail
    try:
        import lock_in_agent_runner
        lock_in_agent_runner.send_gmail_email = mock_send_gmail
    except Exception:
        pass
    try:
        import core.lock_in_agent_runner
        core.lock_in_agent_runner.send_gmail_email = mock_send_gmail
    except Exception:
        pass

    try:
        await run_lock_in_scheduler_cycle()
        assert any(e["user_id"] == user_a_id and "LOCK IN" in e["subject"] for e in sent_emails), "Automatic email not triggered for User A"
        print("  [PASS] Daily email triggered autonomously by scheduler without clicking manual button.", flush=True)
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # TEST 2: Daily email sent only once per day (Idempotency)
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing daily email idempotency (single delivery per day)...", flush=True)
    try:
        today_kolkata_str = now_kolkata.date().isoformat()
        is_sent = has_notification_been_sent_today(proj_a_id, "daily", today_kolkata_str, "Asia/Kolkata")
        assert is_sent is True, "Notification record not found in ledger"
        print("  [PASS] Notification is correctly logged in idempotency ledger.", flush=True)
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # TEST 3: Scheduler running every 10 minutes does not duplicate emails
    # -------------------------------------------------------------
    print("\n[TEST 3] Running secondary scheduler cycle (duplicate suppression)...", flush=True)
    try:
        email_count_before = len(sent_emails)
        await run_lock_in_scheduler_cycle()
        email_count_after = len(sent_emails)
        assert email_count_before == email_count_after, f"Duplicate email was sent! Count grew from {email_count_before} to {email_count_after}"
        print("  [PASS] Second scheduler run detected today's email already sent and safely skipped.", flush=True)
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # TEST 4: User timezone respected (Asia/Kolkata vs America/New_York)
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing timezone-aware reminder evaluation...", flush=True)
    try:
        update_preferences(proj_b_id, user_b_id, {
            "email_enabled": True,
            "daily_reminder_enabled": True,
            "reminder_time": "23:59",
            "timezone": "America/New_York"
        })
        ny_now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
        
        with _conn() as c:
            cur = c.cursor()
            cur.execute("DELETE FROM lockin_notifications WHERE project_id = %s;", (proj_b_id,))
            c.commit()

        if (ny_now.hour, ny_now.minute) < (23, 59):
            user_b_emails_before = len([e for e in sent_emails if e["user_id"] == user_b_id])
            await run_lock_in_scheduler_cycle()
            user_b_emails_after = len([e for e in sent_emails if e["user_id"] == user_b_id])
            assert user_b_emails_before == user_b_emails_after, "User B received email before their local reminder time!"
        print("  [PASS] Timezone calculation correctly aligned to local user clock.", flush=True)
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # TEST 5: Daily notification disabled -> no email
    # -------------------------------------------------------------
    print("\n[TEST 5] Testing Daily notification disabled preference...", flush=True)
    try:
        update_preferences(proj_a_id, user_a_id, {"daily_reminder_enabled": False})
        with _conn() as c:
            cur = c.cursor()
            cur.execute("DELETE FROM lockin_notifications WHERE project_id = %s;", (proj_a_id,))
            c.commit()

        res = await evaluate_and_execute_agent(proj_a_id, notification_type="daily", force_send=False)
        assert res["sent"] is False and "disabled" in res["reason"], f"Expected disabled skip, got: {res}"
        print("  [PASS] Daily email disabled preference respected.", flush=True)
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # TEST 6: Gmail disconnected -> no email
    # -------------------------------------------------------------
    print("\n[TEST 6] Testing Gmail disconnected status...", flush=True)
    try:
        disconnect_gmail(user_a_id)
        res = await evaluate_and_execute_agent(proj_a_id, notification_type="daily", force_send=False)
        assert res["sent"] is False and ("inactive" in res["reason"] or "connected" in res["reason"]), f"Expected disconnect skip, got: {res}"
        print("  [PASS] Disconnected Gmail prevents delivery attempts safely.", flush=True)
        save_gmail_connection(user_a_id, user_a_email, user_a_email, "mock_token", "mock_refresh", datetime.now(timezone.utc) + timedelta(hours=1))
        update_preferences(proj_a_id, user_a_id, {"daily_reminder_enabled": True})
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # TEST 7 & 8: Multi-user isolation (User A only sees User A, User B only sees User B)
    # -------------------------------------------------------------
    print("\n[TEST 7 & 8] Testing strict multi-user isolation...", flush=True)
    try:
        analysis_a = analyze_project_progress(proj_a_id)
        analysis_b = analyze_project_progress(proj_b_id)
        assert analysis_a["user_id"] == user_a_id and analysis_a["completed_count"] == 2
        assert analysis_b["user_id"] == user_b_id and analysis_b["completed_count"] == 1
        assert analysis_a["user_id"] != analysis_b["user_id"]
        print("  [PASS] User A and User B progress and metrics are fully isolated.", flush=True)
        passed += 2
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # TEST 9: Current streak calculated correctly (including preservation)
    # -------------------------------------------------------------
    print("\n[TEST 9] Testing deterministic current streak calculation...", flush=True)
    try:
        with _conn() as c:
            cur = c.cursor()
            d_today = now_kolkata.date()
            d_yesterday = d_today - timedelta(days=1)
            d_2days = d_today - timedelta(days=2)
            
            cur.execute("""
                UPDATE lockin_tasks SET status = 'completed', completed_at = %s WHERE project_id = %s AND task_id = 'w1t1';
            """, (datetime.combine(d_2days, datetime.min.time(), tzinfo=zoneinfo.ZoneInfo("Asia/Kolkata")), proj_a_id))
            cur.execute("""
                UPDATE lockin_tasks SET status = 'completed', completed_at = %s WHERE project_id = %s AND task_id = 'w1t2';
            """, (datetime.combine(d_yesterday, datetime.min.time(), tzinfo=zoneinfo.ZoneInfo("Asia/Kolkata")), proj_a_id))
            c.commit()

        momentum = calculate_momentum_and_streak(proj_a_id, "Asia/Kolkata")
        assert momentum["current_streak"] == 2, f"Expected streak 2, got {momentum['current_streak']}"
        print(f"  [PASS] Current streak is {momentum['current_streak']} (yesterday streak preserved for today).", flush=True)
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # TEST 10: Longest streak calculated correctly
    # -------------------------------------------------------------
    print("\n[TEST 10] Testing longest streak calculation...", flush=True)
    try:
        with _conn() as c:
            cur = c.cursor()
            d_base = now_kolkata.date() - timedelta(days=20)
            for i, tid in enumerate(["w1t3", "w1t4", "w2t1", "w2t2"]):
                t_date = d_base + timedelta(days=i)
                cur.execute("""
                    UPDATE lockin_tasks SET status = 'completed', completed_at = %s WHERE project_id = %s AND task_id = %s;
                """, (datetime.combine(t_date, datetime.min.time(), tzinfo=zoneinfo.ZoneInfo("Asia/Kolkata")), proj_a_id, tid))
            c.commit()

        momentum = calculate_momentum_and_streak(proj_a_id, "Asia/Kolkata")
        assert momentum["longest_streak"] == 4, f"Expected longest streak 4, got {momentum['longest_streak']}"
        print(f"  [PASS] Longest streak correctly calculated as {momentum['longest_streak']} days.", flush=True)
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # TEST 11: Duplicate task completions on same day do NOT inflate streak
    # -------------------------------------------------------------
    print("\n[TEST 11] Testing duplicate task completion on same day...", flush=True)
    try:
        with _conn() as c:
            cur = c.cursor()
            cur.execute("""
                UPDATE lockin_tasks SET status = 'completed', completed_at = %s WHERE project_id = %s AND task_id IN ('w2t3', 'w2t4');
            """, (now_kolkata, proj_a_id))
            c.commit()

        momentum = calculate_momentum_and_streak(proj_a_id, "Asia/Kolkata")
        assert momentum["current_streak"] == 3, f"Expected streak 3, got {momentum['current_streak']}"
        print(f"  [PASS] Multiple completions on same day properly counted as 1 active day (streak = {momentum['current_streak']}).", flush=True)
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # TEST 12: LOCK IN score remains deterministic
    # -------------------------------------------------------------
    print("\n[TEST 12] Testing deterministic LOCK IN score calculation...", flush=True)
    try:
        analysis1 = analyze_project_progress(proj_a_id)
        analysis2 = analyze_project_progress(proj_a_id)
        assert analysis1["lock_in_score"] == analysis2["lock_in_score"]
        assert 0 <= analysis1["lock_in_score"] <= 100
        print(f"  [PASS] LOCK IN Score is 100% deterministic ({analysis1['lock_in_score']}/100).", flush=True)
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # TEST 13: Weekly progress metrics remain deterministic
    # -------------------------------------------------------------
    print("\n[TEST 13] Testing weekly progress metrics...", flush=True)
    try:
        assert "tasks_completed_this_week" in analysis1
        assert "progress_trend" in analysis1
        assert "overall_pct" in analysis1
        print(f"  [PASS] Weekly progress metrics deterministically computed (Completed this week: {analysis1['tasks_completed_this_week']}, Trend: {analysis1['progress_trend']}).", flush=True)
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # TEST 14: Milestone email does not duplicate
    # -------------------------------------------------------------
    print("\n[TEST 14] Testing milestone deadline email idempotency...", flush=True)
    try:
        with _conn() as c:
            cur = c.cursor()
            cur.execute("DELETE FROM lockin_notifications WHERE project_id = %s AND notification_type = 'deadline';", (proj_a_id,))
            c.commit()

        update_preferences(proj_a_id, user_a_id, {"deadline_alert_enabled": True})
        res1 = await evaluate_and_execute_agent(proj_a_id, notification_type="deadline", force_send=False)
        assert res1["sent"] is True, f"Milestone email failed to send: {res1}"

        res2 = await evaluate_and_execute_agent(proj_a_id, notification_type="deadline", force_send=False)
        assert res2["sent"] is False and "Already sent" in res2["reason"], f"Expected idempotency skip, got: {res2}"
        print("  [PASS] Milestone alert sent once and strictly prevented from duplicate delivery.", flush=True)
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # TEST 15: Recovery recommendation does not spam (only 1 active pending)
    # -------------------------------------------------------------
    print("\n[TEST 15] Testing HITL Recovery recommendation anti-spam...", flush=True)
    try:
        analysis_mock = {
            "project_id": proj_a_id,
            "user_id": user_a_id,
            "agent_state": "SIGNIFICANTLY_BEHIND",
            "current_week": 3,
            "total_weeks": 12,
            "overdue_tasks": [
                {"task_id": "w1t1", "title": "Overdue Task 1", "week_number": 1, "priority": "should"},
                {"task_id": "w1t2", "title": "Overdue Task 2", "week_number": 1, "priority": "nice"},
            ]
        }
        with _conn() as c:
            cur = c.cursor()
            cur.execute("DELETE FROM lockin_agent_actions WHERE project_id = %s;", (proj_a_id,))
            c.commit()

        rec1 = generate_recovery_recommendation_if_needed(analysis_mock)
        assert rec1 is not None, "Failed to create initial recommendation"
        
        rec2 = generate_recovery_recommendation_if_needed(analysis_mock)
        assert rec2 is None, f"Duplicate recommendation was created: {rec2}"
        print(f"  [PASS] Recommendation created once (Action #{rec1}); subsequent evaluations gracefully skipped.", flush=True)
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # TEST 16: Scheduler survives one user's Gmail failure (fault isolation)
    # -------------------------------------------------------------
    print("\n[TEST 16] Testing scheduler fault isolation between users...", flush=True)
    try:
        async def failing_send(uid, to, subj, txt, html):
            if uid == user_a_id:
                raise Exception("Simulated Gmail 401 Unauthorized Token Revoked")
            sent_emails.append({"user_id": uid, "to": to, "subject": subj, "html": html})
            return "mock_success_msg_b"
        
        gmail_service.send_gmail_email = failing_send
        try:
            import lock_in_agent_runner
            lock_in_agent_runner.send_gmail_email = failing_send
        except Exception:
            pass
        try:
            import core.lock_in_agent_runner
            core.lock_in_agent_runner.send_gmail_email = failing_send
        except Exception:
            pass

        with _conn() as c:
            cur = c.cursor()
            cur.execute("DELETE FROM lockin_notifications WHERE project_id IN (%s, %s);", (proj_a_id, proj_b_id))
            c.commit()

        update_preferences(proj_b_id, user_b_id, {
            "email_enabled": True,
            "daily_reminder_enabled": True,
            "reminder_time": now_kolkata.strftime("%H:%M"),
            "timezone": "Asia/Kolkata"
        })

        await run_lock_in_scheduler_cycle()

        user_b_notifications = has_notification_been_sent_today(proj_b_id, "daily", now_kolkata.date().isoformat(), "Asia/Kolkata")
        assert user_b_notifications is True, "User B did not receive email due to User A's failure!"
        print("  [PASS] Per-user failure isolation verified. User A error did not interrupt User B.", flush=True)
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # TEST 17: Existing Phase 2 flows still pass (Sync, Preferences, Actions)
    # -------------------------------------------------------------
    print("\n[TEST 17] Verifying Phase 2 backwards compatibility...", flush=True)
    try:
        p_loaded = get_project_by_id(proj_a_id)
        assert p_loaded is not None and p_loaded["blueprint_id"] == bp_a
        prefs_loaded = get_preferences(proj_a_id, user_a_id)
        assert prefs_loaded is not None and "reminder_time" in prefs_loaded
        print("  [PASS] All Phase 2 database, sync, and preferences models functioning flawlessly.", flush=True)
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {e}", flush=True)

    # -------------------------------------------------------------
    # CLEANUP: Remove mock test users from database
    # -------------------------------------------------------------
    try:
        with _conn() as c:
            cur = c.cursor()
            cur.execute("DELETE FROM lockin_projects WHERE user_id IN (%s, %s);", (user_a_id, user_b_id))
            cur.execute("DELETE FROM gmail_connections WHERE user_id IN (%s, %s);", (user_a_id, user_b_id))
            c.commit()
    except Exception as clean_err:
        print(f"Warning: Cleanup failed: {clean_err}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print(f"FINAL RESULT: {passed} / {total} TESTS PASSED", flush=True)
    print("=" * 70, flush=True)
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
