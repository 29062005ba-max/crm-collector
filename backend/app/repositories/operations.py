from typing import Sequence
from datetime import date
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.operations import Promise, PromiseStatus, Payment, CallLog, CsiCase
from app.repositories.base import BaseRepository


class PromiseRepository(BaseRepository[Promise]):
    def __init__(self, db: AsyncSession):
        super().__init__(Promise, db)

    async def get_by_contract(self, contract_id: int) -> Sequence[Promise]:
        result = await self.db.execute(
            select(Promise).where(Promise.contract_id == contract_id).order_by(Promise.promise_date.desc())
        )
        return result.scalars().all()

    async def get_active(self) -> Sequence[Promise]:
        result = await self.db.execute(
            select(Promise).where(Promise.status == PromiseStatus.ACTIVE)
        )
        return result.scalars().all()

    async def mark_overdue(self, company_id: int | None = None) -> int:
        today = date.today()
        conditions = [
            Promise.status == PromiseStatus.ACTIVE,
            Promise.promise_date < today,
        ]
        if company_id is not None:
            conditions.append(Promise.company_id == company_id)
        stmt = (
            update(Promise)
            .where(and_(*conditions))
            .values(status=PromiseStatus.OVERDUE)
        )
        result = await self.db.execute(stmt)
        return result.rowcount


class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, db: AsyncSession):
        super().__init__(Payment, db)

    async def get_by_contract(self, contract_id: int) -> Sequence[Payment]:
        result = await self.db.execute(
            select(Payment).where(Payment.contract_id == contract_id).order_by(Payment.payment_date.desc())
        )
        return result.scalars().all()

    async def get_total_for_contract(self, contract_id: int) -> float:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.sum(Payment.amount)).where(Payment.contract_id == contract_id)
        )
        return float(result.scalar_one() or 0)


class CallLogRepository(BaseRepository[CallLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(CallLog, db)

    async def get_by_contract(self, contract_id: int) -> Sequence[CallLog]:
        result = await self.db.execute(
            select(CallLog).where(CallLog.contract_id == contract_id).order_by(CallLog.called_at.desc())
        )
        return result.scalars().all()


class CsiCaseRepository(BaseRepository[CsiCase]):
    def __init__(self, db: AsyncSession):
        super().__init__(CsiCase, db)

    async def get_by_debtor(self, debtor_id: int) -> Sequence[CsiCase]:
        result = await self.db.execute(
            select(CsiCase).where(CsiCase.debtor_id == debtor_id).order_by(CsiCase.created_at.desc())
        )
        return result.scalars().all()
