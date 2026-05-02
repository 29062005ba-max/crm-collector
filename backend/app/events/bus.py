"""Event Bus: regsiter handlers, dispatch events, persist to event_log"""
import logging
from typing import Callable, Awaitable
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from app.events.types import DomainEvent
from app.models.enterprise import EventLog

logger = logging.getLogger(__name__)

# Handler signature: async (event, db_session, **ctx) -> dict
EventHandler = Callable[..., Awaitable[dict | None]]


class EventBus:
    """In-process event bus + persistent event log.

    Handlers are sync (in-process) AND a Celery task is enqueued for async processing.
    Critical bg jobs (notifications, KPI recalc) — through Celery.
    """
    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed handler {handler.__name__} to event {event_type}")

    def on(self, event_type: str):
        """Decorator for subscribing"""
        def decorator(func: EventHandler) -> EventHandler:
            self.subscribe(event_type, func)
            return func
        return decorator

    async def publish(self, event: DomainEvent, db: AsyncSession,
                      run_sync_handlers: bool = True,
                      enqueue_async: bool = True) -> EventLog:
        """Publish event:
        1. Persist to event_log
        2. Run sync handlers immediately (within same DB transaction)
        3. Enqueue Celery task for async handlers (notifications, etc)
        """
        # Persist
        log = EventLog(
            event_type=event.event_type,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            company_id=event.company_id,
            actor_id=event.actor_id,
            payload=event.payload,
            correlation_id=event.correlation_id,
            idempotency_key=event.idempotency_key,
        )
        db.add(log)
        await db.flush()

        # Run sync handlers
        results = {}
        if run_sync_handlers:
            handlers = self._handlers.get(event.event_type, [])
            for h in handlers:
                try:
                    r = await h(event, db)
                    results[h.__name__] = {"ok": True, "result": r}
                except Exception as e:
                    logger.exception(f"Sync handler {h.__name__} failed for {event.event_type}: {e}")
                    results[h.__name__] = {"ok": False, "error": str(e)}

        # Enqueue async dispatch via Celery
        if enqueue_async:
            try:
                from app.celery_app import dispatch_event_async
                dispatch_event_async.delay(log.id)
            except Exception as e:
                logger.warning(f"Failed to enqueue async dispatch for event {log.id}: {e}")

        log.handler_results = results
        log.processed = bool(results)
        if results:
            from datetime import datetime
            log.processed_at = datetime.utcnow()

        return log


# Global singleton
event_bus = EventBus()
