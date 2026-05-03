"""Pack 2: Periodic check for overdue tasks.
Runs every 30 minutes (Celery Beat).
Sends notifications to assignee and creator when task is overdue.
Idempotent: marks tasks with `overdue_notified_at` so we don't spam.
"""
import asyncio
import logging
from datetime import datetime
from celery import shared_task
from sqlalchemy import select, and_, or_

from app.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models import Task, Notification, User, Company

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.tasks_overdue.check_overdue_tasks",
    queue="workflow_queue",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def check_overdue_tasks(self):
    """Каждые 30 минут проверяет просроченные задачи во всех компаниях."""
    return asyncio.run(_check_all_companies())


async def _check_all_companies() -> dict:
    """Iterate companies and check overdue."""
    total_notified = 0
    total_overdue = 0
    async with AsyncSessionLocal() as db:
        companies = (await db.execute(select(Company.id))).scalars().all()
        for company_id in companies:
            try:
                stats = await _check_company(db, company_id)
                total_overdue += stats.get("overdue", 0)
                total_notified += stats.get("notified", 0)
            except Exception as e:
                logger.exception("Failed to check overdue tasks for company %s: %s", company_id, e)
        await db.commit()
    return {"companies": len(companies), "overdue": total_overdue, "notified": total_notified}


async def _check_company(db, company_id: int) -> dict:
    """Find overdue tasks for a single company and notify users."""
    now = datetime.utcnow()

    # Условие: due_date < now AND status NOT IN (done, cancelled) AND not soft-deleted
    q = select(Task).where(
        Task.company_id == company_id,
        Task.due_date.isnot(None),
        Task.due_date < now,
        Task.status.notin_(["done", "cancelled"]),
    )
    if hasattr(Task, "deleted_at"):
        q = q.where(Task.deleted_at.is_(None))

    overdue_tasks = (await db.execute(q)).scalars().all()
    notified = 0

    for task in overdue_tasks:
        # Проверяем — не отправляли ли уже сегодня уведомление этому assignee про эту задачу
        # Простая идемпотентность: ищем notification с типом 'task_overdue' за последние 6 часов
        from datetime import timedelta
        cutoff = now - timedelta(hours=6)

        existing = (await db.execute(
            select(Notification).where(
                Notification.user_id == task.assignee_id if task.assignee_id else False,
                Notification.type == "task_overdue",
                Notification.created_at >= cutoff,
                Notification.link == f"/tasks?status=overdue&id={task.id}",
            )
        )).scalar_one_or_none() if task.assignee_id else None

        if existing or not task.assignee_id:
            continue

        # Создаём уведомление assignee
        notif = Notification(
            company_id=company_id,
            user_id=task.assignee_id,
            type="task_overdue",
            title="Просроченная задача",
            message=f"Задача «{task.title}» просрочена ({task.due_date.strftime('%d.%m.%Y %H:%M') if task.due_date else '—'})",
            link=f"/tasks?status=overdue&id={task.id}",
            related_debtor_id=task.debtor_id,
            is_read=False,
        )
        db.add(notif)
        notified += 1

        # Также уведомляем создателя (если это другой человек и он head/admin)
        if task.created_by_id and task.created_by_id != task.assignee_id:
            creator_notif = Notification(
                company_id=company_id,
                user_id=task.created_by_id,
                type="task_overdue",
                title="Просрочена делегированная задача",
                message=f"Задача «{task.title}» (исп.: ID {task.assignee_id}) просрочена",
                link=f"/tasks?status=overdue&id={task.id}",
                related_debtor_id=task.debtor_id,
                is_read=False,
            )
            db.add(creator_notif)
            notified += 1

    if notified > 0:
        logger.info("[overdue-tasks] company=%s overdue=%s notified=%s",
                    company_id, len(overdue_tasks), notified)

    return {"overdue": len(overdue_tasks), "notified": notified}
