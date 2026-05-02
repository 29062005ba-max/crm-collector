"""Notification dispatch tasks (separate queue for fast bell-icon responsiveness)"""
import asyncio
import logging
from celery import shared_task
from app.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.tasks._async_helper import track_job

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.notifications.send_notification",
    queue="notification_queue",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    acks_late=True,
)
@track_job(task_name="send_notification", queue="notification_queue")
def send_notification(self, user_id: int, type: str, title: str,
                      message: str = None, link: str = None,
                      debtor_id: int = None, task_id: int = None,
                      company_id: int = None,
                      idempotency_key: str = None):
    """Создать уведомление с защитой от дублей через idempotency_key"""
    return asyncio.run(_create_notif(
        user_id, type, title, message, link, debtor_id, task_id, company_id, idempotency_key
    ))


async def _create_notif(user_id, type, title, message, link, debtor_id, task_id, company_id, idempotency_key):
    from app.services.saas import NotificationService
    from app.models.enterprise import IdempotencyKey
    from datetime import datetime, timedelta
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        try:
            # Idempotency check
            if idempotency_key:
                existing = await db.execute(
                    select(IdempotencyKey).where(IdempotencyKey.key == idempotency_key)
                )
                if existing.scalar_one_or_none():
                    logger.info(f"Notification skipped (idempotent): {idempotency_key}")
                    return {"skipped": True, "reason": "idempotent"}

            svc = NotificationService(db, company_id=company_id)
            notif = await svc.create(
                user_id=user_id, type=type, title=title, message=message,
                link=link, debtor_id=debtor_id, task_id=task_id, company_id=company_id,
            )

            if idempotency_key:
                db.add(IdempotencyKey(
                    key=idempotency_key,
                    endpoint="notifications.send",
                    user_id=user_id,
                    company_id=company_id,
                    request_hash=idempotency_key[:64],
                    response_status=200,
                    response_body={"notification_id": notif.id},
                    expires_at=datetime.utcnow() + timedelta(days=1),
                ))

            await db.commit()
            return {"notification_id": notif.id}
        except Exception:
            await db.rollback()
            raise
