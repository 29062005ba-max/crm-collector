"""Event processing: async handlers, idempotency cleanup"""
import asyncio
import logging
from datetime import datetime, timedelta
from app.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.tasks._async_helper import track_job

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.events.process_pending_events",
    queue="workflow_queue",
)
def process_pending_events():
    """Catch-up для unprocessed events (если sync handlers упали)"""
    return asyncio.run(_catchup())


async def _catchup() -> dict:
    from sqlalchemy import select
    from app.models.enterprise import EventLog

    async with AsyncSessionLocal() as db:
        # Find unprocessed events older than 1 minute (give sync handlers a chance)
        cutoff = datetime.utcnow() - timedelta(minutes=1)
        q = select(EventLog).where(
            EventLog.processed == False,
            EventLog.created_at < cutoff,
        ).limit(100)
        events = (await db.execute(q)).scalars().all()
        processed = 0
        for e in events:
            try:
                await _process_event_async(e.id)
                processed += 1
            except Exception as ex:
                logger.exception(f"Failed to process event {e.id}: {ex}")
        return {"processed": processed, "found": len(events)}


async def _process_event_async(event_log_id: int) -> dict:
    """Process async handlers for a single event"""
    from app.models.enterprise import EventLog
    async with AsyncSessionLocal() as db:
        event_log = await db.get(EventLog, event_log_id)
        if not event_log:
            return {"error": "event not found"}
        if event_log.processed:
            return {"skipped": True, "reason": "already processed"}

        # Async handlers can be added here per event type
        # For now: just mark as processed
        event_log.processed = True
        event_log.processed_at = datetime.utcnow()
        await db.commit()
        return {"event_id": event_log_id, "ok": True}


@celery_app.task(
    name="app.tasks.events.cleanup_expired_idempotency_keys",
    queue="default",
)
def cleanup_expired_idempotency_keys():
    return asyncio.run(_cleanup())


async def _cleanup() -> dict:
    from sqlalchemy import delete as sql_delete
    from app.models.enterprise import IdempotencyKey

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                sql_delete(IdempotencyKey).where(IdempotencyKey.expires_at < datetime.utcnow())
            )
            await db.commit()
            logger.info(f"Cleaned up {result.rowcount} expired idempotency keys")
            return {"deleted": result.rowcount}
        except Exception:
            await db.rollback()
            raise



@celery_app.task(
    name="app.tasks.events.handle_dead_letter",
    queue="dead_letter_queue",
)
def handle_dead_letter(original_task_id: str, task_name: str, error: str):
    """Dead letter queue handler — alert admins, log persistently"""
    logger.error(f"[DLQ] {task_name} ({original_task_id}): {error}")
    # TODO: send email/Slack to admins
    return {"acknowledged": True, "task_id": original_task_id}
