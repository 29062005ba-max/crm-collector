"""Workflow tasks: process overdue promises/schedules.
Replaces in-process APScheduler logic from main.py.
"""
import asyncio
import logging
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from datetime import datetime
from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models import Company
from app.services.saas import WorkflowService
from app.tasks._async_helper import track_job

logger = logging.getLogger(__name__)


# ==================== Per-company workflow ====================
@celery_app.task(
    bind=True,
    name="app.tasks.workflow.process_overdue_promises_for_company",
    queue="workflow_queue",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
    acks_late=True,
)
@track_job(task_name="process_overdue_promises_for_company", queue="workflow_queue")
def process_overdue_promises_for_company(self, company_id: int):
    """Process overdue promises for a single company.
    Idempotent: повторный запуск не создаст дублей (status уже будет 'overdue')."""
    return asyncio.run(_process_promises(company_id))


async def _process_promises(company_id: int) -> dict:
    async with AsyncSessionLocal() as db:
        try:
            svc = WorkflowService(db, company_id=company_id)
            count = await svc.process_overdue_promises()
            await db.commit()
            logger.info(f"[workflow] company={company_id}: processed {count} overdue promises")
            return {"company_id": company_id, "overdue_promises_processed": count}
        except Exception:
            await db.rollback()
            raise


@celery_app.task(
    bind=True,
    name="app.tasks.workflow.process_overdue_schedules_for_company",
    queue="schedule_queue",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=5,
    acks_late=True,
)
@track_job(task_name="process_overdue_schedules_for_company", queue="schedule_queue")
def process_overdue_schedules_for_company(self, company_id: int):
    return asyncio.run(_process_schedules(company_id))


async def _process_schedules(company_id: int) -> dict:
    async with AsyncSessionLocal() as db:
        try:
            svc = WorkflowService(db, company_id=company_id)
            count = await svc.process_overdue_schedules()
            await db.commit()
            logger.info(f"[workflow] company={company_id}: processed {count} overdue schedules")
            return {"company_id": company_id, "overdue_schedules_processed": count}
        except Exception:
            await db.rollback()
            raise


# ==================== Beat-scheduled fan-out tasks ====================
# Эти запускаются Celery Beat, и веером раздают per-company задачи

@celery_app.task(
    name="app.tasks.workflow.process_overdue_promises_all_companies",
    queue="workflow_queue",
)
def process_overdue_promises_all_companies():
    """Beat-triggered: разослать задачи по всем активным компаниям"""
    return asyncio.run(_fanout_promises())


async def _fanout_promises() -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Company).where(Company.is_active == True))
        companies = result.scalars().all()
    enqueued = 0
    for c in companies:
        process_overdue_promises_for_company.delay(c.id)
        enqueued += 1
    logger.info(f"[workflow] fanout promises: enqueued {enqueued} per-company tasks")
    return {"enqueued": enqueued, "companies": len(companies)}


@celery_app.task(
    name="app.tasks.workflow.process_overdue_schedules_all_companies",
    queue="schedule_queue",
)
def process_overdue_schedules_all_companies():
    return asyncio.run(_fanout_schedules())


async def _fanout_schedules() -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Company).where(Company.is_active == True))
        companies = result.scalars().all()
    enqueued = 0
    for c in companies:
        process_overdue_schedules_for_company.delay(c.id)
        enqueued += 1
    logger.info(f"[workflow] fanout schedules: enqueued {enqueued} per-company tasks")
    return {"enqueued": enqueued, "companies": len(companies)}
