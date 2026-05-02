from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.operations import ContractCreate, ContractUpdate, ContractResponse
from app.services.contract import ContractService
from app.core.deps import get_current_active_user, get_current_company
from app.models.user import User
from app.models.company import Company

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.post("/", response_model=ContractResponse, status_code=201)
async def create_contract(
    data: ContractCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = ContractService(db, company_id=company.id)
    return await service.create(data)


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = ContractService(db, company_id=company.id)
    return await service.get(contract_id)


@router.patch("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: int,
    data: ContractUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = ContractService(db, company_id=company.id)
    return await service.update(contract_id, data, current_user.id)


@router.delete("/{contract_id}", status_code=204)
async def delete_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    """Soft delete contract"""
    service = ContractService(db, company_id=company.id)
    await service.soft_delete(contract_id)


@router.get("/by-debtor/{debtor_id}", response_model=list[ContractResponse])
async def get_contracts_by_debtor(
    debtor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = ContractService(db, company_id=company.id)
    return await service.get_by_debtor(debtor_id)
