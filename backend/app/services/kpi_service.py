"""
KPI менеджеров:
- Кол-во и сумма платежей за период
- Кол-во звонков
- Обещания: выполненные / просроченные
- Процент сбора (факт/план)
- Коэффициент эффективности звонков (дозвон / всего)
"""
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from app.models.user import User
from app.models.operations import Assignment, CallLog, Promise, PromiseStatus, Payment, CallResult
from app.models.contract import Contract


class KpiService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_kpi(self, date_from: date, date_to: date) -> list[dict]:
        managers = await self._get_managers()
        result = []
        for m in managers:
            kpi = await self._manager_kpi(m, date_from, date_to)
            result.append(kpi)
        # Сортируем по сумме сборов убыванию
        result.sort(key=lambda x: x["payments_amount"], reverse=True)
        return result

    async def _manager_kpi(self, manager: User, date_from: date, date_to: date) -> dict:
        mid = manager.id

        # Платежи за период
        pay_q = await self.db.execute(
            select(
                func.count(Payment.id).label("cnt"),
                func.coalesce(func.sum(Payment.amount), 0).label("total"),
            ).where(
                and_(
                    Payment.registered_by_id == mid,
                    Payment.payment_date >= date_from,
                    Payment.payment_date <= date_to,
                )
            )
        )
        pay = pay_q.one()

        # Звонки за период
        calls_q = await self.db.execute(
            select(
                func.count(CallLog.id).label("total"),
                func.sum(
                    case((CallLog.result == "reached", 1), else_=0)
                ).label("reached"),
            ).where(
                and_(
                    CallLog.manager_id == mid,
                    func.date(CallLog.called_at) >= date_from,
                    func.date(CallLog.called_at) <= date_to,
                )
            )
        )
        calls = calls_q.one()

        # Обещания созданные менеджером
        promises_q = await self.db.execute(
            select(
                func.count(Promise.id).label("total"),
                func.sum(case((Promise.status == "done", 1), else_=0)).label("done"),
                func.sum(case((Promise.status == "overdue", 1), else_=0)).label("overdue"),
                func.sum(case((Promise.status == "active", 1), else_=0)).label("active"),
            ).where(Promise.created_by_id == mid)
        )
        promises = promises_q.one()

        # Кол-во активных договоров у менеджера
        contracts_q = await self.db.execute(
            select(func.count(Assignment.id)).where(
                and_(
                    Assignment.manager_id == mid,
                    Assignment.is_active == True,
                )
            )
        )
        contracts_count = contracts_q.scalar_one() or 0

        total_calls = int(calls.total or 0)
        reached = int(calls.reached or 0)
        contact_rate = round(reached / total_calls * 100, 1) if total_calls > 0 else 0.0

        total_promises = int(promises.total or 0)
        done_promises = int(promises.done or 0)
        promise_kept_rate = round(done_promises / total_promises * 100, 1) if total_promises > 0 else 0.0

        return {
            "manager_id": mid,
            "manager_name": manager.full_name,
            "role": manager.role,
            "contracts_count": contracts_count,
            # Платежи
            "payments_count": int(pay.cnt or 0),
            "payments_amount": float(pay.total or 0),
            # Звонки
            "calls_total": total_calls,
            "calls_reached": reached,
            "contact_rate": contact_rate,
            # Обещания
            "promises_total": total_promises,
            "promises_done": done_promises,
            "promises_overdue": int(promises.overdue or 0),
            "promises_active": int(promises.active or 0),
            "promise_kept_rate": promise_kept_rate,
        }

    async def _get_managers(self) -> list[User]:
        result = await self.db.execute(
            select(User).where(
                and_(User.is_active == True, User.role.in_(["MANAGER", "HEAD"]))
            )
        )
        return list(result.scalars().all())
