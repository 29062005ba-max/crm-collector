"""
KPI snapshots Celery task — пересчёт каждый час.
Записывает в manager_kpi_snapshots для всех компаний.
"""
import asyncio
import logging
from sqlalchemy import select
from app.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.tasks._async_helper import track_job
from app.models.company import Company
from app.services.kpi_snapshot import KpiSnapshotService

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.kpi_snapshot.recalc_company_snapshots",
    queue="kpi_queue",
    autoretry_for=(Exception,),
    max_retries=2,
)
@track_job(task_name="recalc_company_snapshots", queue="kpi_queue")
def recalc_company_snapshots(self, company_id: int):
    return asyncio.run(_recalc(company_id))


async def _recalc(company_id: int) -> dict:
    async with AsyncSessionLocal() as db:
        svc = KpiSnapshotService(db, company_id=company_id)
        result = await svc.recalculate()
        logger.info(f"[kpi-snapshot] company={company_id} {result}")
        return {"company_id": company_id, **result}


@celery_app.task(
    name="app.tasks.kpi_snapshot.recalc_all_companies",
    queue="kpi_queue",
)
def recalc_all_companies_snapshots():
    return asyncio.run(_fanout())


async def _fanout():
    async with AsyncSessionLocal() as db:
        ids = list((await db.execute(
            select(Company.id).where(Company.is_active == True)
        )).scalars().all())
    for cid in ids:
        recalc_company_snapshots.delay(cid)
    return {"companies_scheduled": len(ids)}
