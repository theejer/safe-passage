"""Scheduled monitoring task for CURE pillar.

This task is intended to run on a cron scheduler. It compares latest
heartbeats against expected offline windows and triggers alerts.
"""

from app.services.heartbeat_monitor import run_watchdog_cycle


def run_watchdog_task() -> dict:
    """Run the watchdog cycle used by APScheduler or internal triggers."""
    return run_watchdog_cycle()
