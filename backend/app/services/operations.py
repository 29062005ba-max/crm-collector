from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.repositories.operations import PromiseRepository, PaymentRepository, CallLogRepository, CsiCaseRepository
from app.schemas.operations import (
    PromiseCreate, PromiseUpdate,
    PaymentCreate,
    CallLogCreate,
    CsiCaseCreate, CsiCaseUpdate,
)
from app.models.operations import Promise, Payment, CallLog, CsiCase
from app.models.contract import Contract


def _check_tenant(obj, company_id: Optional[int], detail: str = "Not found"):
    """Raise 404 if obj belongs to another tenant or is soft-deleted"""
    if obj is None:
        raise HTTPException(status_code=404, detail=detail)
    if company_id is not None and getattr(obj, "company_id", None) != company_id:
        raise HTTPException(status_code=404, detail=detail)
    if getattr(obj, "deleted_at", None) is not None:
        raise HTTPException(status_code=404, detail=detail)


async def _verify_contract_tenant(db: AsyncSession, contract_id: int, company_id: Optional[int]) -> Contract:
    """Get contract and verify tenant. Used when creating dependent records."""
    contract = await db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if company_id is not None and contract.company_id != company_id:
        raise HTTPException(status_code=404, detail="Contract not found")
    if getattr(contract, "deleted_at", None) is not None:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


class PromiseService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.repo = PromiseRepository(db)
        self.company_id = company_id

    async def create(self, data: PromiseCreate, created_by_id: int) -> Promise:
        # Verify contract belongs to current tenant
        await _verify_contract_tenant(self.db, data.contract_id, self.company_id)

        kwargs = data.model_dump()
        if self.company_id is not None:
            kwargs["company_id"] = self.company_id
        promise = Promise(**kwargs, created_by_id=created_by_id)
        return await self.repo.create(promise)

    async def get(self, promise_id: int) -> Promise:
        p = await self.repo.get(promise_id)
        _check_tenant(p, self.company_id, "Promise not found")
        return p

    async def update(self, promise_id: int, data: PromiseUpdate) -> Promise:
        p = await self.get(promise_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(p, field, value)
        return await self.repo.update(p)

    async def soft_delete(self, promise_id: int) -> None:
        p = await self.get(promise_id)
        p.deleted_at = datetime.utcnow()
        await self.db.flush()

    async def list_by_contract(self, contract_id: int) -> list[Promise]:
        # Verify contract tenant
        await _verify_contract_tenant(self.db, contract_id, self.company_id)
        items = await self.repo.get_by_contract(contract_id)
        return [
            p for p in items
            if getattr(p, "deleted_at", None) is None
            and (self.company_id is None or p.company_id == self.company_id)
        ]

    async def process_overdue(self) -> int:
        """Process overdue promises within current tenant only"""
        return await self.repo.mark_overdue(company_id=self.company_id)


class PaymentService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.repo = PaymentRepository(db)
        self.company_id = company_id

    async def create(self, data: PaymentCreate, registered_by_id: int) -> Payment:
        await _verify_contract_tenant(self.db, data.contract_id, self.company_id)

        kwargs = data.model_dump()
        if self.company_id is not None:
            kwargs["company_id"] = self.company_id
        payment = Payment(**kwargs, registered_by_id=registered_by_id)
        return await self.repo.create(payment)

    async def get(self, payment_id: int) -> Payment:
        p = await self.repo.get(payment_id)
        _check_tenant(p, self.company_id, "Payment not found")
        return p

    async def list_by_contract(self, contract_id: int) -> list[Payment]:
        await _verify_contract_tenant(self.db, contract_id, self.company_id)
        items = await self.repo.get_by_contract(contract_id)
        return [
            p for p in items
            if getattr(p, "deleted_at", None) is None
            and (self.company_id is None or p.company_id == self.company_id)
        ]


class CallLogService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.repo = CallLogRepository(db)
        self.company_id = company_id

    async def create(self, data: CallLogCreate, manager_id: int) -> CallLog:
        await _verify_contract_tenant(self.db, data.contract_id, self.company_id)

        kwargs = data.model_dump()
        if self.company_id is not None:
            kwargs["company_id"] = self.company_id
        call_log = CallLog(**kwargs, manager_id=manager_id)
        return await self.repo.create(call_log)

    async def list_by_contract(self, contract_id: int) -> list[CallLog]:
        await _verify_contract_tenant(self.db, contract_id, self.company_id)
        items = await self.repo.get_by_contract(contract_id)
        return [
            c for c in items
            if self.company_id is None or c.company_id == self.company_id
        ]


class CsiCaseService:
    def __init__(self, db: AsyncSession, company_id: Optional[int] = None):
        self.db = db
        self.repo = CsiCaseRepository(db)
        self.company_id = company_id

    async def create(self, data: CsiCaseCreate) -> CsiCase:
        kwargs = data.model_dump()
        if self.company_id is not None:
            kwargs["company_id"] = self.company_id
        case = CsiCase(**kwargs)
        return await self.repo.create(case)

    async def get(self, case_id: int) -> CsiCase:
        c = await self.repo.get(case_id)
        _check_tenant(c, self.company_id, "CSI case not found")
        return c

    async def update(self, case_id: int, data: CsiCaseUpdate) -> CsiCase:
        c = await self.get(case_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(c, field, value)
        return await self.repo.update(c)

    async def list_by_debtor(self, debtor_id: int) -> list[CsiCase]:
        items = await self.repo.get_by_debtor(debtor_id)
        return [c for c in items if self.company_id is None or c.company_id == self.company_id]
