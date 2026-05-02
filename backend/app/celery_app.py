"""Celery configuration: broker, queues, beat schedule, task definitions"""
import os
import logging
from celery import Celery
from celery.schedules import crontab
from kombu import Queue

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)


celery_app = Celery(
    "crm_collector",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        "app.tasks.workflow",
        "app.tasks.notifications",
        "app.tasks.schedules",
        "app.tasks.kpi",
        "app.tasks.events",
        "app.tasks.scoring",  # <-- NEW: scoring recalculation
        "app.tasks.kpi_snapshot",  # <-- NEW v3: KPI snapshots for control panel
        "app.events.handlers",
    ],
)

# ==================== Configuration ====================
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,

    task_default_retry_delay=60,
    task_default_max_retries=5,

    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Almaty",
    enable_utc=True,

    result_expires=3600 * 24,

    task_routes={
        "app.tasks.workflow.*":      {"queue": "workflow_queue"},
        "app.tasks.notifications.*": {"queue": "notification_queue"},
        "app.tasks.schedules.*":     {"queue": "schedule_queue"},
        "app.tasks.kpi.*":           {"queue": "kpi_queue"},
        "app.tasks.events.*":        {"queue": "workflow_queue"},
        "app.tasks.scoring.*":       {"queue": "kpi_queue"},  # <-- NEW
        "app.tasks.kpi_snapshot.*":  {"queue": "kpi_queue"},  # <-- NEW v3
    },

    task_queues=(
        Queue("workflow_queue",     routing_key="workflow_queue"),
        Queue("notification_queue", routing_key="notification_queue"),
        Queue("schedule_queue",     routing_key="schedule_queue"),
        Queue("kpi_queue",          routing_key="kpi_queue"),
        Queue("default",            routing_key="default"),
        Queue("dead_letter_queue",  routing_key="dead_letter_queue"),
    ),
    task_default_queue="default",
)


# ==================== Beat Schedule ====================
celery_app.conf.beat_schedule = {
    "process-overdue-promises": {
        "task": "app.tasks.workflow.process_overdue_promises_all_companies",
        "schedule": crontab(minute=0),
        "options": {"queue": "workflow_queue"},
    },
    "process-overdue-schedules": {
        "task": "app.tasks.workflow.process_overdue_schedules_all_companies",
        "schedule": crontab(minute=5),
        "options": {"queue": "schedule_queue"},
    },
    "recalculate-daily-kpi": {
        "task": "app.tasks.kpi.recalculate_all_companies_kpi",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "kpi_queue"},
    },
    # === NEW: Daily scoring recalculation (3:30 AM) ===
    "recalculate-daily-scoring": {
        "task": "app.tasks.scoring.recalculate_all_companies_scoring",
        "schedule": crontab(hour=3, minute=30),
        "options": {"queue": "kpi_queue"},
    },
    # === NEW v3: Hourly KPI snapshots for control panel ===
    "recalculate-hourly-kpi-snapshots": {
        "task": "app.tasks.kpi_snapshot.recalc_all_companies",
        "schedule": crontab(minute=15),  # каждый час в :15
        "options": {"queue": "kpi_queue"},
    },
    "process-pending-events": {
        "task": "app.tasks.events.process_pending_events",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "workflow_queue"},
    },
    "cleanup-idempotency-keys": {
        "task": "app.tasks.events.cleanup_expired_idempotency_keys",
        "schedule": crontab(hour=4, minute=0),
        "options": {"queue": "default"},
    },
}


@celery_app.task(name="app.events.dispatch_event_async", queue="workflow_queue")
def dispatch_event_async(event_log_id: int):
    import asyncio
    from app.tasks.events import _process_event_async
    return asyncio.run(_process_event_async(event_log_id))


# ==================== Sentry Integration (optional) ====================
import os as _os
try:
    if _os.getenv("SENTRY_DSN"):
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        sentry_sdk.init(
            dsn=_os.getenv("SENTRY_DSN"),
            integrations=[CeleryIntegration()],
            traces_sample_rate=0.1,
            environment=_os.getenv("ENVIRONMENT", "production"),
        )
        logger.info("Sentry initialized for Celery")
except Exception as _e:
    logger.warning(f"Sentry init skipped: {_e}")


# ==================== Failure handler — Dead Letter Queue ====================
from celery.signals import task_failure


@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, args=None,
                         kwargs=None, traceback=None, einfo=None, **_):
    try:
        if sender and hasattr(sender, "request"):
            retries = sender.request.retries
            max_retries = sender.max_retries or 0
            if retries < max_retries:
                return

        from app.db.session import SessionLocal
        from app.models.enterprise import BackgroundJob
        from datetime import datetime

        with SessionLocal() as db:
            job = db.query(BackgroundJob).filter(BackgroundJob.task_id == task_id).first()
            if job:
                job.status = "dead_letter"
                job.error = str(exception)[:5000]
                job.completed_at = datetime.utcnow()
                db.commit()
                logger.error(f"DLQ: task {task_id} ({sender.name if sender else 'unknown'}) failed permanently: {exception}")

        try:
            celery_app.send_task(
                "app.tasks.events.handle_dead_letter",
                args=[task_id, str(sender.name) if sender else None, str(exception)],
                queue="dead_letter_queue",
            )
        except Exception:
            pass
    except Exception as e:
        logger.exception(f"Failure handler crashed: {e}")
