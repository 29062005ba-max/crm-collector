from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from datetime import datetime
from app.repositories.debtor import DebtorRepository
from app.schemas.debtor import DebtorCreate, DebtorUpdate, DebtorFilter
from app.models.debtor import Debtor


class DebtorService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.repo = DebtorRepository(db)
        self.company_id = company_id  # tenant context

    async def create(self, data: DebtorCreate, actor_id: int | None = None) -> Debtor:
        existing = await self.repo.get_by_iin(data.iin)
        # If existing belongs to another tenant, treat as new
        if existing and (self.company_id is None or existing.company_id == self.company_id):
            raise HTTPException(status_code=400, detail="Должник с таким ИИН уже существует")
        kwargs = data.model_dump()
        if self.company_id is not None:
            kwargs["company_id"] = self.company_id
        debtor = Debtor(**kwargs)
        debtor = await self.repo.create(debtor)

        # Publish event
        try:
            from app.events import event_bus, DebtorCreated
            await event_bus.publish(
                DebtorCreated(
                    aggregate_id=debtor.id,
                    company_id=self.company_id,
                    actor_id=actor_id,
                    payload={"iin": debtor.iin, "full_name": debtor.full_name},
                ),
                self.db,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to publish DebtorCreated: {e}")

        return debtor

    async def get(self, debtor_id: int) -> Debtor:
        debtor = await self.repo.get_with_contracts(debtor_id)
        if not debtor:
            raise HTTPException(status_code=404, detail="Должник не найден")
        # Tenant check
        if self.company_id is not None and debtor.company_id != self.company_id:
            raise HTTPException(status_code=404, detail="Должник не найден")
        # Soft delete check
        if getattr(debtor, "deleted_at", None) is not None:
            raise HTTPException(status_code=404, detail="Должник не найден")
        return debtor

    async def update(self, debtor_id: int, data: DebtorUpdate) -> Debtor:
        debtor = await self.repo.get(debtor_id)
        if not debtor:
            raise HTTPException(status_code=404, detail="Должник не найден")
        if self.company_id is not None and debtor.company_id != self.company_id:
            raise HTTPException(status_code=404, detail="Должник не найден")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(debtor, field, value)
        return await self.repo.update(debtor)

    async def soft_delete(self, debtor_id: int) -> None:
        debtor = await self.repo.get(debtor_id)
        if not debtor:
            raise HTTPException(status_code=404, detail="Должник не найден")
        if self.company_id is not None and debtor.company_id != self.company_id:
            raise HTTPException(status_code=404, detail="Должник не найден")
        debtor.deleted_at = datetime.utcnow()
        debtor.is_active = False
        await self.db.flush()

    async def list(self, filters: DebtorFilter):
        skip = (filters.page - 1) * filters.page_size
        debtors, total = await self.repo.search(
            search=filters.search,
            is_active=filters.is_active,
            contract_status=filters.contract_status,
            manager_id=filters.manager_id,
            debt_min=filters.debt_min,
            debt_max=filters.debt_max,
            skip=skip,
            limit=filters.page_size,
        )
        pages = (total + filters.page_size - 1) // filters.page_size
        return {"items": debtors, "total": total, "page": filters.page, "page_size": filters.page_size, "pages": pages}

    async def delete(self, debtor_id: int) -> None:
        debtor = await self.repo.get(debtor_id)
        if not debtor:
            raise HTTPException(status_code=404, detail="Должник не найден")
        debtor.is_active = False
        await self.repo.update(debtor)
