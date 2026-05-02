from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.repositories.contract import ContractRepository
from app.repositories.operations import PromiseRepository, PaymentRepository
from app.schemas.operations import ContractCreate, ContractUpdate
from app.models.contract import Contract
from app.models.debtor import Debtor
from app.models.operations import StatusHistory


class ContractService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.repo = ContractRepository(db)
        self.company_id = company_id

    def _check_tenant(self, contract: Contract) -> None:
        """Raise 404 if contract belongs to another tenant"""
        if self.company_id is not None and contract.company_id != self.company_id:
            raise HTTPException(status_code=404, detail="Contract not found")
        if getattr(contract, "deleted_at", None) is not None:
            raise HTTPException(status_code=404, detail="Contract not found")

    async def create(self, data: ContractCreate) -> Contract:
        existing = await self.repo.get_by_number(data.contract_number)
        if existing and (self.company_id is None or existing.company_id == self.company_id):
            raise HTTPException(status_code=400, detail="Contract number already exists")

        # Verify debtor belongs to current tenant
        if self.company_id is not None:
            debtor = await self.db.get(Debtor, data.debtor_id)
            if not debtor or debtor.company_id != self.company_id:
                raise HTTPException(status_code=404, detail="Debtor not found")

        kwargs = data.model_dump()
        if self.company_id is not None:
            kwargs["company_id"] = self.company_id
        contract = Contract(**kwargs)
        return await self.repo.create(contract)

    async def get(self, contract_id: int) -> Contract:
        contract = await self.repo.get_with_relations(contract_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        self._check_tenant(contract)
        return contract

    async def update(self, contract_id: int, data: ContractUpdate, changed_by_id: int) -> Contract:
        contract = await self.repo.get(contract_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        self._check_tenant(contract)

        update_data = data.model_dump(exclude_unset=True)
        old_status = contract.status

        for field, value in update_data.items():
            setattr(contract, field, value)

        if "status" in update_data and update_data["status"] != old_status:
            history = StatusHistory(
                contract_id=contract_id,
                old_status=old_status,
                new_status=update_data["status"],
                changed_by_id=changed_by_id,
            )
            self.db.add(history)

        return await self.repo.update(contract)

    async def soft_delete(self, contract_id: int) -> None:
        contract = await self.repo.get(contract_id)
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        self._check_tenant(contract)
        contract.deleted_at = datetime.utcnow()
        await self.db.flush()

    async def get_by_debtor(self, debtor_id: int) -> list[Contract]:
        # Verify debtor belongs to current tenant
        if self.company_id is not None:
            debtor = await self.db.get(Debtor, debtor_id)
            if not debtor or debtor.company_id != self.company_id:
                return []
        contracts = await self.repo.get_by_debtor(debtor_id)
        # Filter out soft-deleted and other tenants (defensive)
        return [
            c for c in contracts
            if getattr(c, "deleted_at", None) is None
            and (self.company_id is None or c.company_id == self.company_id)
        ]
