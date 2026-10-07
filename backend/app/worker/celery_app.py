from celery import Celery
from celery.schedules import schedule

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "tenderiq",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Baghdad",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "crawl-all-sources-hourly": {
            "task": "crawl_all_sources",
            "schedule": schedule(run_every=max(60, settings.crawl_interval_minutes * 60)),
        },
    },
)
