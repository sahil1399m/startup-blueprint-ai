"""
lock_in_scheduler.py — APScheduler background job runner for LOCK IN AI accountability agent.

Features:
  1. Timezone-aware daily reminder matching (per-user browser timezone)
  2. Idempotent email dispatching via lock_in_agent_runner
  3. Per-project exception isolation (one user's failure never crashes the engine)
  4. Safe lifecycle management (startup/shutdown in FastAPI lifespan)
"""

import asyncio
import logging
from datetime import datetime, timezone
import zoneinfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from lock_in_db import get_all_active_projects_for_scheduler, has_notification_been_sent_today
from lock_in_agent_runner import evaluate_and_execute_agent

log = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def run_lock_in_scheduler_cycle():
    """
    Periodic job (runs every 10 minutes):
    Iterates over all active projects, checks timezones, preferences, and schedules.
    """
    log.info("⏰ [LOCK IN Scheduler] Checking active projects for scheduled accountability actions…")
    try:
        active_projects = get_all_active_projects_for_scheduler()
    except Exception as e:
        log.error(f"[LOCK IN Scheduler] Error loading active projects from DB: {e}")
        return

    if not active_projects:
        log.info("⏰ [LOCK IN Scheduler] No active projects with Gmail connections at this time.")
        return

    for proj in active_projects:
        project_id = proj["project_id"]
        user_id = proj["user_id"]
        tz_name = proj.get("timezone") or "Asia/Kolkata"
        reminder_time_str = proj.get("reminder_time") or "09:00"

        try:
            # 1. Determine local time in user's specified timezone
            try:
                user_tz = zoneinfo.ZoneInfo(tz_name)
            except Exception:
                user_tz = zoneinfo.ZoneInfo("UTC")

            local_now = datetime.now(user_tz)
            local_date_str = local_now.date().isoformat()
            local_hour_minute = local_now.strftime("%H:%M")

            # Parse user's desired reminder hour/minute
            target_parts = reminder_time_str.split(":")
            target_hour = int(target_parts[0]) if target_parts else 9
            target_minute = int(target_parts[1]) if len(target_parts) > 1 else 0

            # 2. Daily Accountability Check
            if proj.get("daily_reminder_enabled", True):
                # Trigger if local time has reached or passed target reminder time today
                time_reached = (local_now.hour > target_hour) or (local_now.hour == target_hour and local_now.minute >= target_minute)
                if time_reached:
                    if not has_notification_been_sent_today(project_id, "daily", local_date_str, tz_name):
                        log.info(f"🚀 [LOCK IN Scheduler] Triggering daily agent for project {project_id} (User: {user_id}, Local Time: {local_hour_minute}, TZ: {tz_name})")
                        await evaluate_and_execute_agent(project_id, notification_type="daily", force_send=False)

            # 3. Weekly Report Check (e.g. on Sundays at 18:00 local time)
            if proj.get("weekly_report_enabled", True):
                is_sunday = local_now.weekday() == 6
                is_evening = local_now.hour >= 18
                if is_sunday and is_evening:
                    if not has_notification_been_sent_today(project_id, "weekly", local_date_str, tz_name):
                        log.info(f"📊 [LOCK IN Scheduler] Triggering weekly report for project {project_id}")
                        await evaluate_and_execute_agent(project_id, notification_type="weekly", force_send=False)

            # 4. Milestone & Deadline Alert Check (e.g. evaluated mid-day around 14:00)
            if proj.get("deadline_alert_enabled", True):
                is_midday = local_now.hour == 14
                if is_midday:
                    if not has_notification_been_sent_today(project_id, "deadline", local_date_str, tz_name):
                        log.info(f"⏰ [LOCK IN Scheduler] Evaluating milestone/deadline alert for project {project_id}")
                        await evaluate_and_execute_agent(project_id, notification_type="deadline", force_send=False)

        except Exception as e:
            # Per-project isolation — ensure one error does not abort evaluation of other projects
            log.error(f"[LOCK IN Scheduler] Error processing project {project_id}: {e}", exc_info=True)


def start_scheduler():
    """Starts the APScheduler instance if not already running."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        log.info("LOCK IN Scheduler is already running.")
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        run_lock_in_scheduler_cycle,
        trigger=IntervalTrigger(minutes=10),
        id="lock_in_agent_cycle",
        name="LOCK IN AI Agent Scheduled Cycle",
        replace_existing=True,
    )
    _scheduler.start()
    log.info("✅ LOCK IN AI Background Scheduler started (evaluates every 10 mins).")


def shutdown_scheduler():
    """Gracefully stops the scheduler on server shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("LOCK IN Scheduler shut down.")
        _scheduler = None
