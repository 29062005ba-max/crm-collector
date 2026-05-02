from typing import Optional, Sequence
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.contract import Contract
from app.repositories.base import BaseRepository


class ContractRepository(BaseRepository[Contract]):
    def __init__(self, db: AsyncSession):
        super().__init__(Contract, db)

    async def get_by_debtor(self, debtor_id: int) -> Sequence[Contract]:
        result = await self.db.execute(
            select(Contract)
            .where(Contract.debtor_id == debtor_id)
            .order_by(Contract.created_at.desc())
        )
        return result.scalars().all()

    async def get_with_relations(self, contract_id: int) -> Optional[Contract]:
        result = await self.db.execute(
            select(Contract)
            .options(
                selectinload(Contract.promises),
                selectinload(Contract.payments),
                selectinload(Contract.call_logs),
                selectinload(Contract.assignments),
            )
            .where(Contract.id == contract_id)
        )
        return result.scalar_one_or_none()

    async def get_by_number(self, contract_number: str) -> Optional[Contract]:
        result = await self.db.execute(
            select(Contract).where(Contract.contract_number == contract_number)
        )
        return result.scalar_one_or_none()
