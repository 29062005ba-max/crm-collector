"""
MyDayService — единая точка фокусировки менеджера на текущий день.

Возвращает 3 блока:
  1. Горящие (HOT) — задачи/обещания по должникам со score_tier='hot'
  2. На сегодня — обещания promise_date == today + ручные tasks с due_date today
  3. Просроченные — обещания со status='overdue' + tasks с due_date < today
"""
from datetime import datetime, date, timedelta
from typing import Optional
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.saas import Task
from app.models.operations import Promise, Payment
from app.models.contract import Contract
from app.models.debtor import Debtor
from app.models.user import User


class MyDayService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.company_id = company_id

    async def get_my_day(self, manager_id: int) -> dict:
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        promises_today = await self._promises_today(manager_id, today)
        promises_overdue = await self._promises_overdue(manager_id, today)
        tasks_today = await self._tasks_today(manager_id, today_start, today_end)
        tasks_overdue = await self._tasks_overdue(manager_id, today_start)

        # Соединяем: горящие = HOT-должники из всех 4-х списков
        hot_items = []
        regular_today = []
        regular_overdue = []

        for p in promises_today:
            (hot_items if p["is_hot"] else regular_today).append({**p, "kind": "promise_today"})
        for t in tasks_today:
            (hot_items if t["is_hot"] else regular_today).append({**t, "kind": "task_today"})
        for p in promises_overdue:
            (hot_items if p["is_hot"] else regular_overdue).append({**p, "kind": "promise_overdue"})
        for t in tasks_overdue:
            (hot_items if t["is_hot"] else regular_overdue).append({**t, "kind": "task_overdue"})

        # Hot — отсортировать по сумме (desc), для остальных — по due_date/promise_date asc
        hot_items.sort(key=lambda x: float(x.get("amount") or x.get("debt") or 0), reverse=True)
        regular_today.sort(key=lambda x: x.get("due_date_iso") or x.get("promise_date_iso") or "")
        regular_overdue.sort(key=lambda x: x.get("due_date_iso") or x.get("promise_date_iso") or "")

        # Summary
        total_promises_amount_today = sum(
            float(p["amount"] or 0) for p in promises_today if p.get("amount")
        )

        return {
            "manager_id": manager_id,
            "date": today.isoformat(),
            "summary": {
                "hot_count": len(hot_items),
                "today_count": len(regular_today) + sum(1 for x in hot_items if "today" in x["kind"]),
                "overdue_count": len(regular_overdue) + sum(1 for x in hot_items if "overdue" in x["kind"]),
                "promises_today_count": len(promises_today),
                "promises_today_amount": total_promises_amount_today,
                "promises_overdue_count": len(promises_overdue),
                "tasks_today_count": len(tasks_today),
                "tasks_overdue_count": len(tasks_overdue),
            },
            "hot": hot_items,
            "today": regular_today,
            "overdue": regular_overdue,
        }

    async def _promises_today(self, manager_id: int, today: date) -> list[dict]:
        """Обещания на сегодня, где должник назначен этому менеджеру ИЛИ обещание создал он."""
        q = (
            select(Promise, Contract, Debtor)
            .join(Contract, Promise.contract_id == Contract.id)
            .join(Debtor, Contract.debtor_id == Debtor.id)
            .where(
                Promise.promise_date == today,
                Promise.status == "active",
                Debtor.deleted_at.is_(None),
            )
        )
        q = self._tenant(q, Promise)
        q = q.where(or_(
            Debtor.assigned_manager_id == manager_id,
            Promise.created_by_id == manager_id,
        ))
        rows = (await self.db.execute(q)).all()
        return [self._map_promise(p, c, d) for p, c, d in rows]

    async def _promises_overdue(self, manager_id: int, today: date) -> list[dict]:
        """Просроченные обещания (overdue или active с promise_date < today)."""
        q = (
            select(Promise, Contract, Debtor)
            .join(Contract, Promise.contract_id == Contract.id)
            .join(Debtor, Contract.debtor_id == Debtor.id)
            .where(
                or_(
                    Promise.status == "overdue",
                    and_(Promise.status == "active", Promise.promise_date < today),
                ),
                Debtor.deleted_at.is_(None),
            )
        )
        q = self._tenant(q, Promise)
        q = q.where(or_(
            Debtor.assigned_manager_id == manager_id,
            Promise.created_by_id == manager_id,
        ))
        # Limit чтобы не вернуть тысячи старых
        q = q.order_by(Promise.promise_date.desc()).limit(200)
        rows = (await self.db.execute(q)).all()
        return [self._map_promise(p, c, d) for p, c, d in rows]

    async def _tasks_today(self, manager_id: int, today_start: datetime, today_end: datetime) -> list[dict]:
        q = (
            select(Task, Debtor)
            .outerjoin(Debtor, Task.debtor_id == Debtor.id)
            .where(
                Task.assignee_id == manager_id,
                Task.status == "open",
                Task.due_date.between(today_start, today_end),
            )
        )
        q = self._tenant(q, Task)
        q = q.order_by(Task.due_date.asc())
        rows = (await self.db.execute(q)).all()
        return [self._map_task(t, d) for t, d in rows]

    async def _tasks_overdue(self, manager_id: int, today_start: datetime) -> list[dict]:
        q = (
            select(Task, Debtor)
            .outerjoin(Debtor, Task.debtor_id == Debtor.id)
            .where(
                Task.assignee_id == manager_id,
                Task.status == "open",
                Task.due_date < today_start,
            )
        )
        q = self._tenant(q, Task)
        q = q.order_by(Task.due_date.asc()).limit(200)
        rows = (await self.db.execute(q)).all()
        return [self._map_task(t, d) for t, d in rows]

    def _tenant(self, q, model):
        if self.company_id is not None:
            q = q.where(model.company_id == self.company_id)
        return q

    def _map_promise(self, p: Promise, c: Contract, d: Debtor) -> dict:
        return {
            "type": "promise",
            "id": p.id,
            "promise_date": p.promise_date,
            "promise_date_iso": p.promise_date.isoformat() if p.promise_date else None,
            "amount": float(p.amount) if p.amount else 0,
            "status": p.status,
            "notes": p.notes,
            "contract_id": c.id,
            "contract_number": c.contract_number,
            "debtor_id": d.id,
            "debtor_full_name": d.full_name,
            "debtor_phone": d.phone_primary,
            "debtor_score": d.score,
            "debtor_score_tier": d.score_tier,
            "is_hot": d.score_tier == "hot",
            "debt": float(c.total_debt) if c.total_debt else 0,
        }

    def _map_task(self, t: Task, d: Debtor | None) -> dict:
        return {
            "type": "task",
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "task_type": t.type,
            "priority": t.priority,
            "status": t.status,
            "due_date": t.due_date,
            "due_date_iso": t.due_date.isoformat() if t.due_date else None,
            "debtor_id": d.id if d else None,
            "debtor_full_name": d.full_name if d else None,
            "debtor_phone": d.phone_primary if d else None,
            "debtor_score": d.score if d else None,
            "debtor_score_tier": d.score_tier if d else None,
            "is_hot": (d.score_tier == "hot") if d else False,
            "amount": None,
            "debt": None,
        }

    async def complete_task(self, task_id: int, manager_id: int) -> dict:
        """Закрыть задачу (для UI). Audit logged через ActivityLogService."""
        from app.services.saas import ActivityLogService
        task = await self.db.get(Task, task_id)
        if not task:
            return {"ok": False, "error": "not_found"}
        if task.assignee_id != manager_id:
            return {"ok": False, "error": "not_yours"}
        if self.company_id is not None and task.company_id != self.company_id:
            return {"ok": False, "error": "wrong_company"}
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        log = ActivityLogService(self.db, company_id=self.company_id)
        await log.log(
            actor_id=manager_id,
            action="task_completed",
            entity_type="task",
            entity_id=task_id,
            description=f"Задача #{task_id} закрыта менеджером",
            debtor_id=task.debtor_id,
        )
        await self.db.commit()
        return {"ok": True, "task_id": task_id}
