"""Scoring recalculation Celery task — runs daily."""
import asyncio
import logging
from sqlalchemy import select
from app.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.tasks._async_helper import track_job
from app.models.company import Company
from app.services.scoring import ScoringService

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.scoring.recalculate_company_scoring",
    queue="kpi_queue",
    autoretry_for=(Exception,),
    max_retries=2,
)
@track_job(task_name="recalculate_company_scoring", queue="kpi_queue")
def recalculate_company_scoring(self, company_id: int):
    return asyncio.run(_recalc(company_id))


async def _recalc(company_id: int) -> dict:
    async with AsyncSessionLocal() as db:
        svc = ScoringService(db, company_id=company_id)
        result = await svc.recalculate_all()
        logger.info(f"[scoring] company={company_id} updated={result['updated']}")
        return {"company_id": company_id, **result}


@celery_app.task(
    name="app.tasks.scoring.recalculate_all_companies_scoring",
    queue="kpi_queue",
)
def recalculate_all_companies_scoring():
    return asyncio.run(_fanout())


async def _fanout():
    async with AsyncSessionLocal() as db:
        ids = list((await db.execute(
            select(Company.id).where(Company.is_active == True)
        )).scalars().all())
    for cid in ids:
        recalculate_company_scoring.delay(cid)
    return {"companies_scheduled": len(ids)}
