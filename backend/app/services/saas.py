"""Business logic services for SaaS features (tenant-aware)"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, Any
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import (
    User, Debtor, Contract, Promise, Payment,
    Task, Notification, ActivityLog, PaymentSchedule, SchedulePayment,
)


# ==================== Task Service ====================
class TaskService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.company_id = company_id

    def _apply_tenant(self, q):
        if self.company_id is not None:
            q = q.where(Task.company_id == self.company_id)
        return q

    async def create(self, data, created_by_id: int) -> Task:
        kwargs = dict(
            title=data.title,
            description=data.description,
            type=data.type,
            priority=data.priority,
            due_date=data.due_date,
            assignee_id=data.assignee_id,
            debtor_id=data.debtor_id,
            contract_id=data.contract_id,
            created_by_id=created_by_id,
        )
        if self.company_id is not None:
            kwargs["company_id"] = self.company_id
        task = Task(**kwargs)
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def list_for_user(self, user_id: int, status: str | None = None, only_assigned: bool = True) -> list[dict]:
        q = select(Task, Debtor.full_name, Contract.contract_number, User.full_name.label("assignee_name")) \
            .outerjoin(Debtor, Task.debtor_id == Debtor.id) \
            .outerjoin(Contract, Task.contract_id == Contract.id) \
            .outerjoin(User, Task.assignee_id == User.id)
        if only_assigned:
            q = q.where(Task.assignee_id == user_id)
        if status:
            q = q.where(Task.status == status)
        q = self._apply_tenant(q)
        q = q.order_by(Task.priority.desc(), Task.due_date.asc().nullslast(), Task.created_at.desc())
        rows = (await self.db.execute(q)).all()
        result = []
        for task, debtor_name, contract_number, assignee_name in rows:
            result.append({
                **{c.name: getattr(task, c.name) for c in task.__table__.columns},
                "debtor_name": debtor_name,
                "contract_number": contract_number,
                "assignee_name": assignee_name,
            })
        return result

    async def update(self, task_id: int, data) -> Task | None:
        q = select(Task).where(Task.id == task_id)
        q = self._apply_tenant(q)
        task = (await self.db.execute(q)).scalar_one_or_none()
        if not task:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(task, field, value)
        if data.status == "done" and not task.completed_at:
            task.completed_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete(self, task_id: int) -> bool:
        q = select(Task).where(Task.id == task_id)
        q = self._apply_tenant(q)
        task = (await self.db.execute(q)).scalar_one_or_none()
        if not task:
            return False
        await self.db.delete(task)
        await self.db.commit()
        return True


# ==================== Notification Service ====================
class NotificationService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.company_id = company_id

    def _apply_tenant(self, q):
        if self.company_id is not None:
            q = q.where(Notification.company_id == self.company_id)
        return q

    async def create(self, user_id: int, type: str, title: str, message: str = None,
                     link: str = None, debtor_id: int = None, task_id: int = None,
                     company_id: int | None = None) -> Notification:
        cid = company_id if company_id is not None else self.company_id
        kwargs = dict(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            link=link,
            related_debtor_id=debtor_id,
            related_task_id=task_id,
        )
        if cid is not None:
            kwargs["company_id"] = cid
        notif = Notification(**kwargs)
        self.db.add(notif)
        await self.db.commit()
        await self.db.refresh(notif)
        return notif

    async def list_for_user(self, user_id: int, unread_only: bool = False, limit: int = 50) -> list[Notification]:
        q = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            q = q.where(Notification.is_read == False)
        q = self._apply_tenant(q)
        q = q.order_by(Notification.created_at.desc()).limit(limit)
        return (await self.db.execute(q)).scalars().all()

    async def unread_count(self, user_id: int) -> int:
        q = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
        q = self._apply_tenant(q)
        return (await self.db.execute(q)).scalar() or 0

    async def mark_read(self, notif_id: int, user_id: int) -> bool:
        q = select(Notification).where(Notification.id == notif_id)
        q = self._apply_tenant(q)
        notif = (await self.db.execute(q)).scalar_one_or_none()
        if not notif or notif.user_id != user_id:
            return False
        notif.is_read = True
        await self.db.commit()
        return True

    async def mark_all_read(self, user_id: int) -> int:
        from sqlalchemy import update as sql_update
        stmt = sql_update(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
        if self.company_id is not None:
            stmt = stmt.where(Notification.company_id == self.company_id)
        stmt = stmt.values(is_read=True)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount


# ==================== Activity Log Service ====================
class ActivityLogService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.company_id = company_id

    def _apply_tenant(self, q):
        if self.company_id is not None:
            q = q.where(ActivityLog.company_id == self.company_id)
        return q

    async def log(self, actor_id: int | None, action: str, entity_type: str,
                  entity_id: int | None = None, description: str = None,
                  changes: dict = None, debtor_id: int | None = None,
                  ip_address: str | None = None,
                  old_value: dict | None = None,
                  new_value: dict | None = None,
                  company_id: int | None = None) -> ActivityLog:
        cid = company_id if company_id is not None else self.company_id
        kwargs = dict(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            changes=changes,
            debtor_id=debtor_id,
            ip_address=ip_address,
            old_value=old_value,
            new_value=new_value,
        )
        if cid is not None:
            kwargs["company_id"] = cid
        log = ActivityLog(**kwargs)
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def list_for_debtor(self, debtor_id: int, limit: int = 100) -> list[dict]:
        q = select(ActivityLog, User.full_name) \
            .outerjoin(User, ActivityLog.actor_id == User.id) \
            .where(ActivityLog.debtor_id == debtor_id)
        q = self._apply_tenant(q)
        q = q.order_by(ActivityLog.created_at.desc()).limit(limit)
        rows = (await self.db.execute(q)).all()
        return [
            {**{c.name: getattr(log, c.name) for c in log.__table__.columns}, "actor_name": actor_name}
            for log, actor_name in rows
        ]

    async def list_recent(self, limit: int = 100, debtor_id: int | None = None) -> list[dict]:
        q = select(ActivityLog, User.full_name) \
            .outerjoin(User, ActivityLog.actor_id == User.id)
        if debtor_id:
            q = q.where(ActivityLog.debtor_id == debtor_id)
        q = self._apply_tenant(q)
        q = q.order_by(ActivityLog.created_at.desc()).limit(limit)
        rows = (await self.db.execute(q)).all()
        return [
            {**{c.name: getattr(log, c.name) for c in log.__table__.columns}, "actor_name": actor_name}
            for log, actor_name in rows
        ]


# ==================== Payment Schedule Service ====================
class PaymentScheduleService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.company_id = company_id

    async def create(self, data, created_by_id: int) -> PaymentSchedule:
        kwargs = dict(
            contract_id=data.contract_id,
            total_amount=data.total_amount,
            down_payment=data.down_payment,
            months=data.months,
            monthly_payment=data.monthly_payment,
            start_date=data.start_date,
            notes=data.notes,
            created_by_id=created_by_id,
        )
        if self.company_id is not None:
            kwargs["company_id"] = self.company_id
        schedule = PaymentSchedule(**kwargs)
        self.db.add(schedule)
        await self.db.flush()

        remaining = float(data.total_amount) - float(data.down_payment)
        for i in range(1, data.months + 1):
            due = data.start_date + timedelta(days=30 * i)
            amount = float(data.monthly_payment) if i < data.months else remaining
            remaining -= amount
            sp = SchedulePayment(
                schedule_id=schedule.id,
                payment_number=i,
                due_date=due,
                amount=Decimal(str(round(amount, 2))),
            )
            self.db.add(sp)

        # Update contract status to "graph"
        contract = await self.db.get(Contract, data.contract_id)
        if contract:
            contract.status = "graph"
            debtor = await self.db.get(Debtor, contract.debtor_id)
            if debtor:
                debtor.kanban_status = "schedule"

        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def get_for_contract(self, contract_id: int) -> PaymentSchedule | None:
        q = select(PaymentSchedule).where(
            PaymentSchedule.contract_id == contract_id,
            PaymentSchedule.status == "active",
        )
        if self.company_id is not None:
            q = q.where(PaymentSchedule.company_id == self.company_id)
        q = q.options(selectinload(PaymentSchedule.payments))
        return (await self.db.execute(q)).scalar_one_or_none()

    async def mark_payment(self, payment_id: int, paid_amount: Decimal) -> SchedulePayment | None:
        sp = await self.db.get(SchedulePayment, payment_id)
        if not sp:
            return None
        # Tenant check via parent schedule
        if self.company_id is not None:
            parent = await self.db.get(PaymentSchedule, sp.schedule_id)
            if not parent or parent.company_id != self.company_id:
                return None
        sp.paid_amount = paid_amount
        sp.paid_at = date.today()
        if paid_amount >= sp.amount:
            sp.status = "paid"
        elif paid_amount > 0:
            sp.status = "partial"
        await self.db.commit()
        await self.db.refresh(sp)
        return sp


# ==================== Workflow Engine ====================
class WorkflowService:
    """Auto-process overdue promises, schedules, etc — within current tenant if specified"""
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.company_id = company_id
        self.notif_svc = NotificationService(db, company_id=company_id)
        self.task_svc = TaskService(db, company_id=company_id)
        self.log_svc = ActivityLogService(db, company_id=company_id)

    async def process_overdue_promises(self) -> int:
        today = date.today()
        q = select(Promise).where(
            Promise.status == "active",
            Promise.promise_date < today,
        )
        if self.company_id is not None:
            q = q.where(Promise.company_id == self.company_id)
        overdue_list = (await self.db.execute(q)).scalars().all()
        count = 0
        for promise in overdue_list:
            promise.status = "overdue"
            count += 1
            contract = await self.db.get(Contract, promise.contract_id)
            if not contract:
                continue
            debtor = await self.db.get(Debtor, contract.debtor_id)
            if not debtor:
                continue
            if debtor.kanban_status not in ("paid", "overdue"):
                debtor.kanban_status = "overdue"

            # Create task for assigned manager
            if debtor.assigned_manager_id:
                task_kwargs = dict(
                    title=f"Сорванное обещание: {debtor.full_name}",
                    description=f"Обещание на {promise.amount} от {promise.promise_date} не выполнено",
                    type="followup",
                    priority="high",
                    due_date=datetime.utcnow() + timedelta(days=1),
                    assignee_id=debtor.assigned_manager_id,
                    debtor_id=debtor.id,
                    contract_id=contract.id,
                )
                if debtor.company_id:
                    task_kwargs["company_id"] = debtor.company_id
                self.db.add(Task(**task_kwargs))

                notif_kwargs = dict(
                    user_id=debtor.assigned_manager_id,
                    type="promise_overdue",
                    title="Сорванное обещание",
                    message=f"Должник {debtor.full_name} не выполнил обещание на {promise.amount}",
                    link=f"/debtors/{debtor.id}",
                    related_debtor_id=debtor.id,
                )
                if debtor.company_id:
                    notif_kwargs["company_id"] = debtor.company_id
                self.db.add(Notification(**notif_kwargs))

            # Notify admins/heads of same company
            admin_q = select(User).where(
                User.role.in_(["ADMIN", "HEAD"]),
                User.is_active == True,
            )
            if debtor.company_id:
                admin_q = admin_q.where(User.company_id == debtor.company_id)
            admins = (await self.db.execute(admin_q)).scalars().all()
            for admin in admins:
                an_kwargs = dict(
                    user_id=admin.id,
                    type="promise_overdue",
                    title="Сорванное обещание",
                    message=f"Должник {debtor.full_name} - {promise.amount}",
                    link=f"/debtors/{debtor.id}",
                    related_debtor_id=debtor.id,
                )
                if debtor.company_id:
                    an_kwargs["company_id"] = debtor.company_id
                self.db.add(Notification(**an_kwargs))

            log_kwargs = dict(
                action="status_changed",
                entity_type="promise",
                entity_id=promise.id,
                description=f"Promise marked overdue (amount: {promise.amount})",
                debtor_id=debtor.id,
                changes={"status": ["active", "overdue"]},
            )
            if debtor.company_id:
                log_kwargs["company_id"] = debtor.company_id
            self.db.add(ActivityLog(**log_kwargs))
        await self.db.commit()
        return count

    async def process_overdue_schedules(self) -> int:
        today = date.today()
        q = select(SchedulePayment, PaymentSchedule.company_id).join(
            PaymentSchedule, PaymentSchedule.id == SchedulePayment.schedule_id
        ).where(
            SchedulePayment.status == "pending",
            SchedulePayment.due_date < today,
        )
        if self.company_id is not None:
            q = q.where(PaymentSchedule.company_id == self.company_id)
        rows = (await self.db.execute(q)).all()
        count = 0
        affected_schedules = set()
        for sp, _cid in rows:
            sp.status = "overdue"
            count += 1
            affected_schedules.add(sp.schedule_id)

        for sched_id in affected_schedules:
            schedule = await self.db.get(PaymentSchedule, sched_id)
            if not schedule:
                continue
            contract = await self.db.get(Contract, schedule.contract_id)
            if not contract:
                continue
            debtor = await self.db.get(Debtor, contract.debtor_id)
            if not debtor:
                continue
            if debtor.kanban_status != "paid":
                debtor.kanban_status = "overdue"

            if debtor.assigned_manager_id:
                notif_kwargs = dict(
                    user_id=debtor.assigned_manager_id,
                    type="schedule_overdue",
                    title="Просрочка по графику",
                    message=f"Должник {debtor.full_name} пропустил платёж по графику",
                    link=f"/debtors/{debtor.id}",
                    related_debtor_id=debtor.id,
                )
                if debtor.company_id:
                    notif_kwargs["company_id"] = debtor.company_id
                self.db.add(Notification(**notif_kwargs))

                task_kwargs = dict(
                    title=f"Просрочка графика: {debtor.full_name}",
                    description=f"Срочно связаться по поводу пропущенного платежа",
                    type="followup",
                    priority="urgent",
                    due_date=datetime.utcnow() + timedelta(days=1),
                    assignee_id=debtor.assigned_manager_id,
                    debtor_id=debtor.id,
                    contract_id=contract.id,
                )
                if debtor.company_id:
                    task_kwargs["company_id"] = debtor.company_id
                self.db.add(Task(**task_kwargs))
        await self.db.commit()
        return count


# ==================== Dashboard KPI Service ====================
class DashboardKPIService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.company_id = company_id

    async def get_dashboard_kpi(self) -> dict:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        debt_q = select(func.count(Debtor.id)).where(
            Debtor.is_active == True,
            Debtor.deleted_at.is_(None),
        )
        if self.company_id is not None:
            debt_q = debt_q.where(Debtor.company_id == self.company_id)
        total_debtors = (await self.db.execute(debt_q)).scalar() or 0

        kanban_q = select(Debtor.kanban_status, func.count(Debtor.id)).where(
            Debtor.is_active == True,
            Debtor.deleted_at.is_(None),
        )
        if self.company_id is not None:
            kanban_q = kanban_q.where(Debtor.company_id == self.company_id)
        kanban_q = kanban_q.group_by(Debtor.kanban_status)
        kanban_rows = (await self.db.execute(kanban_q)).all()
        debtors_by_kanban = {status or "new": count for status, count in kanban_rows}

        prom_q = select(func.count(Promise.id), func.coalesce(func.sum(Promise.amount), 0)) \
            .where(Promise.promise_date == today, Promise.status == "active")
        if self.company_id is not None:
            prom_q = prom_q.where(Promise.company_id == self.company_id)
        promises_today = (await self.db.execute(prom_q)).first()
        promises_today_count = promises_today[0] or 0
        promises_today_amount = promises_today[1] or Decimal(0)

        ovr_q = select(func.count(Promise.id)).where(Promise.status == "overdue")
        if self.company_id is not None:
            ovr_q = ovr_q.where(Promise.company_id == self.company_id)
        overdue_promises = (await self.db.execute(ovr_q)).scalar() or 0

        sched_q = select(func.count(PaymentSchedule.id)).where(PaymentSchedule.status == "active")
        if self.company_id is not None:
            sched_q = sched_q.where(PaymentSchedule.company_id == self.company_id)
        active_schedules = (await self.db.execute(sched_q)).scalar() or 0

        ovs_q = select(func.count(func.distinct(SchedulePayment.schedule_id))) \
            .join(PaymentSchedule, PaymentSchedule.id == SchedulePayment.schedule_id) \
            .where(SchedulePayment.status == "overdue")
        if self.company_id is not None:
            ovs_q = ovs_q.where(PaymentSchedule.company_id == self.company_id)
        overdue_schedules = (await self.db.execute(ovs_q)).scalar() or 0

        def _payment_q(date_filter):
            q = select(func.coalesce(func.sum(Payment.amount), 0)).where(date_filter)
            if self.company_id is not None:
                q = q.where(Payment.company_id == self.company_id)
            return q

        payments_today = (await self.db.execute(_payment_q(Payment.payment_date == today))).scalar() or Decimal(0)
        payments_week = (await self.db.execute(_payment_q(Payment.payment_date >= week_start))).scalar() or Decimal(0)
        payments_month = (await self.db.execute(_payment_q(Payment.payment_date >= month_start))).scalar() or Decimal(0)

        thirty_days_ago = today - timedelta(days=30)
        daily_q = select(
            Payment.payment_date,
            func.coalesce(func.sum(Payment.amount), 0),
            func.count(Payment.id),
        ).where(Payment.payment_date >= thirty_days_ago)
        if self.company_id is not None:
            daily_q = daily_q.where(Payment.company_id == self.company_id)
        daily_q = daily_q.group_by(Payment.payment_date).order_by(Payment.payment_date)
        daily_rows = (await self.db.execute(daily_q)).all()
        daily_collections = [
            {"date": d.isoformat(), "amount": float(amt), "count": cnt}
            for d, amt, cnt in daily_rows
        ]

        return {
            "total_debtors": total_debtors,
            "debtors_by_kanban": debtors_by_kanban,
            "promises_today": promises_today_count,
            "promises_today_amount": float(promises_today_amount),
            "promises_overdue": overdue_promises,
            "active_schedules": active_schedules,
            "overdue_schedules": overdue_schedules,
            "payments_today": float(payments_today),
            "payments_this_week": float(payments_week),
            "payments_this_month": float(payments_month),
            "daily_collections": daily_collections,
        }

    async def get_managers_kpi(self) -> list[dict]:
        today = date.today()
        month_start = today.replace(day=1)

        managers_q = select(User).where(
            User.role.in_(["MANAGER", "HEAD"]),
            User.is_active == True,
        )
        if self.company_id is not None:
            managers_q = managers_q.where(User.company_id == self.company_id)
        managers = (await self.db.execute(managers_q)).scalars().all()

        result = []
        for m in managers:
            # Debtors assigned to this manager (within tenant)
            dq = select(func.count(Debtor.id)).where(
                Debtor.assigned_manager_id == m.id,
                Debtor.deleted_at.is_(None),
            )
            if self.company_id is not None:
                dq = dq.where(Debtor.company_id == self.company_id)
            debtors_count = (await self.db.execute(dq)).scalar() or 0

            def _prom_q(status):
                q = select(func.count(Promise.id)).where(
                    Promise.created_by_id == m.id,
                    Promise.status == status,
                )
                if self.company_id is not None:
                    q = q.where(Promise.company_id == self.company_id)
                return q

            active_promises = (await self.db.execute(_prom_q("active"))).scalar() or 0
            overdue = (await self.db.execute(_prom_q("overdue"))).scalar() or 0
            kept = (await self.db.execute(_prom_q("done"))).scalar() or 0
            total_promises = active_promises + overdue + kept
            completion_rate = round((kept / total_promises * 100) if total_promises > 0 else 0, 1)

            pq = select(
                func.coalesce(func.sum(Payment.amount), 0),
                func.count(Payment.id),
            ).where(
                Payment.registered_by_id == m.id,
                Payment.payment_date >= month_start,
            )
            if self.company_id is not None:
                pq = pq.where(Payment.company_id == self.company_id)
            pay_amt, pay_cnt = (await self.db.execute(pq)).first()

            result.append({
                "manager_id": m.id,
                "manager_name": m.full_name,
                "debtors_count": debtors_count,
                "active_promises": active_promises,
                "overdue_promises": overdue,
                "promises_kept_count": kept,
                "payments_this_month": float(pay_amt or 0),
                "payments_count": pay_cnt or 0,
                "active_schedules": 0,
                "overdue_schedules": 0,
                "completion_rate": completion_rate,
            })
        result.sort(key=lambda x: x["payments_this_month"], reverse=True)
        return result
