"""KPI recalculation tasks (heavy queries — separate queue to not block other work)"""
import asyncio
import logging
from app.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.tasks._async_helper import track_job

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.kpi.recalculate_company_kpi",
    queue="kpi_queue",
    autoretry_for=(Exception,),
    max_retries=2,
)
@track_job(task_name="recalculate_company_kpi", queue="kpi_queue")
def recalculate_company_kpi(self, company_id: int):
    """Пересчитать KPI для компании и закэшировать в Redis (если решим кэшировать)"""
    return asyncio.run(_recalc(company_id))


async def _recalc(company_id: int) -> dict:
    from app.services.saas import DashboardKPIService
    async with AsyncSessionLocal() as db:
        svc = DashboardKPIService(db, company_id=company_id)
        kpi = await svc.get_dashboard_kpi()
        # TODO: cache in Redis with TTL 5 min
        logger.info(f"[kpi] company={company_id} recalculated")
        return {"company_id": company_id, "ok": True}


@celery_app.task(
    name="app.tasks.kpi.recalculate_all_companies_kpi",
    queue="kpi_queue",
)
def recalculate_all_companies_kpi():
    return asyncio.run(_fanout())


async def _fanout() -> dict:
    from sqlalchemy import select
    from app.models import Company
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Company).where(Company.is_active == True))
        companies = result.scalars().all()
    for c in companies:
        recalculate_company_kpi.delay(c.id)
    return {"enqueued": len(companies)}
