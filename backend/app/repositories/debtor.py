from typing import Optional, Sequence
from sqlalchemy import select, func, or_, and_, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.debtor import Debtor
from app.models.contract import Contract
from app.models.operations import Assignment
from app.repositories.base import BaseRepository


class DebtorRepository(BaseRepository[Debtor]):
    def __init__(self, db: AsyncSession):
        super().__init__(Debtor, db)

    async def get_with_contracts(self, debtor_id: int) -> Optional[Debtor]:
        result = await self.db.execute(
            select(Debtor)
            .options(selectinload(Debtor.contracts))
            .where(Debtor.id == debtor_id)
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        contract_status: Optional[str] = None,
        manager_id: Optional[int] = None,
        debt_min: Optional[float] = None,
        debt_max: Optional[float] = None,
        skip: int = 0,
        limit: int = 20,
        company_id: Optional[int] = None,
    ) -> tuple[Sequence[Debtor], int]:
        query = select(Debtor).distinct()
        count_query = select(func.count(func.distinct(Debtor.id)))

        filters = []

        # Tenant isolation
        if company_id is not None:
            filters.append(Debtor.company_id == company_id)

        # Exclude soft-deleted
        filters.append(Debtor.deleted_at.is_(None))

        if search:
            filters.append(or_(
                Debtor.full_name.ilike(f"%{search}%"),
                Debtor.iin.ilike(f"%{search}%"),
                Debtor.phone_primary.ilike(f"%{search}%"),
            ))

        if is_active is not None:
            filters.append(Debtor.is_active == is_active)

        # Filter by contract status or debt amount — join contracts
        if contract_status or debt_min is not None or debt_max is not None:
            query = query.join(Contract, Contract.debtor_id == Debtor.id)
            count_query = count_query.select_from(Debtor).join(Contract, Contract.debtor_id == Debtor.id)
            if contract_status:
                filters.append(Contract.status == contract_status)
            if debt_min is not None:
                filters.append(Contract.total_debt >= debt_min)
            if debt_max is not None:
                filters.append(Contract.total_debt <= debt_max)

        # Filter by assigned manager
        if manager_id is not None:
            manager_subq = (
                select(Assignment.contract_id)
                .join(Contract, Contract.id == Assignment.contract_id)
                .where(
                    and_(
                        Assignment.manager_id == manager_id,
                        Assignment.is_active == True,
                    )
                )
            )
            if not (contract_status or debt_min is not None or debt_max is not None):
                query = query.join(Contract, Contract.debtor_id == Debtor.id)
                count_query = count_query.select_from(Debtor).join(Contract, Contract.debtor_id == Debtor.id)
            filters.append(Contract.id.in_(manager_subq))

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        result = await self.db.execute(
            query.offset(skip).limit(limit).order_by(Debtor.id.desc())
        )
        return result.scalars().all(), total

    async def get_by_iin(self, iin: str) -> Optional[Debtor]:
        result = await self.db.execute(select(Debtor).where(Debtor.iin == iin))
        return result.scalar_one_or_none()
