"""Scheduled monitoring task for CURE pillar.

This task is intended to run on a cron scheduler. It compares latest
heartbeats against expected offline windows and triggers alerts.
"""

import logging

from app.services.heartbeat_monitor import run_watchdog_cycle

logger = logging.getLogger("watchdog")


def run_watchdog_task() -> dict:
    """Run the watchdog cycle used by APScheduler or internal triggers."""
    logger.info("[watchdog-task] run_requested")
    result = run_watchdog_cycle()
    logger.info(
        "[watchdog-task] run_completed evaluated_at=%s result_count=%s alerts_created=%s",
        result.get("evaluated_at"),
        result.get("result_count"),
        result.get("alerts_created_count", 0),
    )
    return result
