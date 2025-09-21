from celery import Celery
from .settings import settings

# Create Celery instance
celery_app = Celery(
    "scheduler",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.app.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_reject_on_worker_lost=True,
    result_expires=3600,  # 1 hour
)

# Beat schedule configuration
celery_app.conf.beat_schedule = {
    "poll-due-jobs": {
        "task": "src.app.tasks.poll_due_jobs",
        "schedule": 10.0,  # Run every 10 seconds
    },
}

celery_app.conf.timezone = "UTC"
