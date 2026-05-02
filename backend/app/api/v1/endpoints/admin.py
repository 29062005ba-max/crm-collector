"""Admin endpoints: background jobs monitoring, metrics, system health"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_roles
from app.models.user import User
from app.models.enterprise import BackgroundJob, EventLog, IdempotencyKey

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/jobs")
async def list_jobs(
    status: str | None = Query(None, description="filter by status: pending/running/success/failed"),
    queue: str | None = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """View Celery background jobs (admin only)"""
    q = select(BackgroundJob)
    if status:
        q = q.where(BackgroundJob.status == status)
    if queue:
        q = q.where(BackgroundJob.queue == queue)
    q = q.order_by(desc(BackgroundJob.created_at)).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": j.id,
            "task_id": j.task_id,
            "task_name": j.task_name,
            "queue": j.queue,
            "status": j.status,
            "attempt": j.attempt,
            "company_id": j.company_id,
            "created_at": j.created_at,
            "started_at": j.started_at,
            "completed_at": j.completed_at,
            "error": j.error[:500] if j.error else None,
        }
        for j in rows
    ]


@router.get("/jobs/stats")
async def jobs_stats(
    hours: int = Query(24, le=168),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """Aggregate stats for Celery jobs"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    q = select(
        BackgroundJob.queue,
        BackgroundJob.status,
        func.count(BackgroundJob.id),
    ).where(BackgroundJob.created_at >= cutoff) \
     .group_by(BackgroundJob.queue, BackgroundJob.status)
    rows = (await db.execute(q)).all()
    result = {}
    for queue, status, count in rows:
        result.setdefault(queue, {})[status] = count
    return {"window_hours": hours, "stats": result}


@router.get("/events/recent")
async def recent_events(
    limit: int = Query(100, le=500),
    unprocessed_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """View recent domain events"""
    q = select(EventLog)
    if unprocessed_only:
        q = q.where(EventLog.processed == False)
    q = q.order_by(desc(EventLog.id)).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "aggregate_type": e.aggregate_type,
            "aggregate_id": e.aggregate_id,
            "company_id": e.company_id,
            "actor_id": e.actor_id,
            "processed": e.processed,
            "correlation_id": e.correlation_id,
            "created_at": e.created_at,
        }
        for e in rows
    ]


@router.get("/idempotency-keys/count")
async def idempotency_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """Count active idempotency keys"""
    total = (await db.execute(select(func.count(IdempotencyKey.id)))).scalar()
    active = (await db.execute(
        select(func.count(IdempotencyKey.id))
        .where(IdempotencyKey.expires_at > datetime.utcnow())
    )).scalar()
    return {"total": total or 0, "active": active or 0}
