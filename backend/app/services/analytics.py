"""
AnalyticsService — KPI для контрольной панели руководителя.

Все запросы tenant-isolated по company_id. Только ADMIN/HEAD имеют доступ.

Метрики:
  - Collection: суммы платежей в разрезе менеджера за день/неделю/месяц
  - PTP Conversion: процент выполненных обещаний
  - Activity: звонки, задачи, items в очереди
  - Leakage: список сорванных обещаний с ответственным менеджером

Snapshot-based metrics берутся из manager_kpi_snapshots (быстро),
live metrics — прямо из SQL (для актуальных цифр на текущий день).
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, Literal
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.operations import Payment, Promise, CallLog
from app.models.contract import Contract
from app.models.debtor import Debtor
from app.models.saas import Task
from app.models.call_queue import CallQueueItem, QUEUE_ITEM_STATUS_COMPLETED
from app.models.kpi_snapshot import ManagerKpiSnapshot


def _period_range(period: str, today: Optional[date] = None) -> tuple[date, date]:
    today = today or date.today()
    if period == "day":
        return today, today
    if period == "week":
        start = today - timedelta(days=today.weekday())
        return start, today
    if period == "month":
        return today.replace(day=1), today
    raise ValueError(f"Unknown period: {period}")


class AnalyticsService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.company_id = company_id

    # ============ Live (real-time) metrics ============
    async def manager_performance_live(
        self, period: Literal["day", "week", "month"] = "day"
    ) -> list[dict]:
        """
        Live KPI всех менеджеров компании за период.
        Тяжёлый запрос — для быстрых дашбордов используйте snapshots.
        """
        start, end = _period_range(period)
        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())

        managers_q = select(User).where(
            User.role == "MANAGER", User.is_active == True
        )
        if self.company_id is not None:
            managers_q = managers_q.where(User.company_id == self.company_id)
        managers = (await self.db.execute(managers_q)).scalars().all()

        result = []
        for m in managers:
            # Collection (сумма платежей зарегистрированных этим менеджером)
            pay_q = select(
                func.coalesce(func.sum(Payment.amount), 0),
                func.count(Payment.id),
            ).where(
                Payment.registered_by_id == m.id,
                Payment.payment_date.between(start, end),
            )
            if self.company_id is not None:
                pay_q = pay_q.where(Payment.company_id == self.company_id)
            collection_amount, payments_count = (await self.db.execute(pay_q)).one()

            # PTP — обещания которые менеджер давал в этот период
            given_q = select(func.count(Promise.id)).where(
                Promise.created_by_id == m.id,
                Promise.created_at.between(start_dt, end_dt),
            )
            if self.company_id is not None:
                given_q = given_q.where(Promise.company_id == self.company_id)
            promises_given = (await self.db.execute(given_q)).scalar() or 0

            # Kept (status='done' or 'fulfilled')
            kept_q = select(func.count(Promise.id)).where(
                Promise.created_by_id == m.id,
                Promise.created_at.between(start_dt, end_dt),
                Promise.status.in_(["done", "fulfilled", "kept"]),
            )
            if self.company_id is not None:
                kept_q = kept_q.where(Promise.company_id == self.company_id)
            promises_kept = (await self.db.execute(kept_q)).scalar() or 0

            # Broken
            broken_q = select(func.count(Promise.id)).where(
                Promise.created_by_id == m.id,
                Promise.created_at.between(start_dt, end_dt),
                Promise.status.in_(["overdue", "broken"]),
            )
            if self.company_id is not None:
                broken_q = broken_q.where(Promise.company_id == self.company_id)
            promises_broken = (await self.db.execute(broken_q)).scalar() or 0

            # Auto-fulfilled by system
            af_q = select(func.count(Promise.id)).where(
                Promise.created_by_id == m.id,
                Promise.auto_fulfilled == True,
                Promise.fulfilled_at.between(start_dt, end_dt),
            )
            if self.company_id is not None:
                af_q = af_q.where(Promise.company_id == self.company_id)
            promises_auto_fulfilled = (await self.db.execute(af_q)).scalar() or 0

            ptp_conversion = (
                round((promises_kept / promises_given) * 100, 1)
                if promises_given else 0
            )

            # Activity: calls
            calls_q = select(
                func.count(CallLog.id),
                func.sum(case((CallLog.outcome.in_(["reached", "promise"]), 1), else_=0)),
            ).where(
                CallLog.manager_id == m.id,
                CallLog.called_at.between(start_dt, end_dt),
            )
            if self.company_id is not None:
                calls_q = calls_q.where(CallLog.company_id == self.company_id)
            calls_made, calls_reached = (await self.db.execute(calls_q)).one()
            calls_made = calls_made or 0
            calls_reached = int(calls_reached or 0)

            # Queue items processed
            cqi_q = select(func.count(CallQueueItem.id)).where(
                CallQueueItem.assigned_manager_id == m.id,
                CallQueueItem.status == QUEUE_ITEM_STATUS_COMPLETED,
                CallQueueItem.completed_at.between(start_dt, end_dt),
            )
            if self.company_id is not None:
                cqi_q = cqi_q.where(CallQueueItem.company_id == self.company_id)
            queue_processed = (await self.db.execute(cqi_q)).scalar() or 0

            # Tasks completed
            tasks_q = select(func.count(Task.id)).where(
                Task.assignee_id == m.id,
                Task.status == "completed",
                Task.completed_at.between(start_dt, end_dt),
            )
            if self.company_id is not None:
                tasks_q = tasks_q.where(Task.company_id == self.company_id)
            tasks_done = (await self.db.execute(tasks_q)).scalar() or 0

            result.append({
                "manager_id": m.id,
                "manager_name": m.full_name,
                "manager_email": m.email,
                "collection_amount": float(collection_amount or 0),
                "payments_count": payments_count or 0,
                "promises_given": promises_given,
                "promises_kept": promises_kept,
                "promises_broken": promises_broken,
                "promises_auto_fulfilled": promises_auto_fulfilled,
                "ptp_conversion_pct": ptp_conversion,
                "calls_made": calls_made,
                "calls_reached": calls_reached,
                "reach_rate_pct": round((calls_reached / calls_made * 100), 1) if calls_made else 0,
                "queue_items_processed": queue_processed,
                "tasks_completed": tasks_done,
            })

        # Sort by collection desc (leaderboard)
        result.sort(key=lambda x: x["collection_amount"], reverse=True)
        return result

    # ============ Snapshot-based (fast) ============
    async def manager_performance_snapshot(
        self, period: Literal["day", "week", "month"] = "day"
    ) -> list[dict]:
        """Быстрая версия из manager_kpi_snapshots."""
        today = date.today()
        q = (
            select(ManagerKpiSnapshot, User)
            .join(User, ManagerKpiSnapshot.manager_id == User.id)
            .where(
                ManagerKpiSnapshot.period == period,
                ManagerKpiSnapshot.snapshot_date == today,
            )
        )
        if self.company_id is not None:
            q = q.where(ManagerKpiSnapshot.company_id == self.company_id)
        rows = (await self.db.execute(q)).all()
        out = []
        for snap, user in rows:
            out.append({
                "manager_id": user.id,
                "manager_name": user.full_name,
                "manager_email": user.email,
                "collection_amount": float(snap.collection_amount or 0),
                "payments_count": snap.payments_count,
                "promises_given": snap.promises_given,
                "promises_kept": snap.promises_kept,
                "promises_broken": snap.promises_broken,
                "ptp_conversion_pct": float(snap.ptp_conversion_pct),
                "calls_made": snap.calls_made,
                "calls_reached": snap.calls_reached,
                "reach_rate_pct": round(
                    (snap.calls_reached / snap.calls_made * 100), 1
                ) if snap.calls_made else 0,
                "queue_items_processed": snap.queue_items_processed,
                "tasks_completed": snap.tasks_completed,
                "calculated_at": snap.calculated_at.isoformat() if snap.calculated_at else None,
            })
        out.sort(key=lambda x: x["collection_amount"], reverse=True)
        return out

    # ============ Broken Promises (Leakage) ============
    async def broken_promises(
        self, limit: int = 100, manager_id: int | None = None
    ) -> list[dict]:
        """Список сорванных обещаний с ответственным менеджером."""
        q = (
            select(Promise, Contract, Debtor, User)
            .join(Contract, Promise.contract_id == Contract.id)
            .join(Debtor, Contract.debtor_id == Debtor.id)
            .outerjoin(User, Promise.created_by_id == User.id)
            .where(
                Promise.status.in_(["overdue", "broken"]),
                Debtor.deleted_at.is_(None),
            )
        )
        if self.company_id is not None:
            q = q.where(Promise.company_id == self.company_id)
        if manager_id:
            q = q.where(or_(
                Promise.created_by_id == manager_id,
                Debtor.assigned_manager_id == manager_id,
            ))
        q = q.order_by(Promise.promise_date.desc()).limit(limit)
        rows = (await self.db.execute(q)).all()
        return [
            {
                "promise_id": p.id,
                "promise_date": p.promise_date.isoformat() if p.promise_date else None,
                "amount": float(p.amount) if p.amount else 0,
                "status": p.status,
                "days_overdue": (date.today() - p.promise_date).days if p.promise_date else 0,
                "debtor_id": d.id,
                "debtor_full_name": d.full_name,
                "debtor_phone": d.phone_primary,
                "debtor_score": d.score,
                "debtor_score_tier": d.score_tier,
                "contract_id": c.id,
                "contract_number": c.contract_number,
                "manager_id": u.id if u else None,
                "manager_name": u.full_name if u else "—",
            }
            for p, c, d, u in rows
        ]

    # ============ Dashboard summary ============
    async def control_panel_summary(self) -> dict:
        """Сводка для контрольной панели — общие цифры компании."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        month_start_dt = datetime.combine(month_start, datetime.min.time())

        def pay_sum(date_filter):
            q = select(func.coalesce(func.sum(Payment.amount), 0)).where(date_filter)
            if self.company_id is not None:
                q = q.where(Payment.company_id == self.company_id)
            return q

        collection_today = (await self.db.execute(pay_sum(Payment.payment_date == today))).scalar() or 0
        collection_week = (await self.db.execute(pay_sum(Payment.payment_date >= week_start))).scalar() or 0
        collection_month = (await self.db.execute(pay_sum(Payment.payment_date >= month_start))).scalar() or 0

        # Promises (за месяц)
        prom_q = select(
            # active на сегодня
            func.count(Promise.id).filter(
                Promise.status == "active", Promise.promise_date == today
            ).label("active_today"),
            # broken за всё время
            func.count(Promise.id).filter(
                Promise.status.in_(["overdue", "broken"])
            ).label("broken_total"),
            # kept за месяц (любые fulfilled)
            func.count(Promise.id).filter(
                Promise.status.in_(["done", "kept", "fulfilled"]),
                Promise.created_at >= month_start_dt,
            ).label("kept_month"),
            # Auto-fulfilled by system за месяц
            func.count(Promise.id).filter(
                Promise.auto_fulfilled == True,
                Promise.fulfilled_at >= month_start_dt,
            ).label("auto_fulfilled_month"),
            # given за месяц
            func.count(Promise.id).filter(
                Promise.created_at >= month_start_dt
            ).label("given_month"),
        )
        if self.company_id is not None:
            prom_q = prom_q.where(Promise.company_id == self.company_id)
        row = (await self.db.execute(prom_q)).one()
        active_today = row.active_today or 0
        broken_total = row.broken_total or 0
        kept_month = row.kept_month or 0
        auto_fulfilled_month = row.auto_fulfilled_month or 0
        given_month = row.given_month or 0
        ptp_month = round((kept_month / given_month) * 100, 1) if given_month else 0

        # Promise Fulfillment Rate за всё время (kept / (kept + broken))
        total_q = select(
            func.count(Promise.id).filter(
                Promise.status.in_(["done", "kept", "fulfilled"])
            ).label("kept_all"),
            func.count(Promise.id).filter(
                Promise.status.in_(["overdue", "broken"])
            ).label("broken_all"),
        )
        if self.company_id is not None:
            total_q = total_q.where(Promise.company_id == self.company_id)
        kept_all, broken_all = (await self.db.execute(total_q)).one()
        kept_all = kept_all or 0
        broken_all = broken_all or 0
        fulfillment_total = kept_all + broken_all
        fulfillment_rate_pct = (
            round((kept_all / fulfillment_total) * 100, 1) if fulfillment_total else 0
        )

        # Active managers
        m_q = select(func.count(User.id)).where(User.role == "MANAGER", User.is_active == True)
        if self.company_id is not None:
            m_q = m_q.where(User.company_id == self.company_id)
        active_managers = (await self.db.execute(m_q)).scalar() or 0

        # Calls today
        today_start = datetime.combine(today, datetime.min.time())
        c_q = select(func.count(CallLog.id)).where(CallLog.called_at >= today_start)
        if self.company_id is not None:
            c_q = c_q.where(CallLog.company_id == self.company_id)
        calls_today = (await self.db.execute(c_q)).scalar() or 0

        return {
            "collection_today": float(collection_today),
            "collection_week": float(collection_week),
            "collection_month": float(collection_month),
            "promises_active_today": active_today,
            "promises_broken_total": broken_total,
            "promises_kept_month": kept_month,
            "promises_given_month": given_month,
            "ptp_conversion_month_pct": ptp_month,
            # === New (Module 3) ===
            "promises_auto_fulfilled_month": auto_fulfilled_month,
            "promise_fulfillment_rate_pct": fulfillment_rate_pct,
            # ===
            "active_managers": active_managers,
            "calls_today": calls_today,
        }

    # ============ Daily collection chart ============
    async def daily_collection(self, days: int = 30) -> list[dict]:
        start = date.today() - timedelta(days=days - 1)
        q = select(
            Payment.payment_date,
            func.sum(Payment.amount).label("amount"),
            func.count(Payment.id).label("count"),
        ).where(Payment.payment_date >= start)
        if self.company_id is not None:
            q = q.where(Payment.company_id == self.company_id)
        q = q.group_by(Payment.payment_date).order_by(Payment.payment_date)
        rows = (await self.db.execute(q)).all()
        return [
            {"date": r[0].isoformat(), "amount": float(r[1] or 0), "count": r[2]}
            for r in rows
        ]
