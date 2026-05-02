"""
KpiSnapshotService — пересчитывает manager_kpi_snapshots для быстрых дашбордов.
Вызывается из Celery Beat раз в час.

Логика: для каждого менеджера компании на сегодня сохраняет 3 snapshot'а:
period='day', 'week', 'month' с агрегированными метриками.
UPSERT по уникальному ключу (company_id, manager_id, period, snapshot_date).
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional
from sqlalchemy import select, func, and_, case
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.operations import Payment, Promise, CallLog
from app.models.saas import Task
from app.models.call_queue import CallQueueItem, QUEUE_ITEM_STATUS_COMPLETED
from app.models.kpi_snapshot import ManagerKpiSnapshot


class KpiSnapshotService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.company_id = company_id

    async def recalculate(self) -> dict:
        """Пересчитать snapshots для всех менеджеров компании на сегодня."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        # Получить менеджеров
        m_q = select(User.id).where(User.role == "MANAGER", User.is_active == True)
        if self.company_id is not None:
            m_q = m_q.where(User.company_id == self.company_id)
        manager_ids = list((await self.db.execute(m_q)).scalars().all())

        total = 0
        for mid in manager_ids:
            for period_name, period_start in [
                ("day", today),
                ("week", week_start),
                ("month", month_start),
            ]:
                metrics = await self._calc(mid, period_start, today)
                await self._upsert(mid, period_name, today, metrics)
                total += 1

        await self.db.commit()
        return {"snapshots_written": total, "managers": len(manager_ids)}

    async def _calc(self, manager_id: int, start: date, end: date) -> dict:
        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())

        # Collection
        pay_q = select(
            func.coalesce(func.sum(Payment.amount), 0),
            func.count(Payment.id),
        ).where(
            Payment.registered_by_id == manager_id,
            Payment.payment_date.between(start, end),
        )
        if self.company_id is not None:
            pay_q = pay_q.where(Payment.company_id == self.company_id)
        coll, pay_count = (await self.db.execute(pay_q)).one()

        # Promises given
        given_q = select(func.count(Promise.id)).where(
            Promise.created_by_id == manager_id,
            Promise.created_at.between(start_dt, end_dt),
        )
        if self.company_id is not None:
            given_q = given_q.where(Promise.company_id == self.company_id)
        given = (await self.db.execute(given_q)).scalar() or 0

        kept_q = select(func.count(Promise.id)).where(
            Promise.created_by_id == manager_id,
            Promise.created_at.between(start_dt, end_dt),
            Promise.status.in_(["done", "kept", "fulfilled"]),
        )
        if self.company_id is not None:
            kept_q = kept_q.where(Promise.company_id == self.company_id)
        kept = (await self.db.execute(kept_q)).scalar() or 0

        broken_q = select(func.count(Promise.id)).where(
            Promise.created_by_id == manager_id,
            Promise.created_at.between(start_dt, end_dt),
            Promise.status.in_(["overdue", "broken"]),
        )
        if self.company_id is not None:
            broken_q = broken_q.where(Promise.company_id == self.company_id)
        broken = (await self.db.execute(broken_q)).scalar() or 0

        ptp = round((kept / given) * 100, 2) if given else 0

        # Calls
        c_q = select(
            func.count(CallLog.id),
            func.sum(case((CallLog.outcome.in_(["reached", "promise"]), 1), else_=0)),
        ).where(
            CallLog.manager_id == manager_id,
            CallLog.called_at.between(start_dt, end_dt),
        )
        if self.company_id is not None:
            c_q = c_q.where(CallLog.company_id == self.company_id)
        calls_made, calls_reached = (await self.db.execute(c_q)).one()

        # Queue items
        cqi_q = select(func.count(CallQueueItem.id)).where(
            CallQueueItem.assigned_manager_id == manager_id,
            CallQueueItem.status == QUEUE_ITEM_STATUS_COMPLETED,
            CallQueueItem.completed_at.between(start_dt, end_dt),
        )
        if self.company_id is not None:
            cqi_q = cqi_q.where(CallQueueItem.company_id == self.company_id)
        queue_done = (await self.db.execute(cqi_q)).scalar() or 0

        # Tasks
        t_q = select(func.count(Task.id)).where(
            Task.assignee_id == manager_id,
            Task.status == "completed",
            Task.completed_at.between(start_dt, end_dt),
        )
        if self.company_id is not None:
            t_q = t_q.where(Task.company_id == self.company_id)
        tasks_done = (await self.db.execute(t_q)).scalar() or 0

        return {
            "collection_amount": Decimal(coll or 0),
            "payments_count": pay_count or 0,
            "promises_given": given,
            "promises_kept": kept,
            "promises_broken": broken,
            "ptp_conversion_pct": Decimal(str(ptp)),
            "calls_made": calls_made or 0,
            "calls_reached": int(calls_reached or 0),
            "queue_items_processed": queue_done,
            "tasks_completed": tasks_done,
        }

    async def _upsert(self, manager_id: int, period: str, snapshot_date: date, metrics: dict):
        """UPSERT по unique constraint (company_id, manager_id, period, snapshot_date)."""
        stmt = pg_insert(ManagerKpiSnapshot).values(
            company_id=self.company_id or 1,
            manager_id=manager_id,
            period=period,
            snapshot_date=snapshot_date,
            calculated_at=datetime.utcnow(),
            **metrics,
        )
        update_dict = {**metrics, "calculated_at": datetime.utcnow()}
        stmt = stmt.on_conflict_do_update(
            index_elements=["company_id", "manager_id", "period", "snapshot_date"],
            set_=update_dict,
        )
        await self.db.execute(stmt)
