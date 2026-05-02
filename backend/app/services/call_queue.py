"""Call Queue service — atomic take-next + outcome handling"""
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models.call_queue import (
    CallQueue, CallQueueItem,
    QUEUE_ITEM_STATUS_PENDING, QUEUE_ITEM_STATUS_IN_PROGRESS,
    QUEUE_ITEM_STATUS_COMPLETED, QUEUE_ITEM_STATUS_SCHEDULED, QUEUE_ITEM_STATUS_FAILED,
    CALL_OUTCOME_REACHED, CALL_OUTCOME_NOT_REACHED, CALL_OUTCOME_PROMISE,
    CALL_OUTCOME_CALLBACK, CALL_OUTCOME_REFUSED, CALL_OUTCOME_WRONG_NUMBER,
)
from app.models.debtor import Debtor
from app.models.contract import Contract
from app.models.user import User
from app.models.operations import Promise, CallLog
from app.models.saas import Task

LOCK_DURATION_MINUTES = 5


class CallQueueService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.company_id = company_id

    def _tenant_q(self, q):
        if self.company_id is not None:
            q = q.where(CallQueue.company_id == self.company_id)
        return q

    def _tenant_i(self, q):
        if self.company_id is not None:
            q = q.where(CallQueueItem.company_id == self.company_id)
        return q

    # ============ Queue CRUD ============
    async def create_queue(self, data, created_by_id: int) -> CallQueue:
        kwargs = data.model_dump()
        if self.company_id is not None:
            kwargs["company_id"] = self.company_id
        kwargs["created_by_id"] = created_by_id
        q = CallQueue(**kwargs)
        self.db.add(q)
        await self.db.commit()
        await self.db.refresh(q)
        return q

    async def list_queues(self) -> list[dict]:
        q = self._tenant_q(select(CallQueue)).order_by(CallQueue.created_at.desc())
        queues = (await self.db.execute(q)).scalars().all()

        out = []
        for queue in queues:
            cnts_q = (
                select(CallQueueItem.status, func.count())
                .where(CallQueueItem.queue_id == queue.id)
                .group_by(CallQueueItem.status)
            )
            rows = (await self.db.execute(cnts_q)).all()
            by_status = {r[0]: r[1] for r in rows}
            d = {c.name: getattr(queue, c.name) for c in queue.__table__.columns}
            d["total_items"] = sum(by_status.values())
            d["pending_items"] = by_status.get(QUEUE_ITEM_STATUS_PENDING, 0) + by_status.get(QUEUE_ITEM_STATUS_SCHEDULED, 0)
            d["completed_items"] = by_status.get(QUEUE_ITEM_STATUS_COMPLETED, 0)
            out.append(d)
        return out

    async def get_queue(self, queue_id: int) -> CallQueue | None:
        q = self._tenant_q(select(CallQueue).where(CallQueue.id == queue_id))
        return (await self.db.execute(q)).scalar_one_or_none()

    async def update_queue(self, queue_id: int, data) -> CallQueue | None:
        queue = await self.get_queue(queue_id)
        if not queue:
            return None
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(queue, k, v)
        await self.db.commit()
        await self.db.refresh(queue)
        return queue

    async def delete_queue(self, queue_id: int) -> bool:
        queue = await self.get_queue(queue_id)
        if not queue:
            return False
        await self.db.delete(queue)
        await self.db.commit()
        return True

    # ============ Populate ============
    async def populate(self, queue_id: int, params) -> int:
        """
        Заполнить очередь должниками по фильтрам.
        Приоритет в очереди = Debtor.score (если есть scoring),
        иначе params.priority. Это гарантирует что HOT-должники
        идут первыми в take_next.
        """
        queue = await self.get_queue(queue_id)
        if not queue:
            raise HTTPException(404, "Очередь не найдена")

        # Берём контракты + score должника (для приоритизации HOT first)
        cq = (
            select(Contract.id, Contract.debtor_id, Debtor.score)
            .join(Debtor, Contract.debtor_id == Debtor.id)
            .where(Debtor.deleted_at.is_(None))
        )
        if self.company_id is not None:
            cq = cq.where(Contract.company_id == self.company_id)

        if queue.filter_contract_status:
            cq = cq.where(Contract.status == queue.filter_contract_status)
        if queue.filter_debt_min is not None:
            cq = cq.where(Contract.total_debt >= queue.filter_debt_min)
        if queue.filter_debt_max is not None:
            cq = cq.where(Contract.total_debt <= queue.filter_debt_max)

        today = date.today()
        if queue.filter_overdue_min_days is not None:
            cq = cq.where(Contract.overdue_date <= today - timedelta(days=queue.filter_overdue_min_days))
        if queue.filter_overdue_max_days is not None:
            cq = cq.where(Contract.overdue_date >= today - timedelta(days=queue.filter_overdue_max_days))

        # Сортируем — сначала с высоким score, потом по сумме долга
        cq = cq.order_by(
            Debtor.score.desc().nullslast(),
            Contract.total_debt.desc().nullslast(),
        )

        # Не дублировать активные
        existing_q = select(CallQueueItem.contract_id).where(
            and_(
                CallQueueItem.queue_id == queue_id,
                CallQueueItem.status.in_([
                    QUEUE_ITEM_STATUS_PENDING, QUEUE_ITEM_STATUS_IN_PROGRESS, QUEUE_ITEM_STATUS_SCHEDULED
                ]),
            )
        )
        existing_ids = set((await self.db.execute(existing_q)).scalars().all())

        cq = cq.limit(params.limit)
        rows = (await self.db.execute(cq)).all()

        managers = params.manager_ids or []
        if not managers and queue.auto_assign_strategy == "round_robin":
            mq = select(User.id).where(User.role == "MANAGER", User.is_active == True)
            if self.company_id is not None:
                mq = mq.where(User.company_id == self.company_id)
            managers = list((await self.db.execute(mq)).scalars().all())

        added = 0
        for i, (contract_id, debtor_id, debtor_score) in enumerate(rows):
            if contract_id in existing_ids:
                continue
            assigned = managers[i % len(managers)] if managers else None
            # Priority = score должника (0-100), иначе fallback на params.priority
            item_priority = int(debtor_score) if debtor_score is not None else params.priority
            item = CallQueueItem(
                company_id=self.company_id or 1,
                queue_id=queue_id,
                debtor_id=debtor_id,
                contract_id=contract_id,
                assigned_manager_id=assigned,
                status=QUEUE_ITEM_STATUS_PENDING,
                priority=item_priority,
                attempt_count=0,
            )
            self.db.add(item)
            added += 1

        await self.db.commit()
        return added

    # ============ List items ============
    async def list_items(self, queue_id: int, status: str | None = None,
                         manager_id: int | None = None, limit: int = 200) -> list[dict]:
        q = (
            select(CallQueueItem, Debtor, Contract, User.full_name.label("manager_name"))
            .join(Debtor, CallQueueItem.debtor_id == Debtor.id)
            .outerjoin(Contract, CallQueueItem.contract_id == Contract.id)
            .outerjoin(User, CallQueueItem.assigned_manager_id == User.id)
            .where(CallQueueItem.queue_id == queue_id)
        )
        q = self._tenant_i(q)
        if status:
            q = q.where(CallQueueItem.status == status)
        if manager_id:
            q = q.where(CallQueueItem.assigned_manager_id == manager_id)
        q = q.order_by(CallQueueItem.priority.desc(), CallQueueItem.created_at.desc()).limit(limit)
        rows = (await self.db.execute(q)).all()

        out = []
        for item, debtor, contract, manager_name in rows:
            d = {c.name: getattr(item, c.name) for c in item.__table__.columns}
            d["debtor_full_name"] = debtor.full_name if debtor else None
            d["debtor_iin"] = debtor.iin if debtor else None
            d["debtor_phone_primary"] = debtor.phone_primary if debtor else None
            d["debtor_phone_secondary"] = debtor.phone_secondary if debtor else None
            d["contract_number"] = contract.contract_number if contract else None
            d["total_debt"] = contract.total_debt if contract else None
            d["manager_name"] = manager_name
            out.append(d)
        return out

    # ============ TAKE NEXT ============
    async def take_next(self, manager_id: int, queue_id: int | None = None) -> dict | None:
        now = datetime.utcnow()
        lock_until = now + timedelta(minutes=LOCK_DURATION_MINUTES)

        base_filter = [
            CallQueueItem.status.in_([QUEUE_ITEM_STATUS_PENDING, QUEUE_ITEM_STATUS_SCHEDULED]),
            or_(CallQueueItem.locked_until.is_(None), CallQueueItem.locked_until < now),
            or_(CallQueueItem.next_attempt_at.is_(None), CallQueueItem.next_attempt_at <= now),
        ]
        if self.company_id is not None:
            base_filter.append(CallQueueItem.company_id == self.company_id)
        if queue_id:
            base_filter.append(CallQueueItem.queue_id == queue_id)

        # Сначала свои, потом без назначения
        for extra in (
            [CallQueueItem.assigned_manager_id == manager_id],
            [CallQueueItem.assigned_manager_id.is_(None)],
        ):
            q = (
                select(CallQueueItem)
                .where(and_(*base_filter, *extra))
                .order_by(
                    CallQueueItem.priority.desc(),
                    CallQueueItem.next_attempt_at.asc().nullsfirst(),
                    CallQueueItem.created_at.asc(),
                )
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            item = (await self.db.execute(q)).scalar_one_or_none()
            if item:
                item.status = QUEUE_ITEM_STATUS_IN_PROGRESS
                item.locked_until = lock_until
                item.locked_by_id = manager_id
                if item.assigned_manager_id is None:
                    item.assigned_manager_id = manager_id
                await self.db.commit()
                await self.db.refresh(item)
                return await self._enrich_item(item)
        return None

    async def release(self, item_id: int, manager_id: int) -> bool:
        """Менеджер пропускает item (release lock)."""
        q = select(CallQueueItem).where(CallQueueItem.id == item_id).with_for_update()
        if self.company_id is not None:
            q = q.where(CallQueueItem.company_id == self.company_id)
        item = (await self.db.execute(q)).scalar_one_or_none()
        if not item or item.locked_by_id != manager_id:
            return False
        item.status = QUEUE_ITEM_STATUS_PENDING
        item.locked_until = None
        item.locked_by_id = None
        await self.db.commit()
        return True

    async def _enrich_item(self, item: CallQueueItem) -> dict:
        debtor = await self.db.get(Debtor, item.debtor_id)
        contract = await self.db.get(Contract, item.contract_id) if item.contract_id else None
        d = {c.name: getattr(item, c.name) for c in item.__table__.columns}
        d["debtor_full_name"] = debtor.full_name if debtor else None
        d["debtor_iin"] = debtor.iin if debtor else None
        d["debtor_phone_primary"] = debtor.phone_primary if debtor else None
        d["debtor_phone_secondary"] = debtor.phone_secondary if debtor else None
        d["contract_number"] = contract.contract_number if contract else None
        d["total_debt"] = contract.total_debt if contract else None
        return d

    # ============ Submit result ============
    async def submit_result(self, manager: User, data) -> dict:
        q = select(CallQueueItem).where(CallQueueItem.id == data.item_id).with_for_update()
        if self.company_id is not None:
            q = q.where(CallQueueItem.company_id == self.company_id)
        item = (await self.db.execute(q)).scalar_one_or_none()
        if not item:
            raise HTTPException(404, "Элемент очереди не найден")

        if item.locked_by_id and item.locked_by_id != manager.id and item.assigned_manager_id != manager.id:
            raise HTTPException(403, "Заблокирован другим менеджером")

        queue = await self.db.get(CallQueue, item.queue_id)
        if not queue:
            raise HTTPException(404, "Очередь не найдена")

        now = datetime.utcnow()
        item.attempt_count += 1
        item.last_attempt_at = now
        item.last_call_outcome = data.outcome
        item.locked_until = None
        item.locked_by_id = None
        if data.notes:
            prefix = f"[{now:%Y-%m-%d %H:%M}] {manager.full_name}: "
            item.notes = (item.notes + "\n" if item.notes else "") + prefix + data.notes

        promise_id = None
        task_id = None
        message = ""

        # call log
        if item.contract_id:
            call_log = CallLog(
                company_id=self.company_id or 1,
                contract_id=item.contract_id,
                manager_id=manager.id,
                called_at=now,
                phone_number=data.phone_number or "",
                result=data.outcome,
                outcome=data.outcome,
                duration_seconds=data.duration_seconds,
                notes=data.notes,
                queue_item_id=item.id,
                next_callback_at=data.callback_at,
            )
            self.db.add(call_log)

        if data.outcome == CALL_OUTCOME_NOT_REACHED:
            if item.attempt_count < queue.max_attempts:
                item.status = QUEUE_ITEM_STATUS_SCHEDULED
                item.next_attempt_at = now + timedelta(hours=queue.retry_after_hours)
                message = f"Повтор через {queue.retry_after_hours}ч (попытка {item.attempt_count}/{queue.max_attempts})"
            else:
                item.status = QUEUE_ITEM_STATUS_FAILED
                item.completed_at = now
                task = Task(
                    company_id=self.company_id or 1,
                    title="Недозвон 3 раза — связаться с должником",
                    description=f"Менеджер {manager.full_name} не дозвонился {queue.max_attempts} раза. Использовать другие способы связи.",
                    type="callback",
                    priority="high",
                    status="open",
                    due_date=now + timedelta(days=1),
                    assignee_id=manager.id,
                    debtor_id=item.debtor_id,
                    contract_id=item.contract_id,
                    created_by_id=manager.id,
                )
                self.db.add(task)
                await self.db.flush()
                task_id = task.id
                message = f"Исчерпаны попытки. Создана задача #{task_id} на завтра."

        elif data.outcome == CALL_OUTCOME_PROMISE:
            item.status = QUEUE_ITEM_STATUS_COMPLETED
            item.completed_at = now
            if not data.promise_amount or not data.promise_date:
                raise HTTPException(400, "Для обещания нужны сумма и дата")
            if not item.contract_id:
                raise HTTPException(400, "Нет договора для создания обещания")
            promise = Promise(
                company_id=self.company_id or 1,
                contract_id=item.contract_id,
                promise_date=data.promise_date,
                amount=data.promise_amount,
                status="active",
                notes=f"Создано из call queue #{item.id}",
                created_by_id=manager.id,
            )
            self.db.add(promise)
            await self.db.flush()
            promise_id = promise.id
            message = f"Обещание #{promise_id} создано на {data.promise_date} ({data.promise_amount} ₸)"

        elif data.outcome == CALL_OUTCOME_CALLBACK:
            item.status = QUEUE_ITEM_STATUS_COMPLETED
            item.completed_at = now
            if not data.callback_at:
                raise HTTPException(400, "Для callback нужна дата")
            task = Task(
                company_id=self.company_id or 1,
                title="Перезвонить должнику",
                description=data.notes or "Должник просил перезвонить",
                type="callback",
                priority="normal",
                status="open",
                due_date=data.callback_at,
                assignee_id=manager.id,
                debtor_id=item.debtor_id,
                contract_id=item.contract_id,
                created_by_id=manager.id,
            )
            self.db.add(task)
            await self.db.flush()
            task_id = task.id
            message = f"Создана задача #{task_id} перезвонить {data.callback_at:%Y-%m-%d %H:%M}"

        elif data.outcome == CALL_OUTCOME_WRONG_NUMBER:
            # Помечаем проблемный контакт в notes должника
            item.status = QUEUE_ITEM_STATUS_COMPLETED
            item.completed_at = now
            debtor = await self.db.get(Debtor, item.debtor_id)
            if debtor:
                marker = f"[!{now:%Y-%m-%d}] WRONG_NUMBER: {data.phone_number or 'phone'} — manager {manager.full_name}"
                debtor.notes = (debtor.notes + "\n" if debtor.notes else "") + marker
            message = "Контакт помечен как неверный номер"

        else:
            # reached / refused
            item.status = QUEUE_ITEM_STATUS_COMPLETED
            item.completed_at = now
            message = "Звонок завершён"

        await self.db.commit()
        await self.db.refresh(item)
        return {
            "item_id": item.id,
            "new_status": item.status,
            "next_attempt_at": item.next_attempt_at,
            "promise_id": promise_id,
            "task_id": task_id,
            "message": message,
        }

    # ============ Manager progress ============
    async def manager_progress(self, manager_id: int) -> dict:
        today_start = datetime.combine(date.today(), datetime.min.time())

        base = select(func.count(CallQueueItem.id)).where(
            CallQueueItem.assigned_manager_id == manager_id
        )
        if self.company_id is not None:
            base = base.where(CallQueueItem.company_id == self.company_id)

        total = (await self.db.execute(base)).scalar() or 0
        pending = (await self.db.execute(
            base.where(CallQueueItem.status.in_([QUEUE_ITEM_STATUS_PENDING, QUEUE_ITEM_STATUS_SCHEDULED]))
        )).scalar() or 0
        completed_today = (await self.db.execute(
            base.where(CallQueueItem.completed_at >= today_start)
        )).scalar() or 0

        clog_q = select(CallLog.outcome, func.count()).where(
            CallLog.manager_id == manager_id,
            CallLog.called_at >= today_start,
        )
        if self.company_id is not None:
            clog_q = clog_q.where(CallLog.company_id == self.company_id)
        clog_q = clog_q.group_by(CallLog.outcome)
        rows = (await self.db.execute(clog_q)).all()
        by_outcome = {r[0]: r[1] for r in rows if r[0]}

        manager = await self.db.get(User, manager_id)
        return {
            "manager_id": manager_id,
            "manager_name": manager.full_name if manager else "",
            "total_assigned": total,
            "completed_today": completed_today,
            "reached_today": by_outcome.get(CALL_OUTCOME_REACHED, 0),
            "not_reached_today": by_outcome.get(CALL_OUTCOME_NOT_REACHED, 0),
            "promises_today": by_outcome.get(CALL_OUTCOME_PROMISE, 0),
            "pending": pending,
        }

    async def all_managers_progress(self) -> list[dict]:
        mq = select(User.id).where(User.role == "MANAGER", User.is_active == True)
        if self.company_id is not None:
            mq = mq.where(User.company_id == self.company_id)
        ids = list((await self.db.execute(mq)).scalars().all())
        return [await self.manager_progress(mid) for mid in ids]

    # ============ Dashboard stats ============
    async def dashboard_call_stats(self) -> dict:
        """Сводная статистика звонков на сегодня для дашборда."""
        today_start = datetime.combine(date.today(), datetime.min.time())
        clog_q = select(CallLog.outcome, func.count()).where(CallLog.called_at >= today_start)
        if self.company_id is not None:
            clog_q = clog_q.where(CallLog.company_id == self.company_id)
        clog_q = clog_q.group_by(CallLog.outcome)
        rows = (await self.db.execute(clog_q)).all()
        by_outcome = {r[0]: r[1] for r in rows if r[0]}

        total_calls = sum(by_outcome.values())
        reached = by_outcome.get(CALL_OUTCOME_REACHED, 0) + by_outcome.get(CALL_OUTCOME_PROMISE, 0)
        not_reached = by_outcome.get(CALL_OUTCOME_NOT_REACHED, 0)
        promises = by_outcome.get(CALL_OUTCOME_PROMISE, 0)
        reach_rate = round((reached / total_calls) * 100, 1) if total_calls else 0

        return {
            "total_calls_today": total_calls,
            "reached_today": reached,
            "not_reached_today": not_reached,
            "promises_after_call_today": promises,
            "reach_rate_percent": reach_rate,
        }
