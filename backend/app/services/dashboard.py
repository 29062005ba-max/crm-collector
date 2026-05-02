from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import date, timedelta
from app.models.contract import Contract, ContractStatus
from app.models.operations import Promise, PromiseStatus, Payment, CallLog
from app.models.debtor import Debtor
from app.models.user import User


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(self) -> dict:
        today = date.today()
        month_start = today.replace(day=1)

        # Total debtors
        total_debtors = await self.db.execute(select(func.count(Debtor.id)).where(Debtor.is_active == True))

        # Active contracts
        active_contracts = await self.db.execute(
            select(func.count(Contract.id)).where(Contract.status == ContractStatus.ACTIVE)
        )

        # Total debt
        total_debt = await self.db.execute(
            select(func.sum(Contract.total_debt)).where(Contract.status == ContractStatus.ACTIVE)
        )

        # Payments this month
        payments_month = await self.db.execute(
            select(func.sum(Payment.amount)).where(Payment.payment_date >= month_start)
        )

        # Active promises
        active_promises = await self.db.execute(
            select(func.count(Promise.id)).where(Promise.status == PromiseStatus.ACTIVE)
        )

        # Overdue promises
        overdue_promises = await self.db.execute(
            select(func.count(Promise.id)).where(Promise.status == PromiseStatus.OVERDUE)
        )

        # Calls today
        calls_today = await self.db.execute(
            select(func.count(CallLog.id)).where(
                func.date(CallLog.called_at) == today
            )
        )

        # Payments count this month
        payments_count = await self.db.execute(
            select(func.count(Payment.id)).where(Payment.payment_date >= month_start)
        )

        return {
            "total_debtors": total_debtors.scalar_one() or 0,
            "active_contracts": active_contracts.scalar_one() or 0,
            "total_debt": float(total_debt.scalar_one() or 0),
            "payments_this_month": float(payments_month.scalar_one() or 0),
            "payments_count_this_month": payments_count.scalar_one() or 0,
            "active_promises": active_promises.scalar_one() or 0,
            "overdue_promises": overdue_promises.scalar_one() or 0,
            "calls_today": calls_today.scalar_one() or 0,
        }

    async def get_payments_by_day(self, days: int = 30) -> list[dict]:
        start_date = date.today() - timedelta(days=days)
        result = await self.db.execute(
            select(Payment.payment_date, func.sum(Payment.amount).label("total"))
            .where(Payment.payment_date >= start_date)
            .group_by(Payment.payment_date)
            .order_by(Payment.payment_date)
        )
        return [{"date": str(row.payment_date), "amount": float(row.total)} for row in result.all()]

    async def get_top_managers(self) -> list[dict]:
        result = await self.db.execute(
            select(
                User.full_name,
                func.count(Payment.id).label("payments_count"),
                func.sum(Payment.amount).label("total_collected"),
            )
            .join(Payment, Payment.registered_by_id == User.id)
            .group_by(User.id, User.full_name)
            .order_by(func.sum(Payment.amount).desc())
            .limit(10)
        )
        return [
            {
                "manager": row.full_name,
                "payments_count": row.payments_count,
                "total_collected": float(row.total_collected or 0),
            }
            for row in result.all()
        ]
