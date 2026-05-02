"""Prometheus-compatible /metrics endpoint"""
from fastapi import APIRouter, Response, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.core.deps import get_db
from app.models.enterprise import BackgroundJob, EventLog
from app.models import Company

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_class=Response)
async def prometheus_metrics(db: AsyncSession = Depends(get_db)):
    """Prometheus exposition format. Public endpoint (firewall it in prod)."""
    lines = []

    # ==================== App info ====================
    lines.append('# HELP crm_app_info Application info')
    lines.append('# TYPE crm_app_info gauge')
    lines.append('crm_app_info{app="crm-collector"} 1')

    # ==================== Companies ====================
    total_companies = (await db.execute(select(func.count(Company.id)))).scalar() or 0
    active_companies = (await db.execute(
        select(func.count(Company.id)).where(Company.is_active == True)
    )).scalar() or 0
    lines.append('# HELP crm_companies_total Total number of tenants')
    lines.append('# TYPE crm_companies_total gauge')
    lines.append(f'crm_companies_total {total_companies}')
    lines.append(f'crm_companies_active {active_companies}')

    # ==================== Celery jobs (last hour) ====================
    cutoff = datetime.utcnow() - timedelta(hours=1)
    job_q = select(
        BackgroundJob.queue,
        BackgroundJob.status,
        func.count(BackgroundJob.id),
    ).where(BackgroundJob.created_at >= cutoff) \
     .group_by(BackgroundJob.queue, BackgroundJob.status)
    rows = (await db.execute(job_q)).all()

    lines.append('# HELP crm_celery_jobs_1h Celery jobs in last hour by queue and status')
    lines.append('# TYPE crm_celery_jobs_1h gauge')
    for queue, status, count in rows:
        lines.append(f'crm_celery_jobs_1h{{queue="{queue}",status="{status}"}} {count}')

    # ==================== Events ====================
    unprocessed = (await db.execute(
        select(func.count(EventLog.id)).where(EventLog.processed == False)
    )).scalar() or 0
    lines.append('# HELP crm_events_unprocessed Unprocessed domain events')
    lines.append('# TYPE crm_events_unprocessed gauge')
    lines.append(f'crm_events_unprocessed {unprocessed}')

    return Response(content="\n".join(lines) + "\n", media_type="text/plain; charset=utf-8")
