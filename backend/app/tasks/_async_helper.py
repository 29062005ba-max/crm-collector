"""Helper to run async code inside sync Celery tasks"""
import asyncio
import logging
from functools import wraps
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


def async_task(func: Callable[..., Awaitable]):
    """Decorator: wraps async function so it can be called from sync Celery task"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper


def track_job(task_name: str, queue: str):
    """Decorator: track task execution in background_jobs table"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # self is Celery's bound task (when @celery_app.task(bind=True))
            from datetime import datetime
            from app.db.session import SessionLocal  # sync session for tracking
            from app.models.enterprise import BackgroundJob
            task_id = self.request.id if hasattr(self, "request") else "unknown"
            attempt = (self.request.retries + 1) if hasattr(self, "request") else 1

            try:
                with SessionLocal() as db:
                    job = db.query(BackgroundJob).filter(BackgroundJob.task_id == task_id).first()
                    if not job:
                        job = BackgroundJob(
                            task_id=task_id,
                            task_name=task_name,
                            queue=queue,
                            args={"args": list(args), "kwargs": kwargs},
                            attempt=attempt,
                            started_at=datetime.utcnow(),
                            status="running",
                        )
                        db.add(job)
                    else:
                        job.attempt = attempt
                        job.started_at = datetime.utcnow()
                        job.status = "running"
                    db.commit()
            except Exception as e:
                logger.warning(f"Failed to track job start: {e}")

            try:
                result = func(self, *args, **kwargs)
                # Mark success
                try:
                    with SessionLocal() as db:
                        job = db.query(BackgroundJob).filter(BackgroundJob.task_id == task_id).first()
                        if job:
                            job.status = "success"
                            job.completed_at = datetime.utcnow()
                            job.result = result if isinstance(result, dict) else {"value": result}
                            db.commit()
                except Exception as e:
                    logger.warning(f"Failed to track job success: {e}")
                return result
            except Exception as e:
                logger.exception(f"Task {task_name} failed: {e}")
                try:
                    with SessionLocal() as db:
                        job = db.query(BackgroundJob).filter(BackgroundJob.task_id == task_id).first()
                        if job:
                            job.status = "failed"
                            job.error = str(e)
                            job.completed_at = datetime.utcnow()
                            db.commit()
                except Exception:
                    pass
                raise
        return wrapper
    return decorator
