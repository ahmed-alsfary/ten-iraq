"""In-process hourly crawl scheduler (no Redis required for local runs)."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger("uvicorn.error")

_scheduler_task: Optional[asyncio.Task] = None


async def _crawl_loop(interval_seconds: int, initial_delay_seconds: int) -> None:
    from app.worker.tasks import crawl_all_active_sources

    try:
        if initial_delay_seconds > 0:
            await asyncio.sleep(initial_delay_seconds)
        while True:
            logger.info("Starting scheduled crawl of all active sources")
            try:
                result = await asyncio.to_thread(crawl_all_active_sources)
                logger.info(
                    "Scheduled crawl finished: sources=%s created=%s updated=%s",
                    result.get("sources"),
                    result.get("created"),
                    result.get("updated"),
                )
            except Exception:  # noqa: BLE001
                logger.exception("Scheduled crawl failed")
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logger.info("Crawl scheduler stopped")
        raise


def start_crawl_scheduler() -> None:
    global _scheduler_task
    settings = get_settings()
    if not settings.crawl_scheduler_enabled:
        logger.info("In-process crawl scheduler disabled")
        return
    if _scheduler_task and not _scheduler_task.done():
        return

    interval = max(60, int(settings.crawl_interval_minutes) * 60)
    initial_delay = max(0, int(settings.crawl_scheduler_initial_delay_seconds))
    _scheduler_task = asyncio.create_task(
        _crawl_loop(interval, initial_delay),
        name="tenderiq-crawl-scheduler",
    )
    logger.info(
        "Crawl scheduler started: every %s minutes (first run in %ss)",
        settings.crawl_interval_minutes,
        initial_delay,
    )


async def stop_crawl_scheduler() -> None:
    global _scheduler_task
    task = _scheduler_task
    _scheduler_task = None
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
