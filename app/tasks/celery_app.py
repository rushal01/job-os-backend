from celery import Celery

from app.config import settings

celery_app = Celery(
    "job_application_os",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_default_retry_delay=30,
    task_max_retries=3,
)

celery_app.conf.beat_schedule = {
    "discover-jobs-every-6-hours": {
        "task": "scheduled.run_all_discoveries",
        "schedule": 6 * 3600,  # every 6 hours
    },
    "score-new-jobs-every-hour": {
        "task": "scheduled.auto_score_new_jobs",
        "schedule": 3600,  # every hour
    },
    "cleanup-notifications-daily": {
        "task": "scheduled.cleanup_old_notifications",
        "schedule": 86400,  # daily
    },
    "expire-stale-jobs-daily": {
        "task": "scheduled.expire_stale_jobs",
        "schedule": 86400,  # daily
    },
}

celery_app.autodiscover_tasks(
    [
        "app.tasks.discovery_tasks",
        "app.tasks.scoring_tasks",
        "app.tasks.content_tasks",
        "app.tasks.application_tasks",
        "app.tasks.outreach_tasks",
        "app.tasks.email_tasks",
        "app.tasks.analytics_tasks",
        "app.tasks.market_tasks",
        "app.tasks.scheduled_tasks",
    ]
)
