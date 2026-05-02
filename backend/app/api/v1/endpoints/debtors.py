from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.debtor import DebtorCreate, DebtorUpdate, DebtorResponse, DebtorFilter
from app.services.debtor import DebtorService
from app.core.deps import get_current_active_user, get_current_company
from app.models.user import User
from app.models.company import Company

router = APIRouter(prefix="/debtors", tags=["debtors"])


@router.get("/")
async def list_debtors(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    contract_status: Optional[str] = Query(None),
    manager_id: Optional[int] = Query(None),
    debt_min: Optional[float] = Query(None),
    debt_max: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    # Managers only see their own debtors
    if current_user.role.upper() == "MANAGER":
        manager_id = current_user.id

    service = DebtorService(db, company_id=company.id)
    filters = DebtorFilter(
        search=search, is_active=is_active,
        contract_status=contract_status,
        manager_id=manager_id,
        debt_min=debt_min, debt_max=debt_max,
        page=page, page_size=page_size,
    )
    return await service.list(filters)


@router.post("/", response_model=DebtorResponse, status_code=201)
async def create_debtor(
    data: DebtorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    # Check tariff limit
    from sqlalchemy import select, func
    from app.models import Debtor
    count = (await db.execute(
        select(func.count(Debtor.id)).where(
            Debtor.company_id == company.id,
            Debtor.deleted_at.is_(None),
        )
    )).scalar() or 0
    if count >= company.max_debtors:
        from fastapi import HTTPException
        raise HTTPException(
            403,
            f"Достигнут лимит должников по тарифу '{company.tariff}': {company.max_debtors}. Обновите тариф."
        )

    service = DebtorService(db, company_id=company.id)
    return await service.create(data)


@router.get("/{debtor_id}", response_model=DebtorResponse)
async def get_debtor(
    debtor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = DebtorService(db, company_id=company.id)
    return await service.get(debtor_id)


@router.patch("/{debtor_id}", response_model=DebtorResponse)
async def update_debtor(
    debtor_id: int,
    data: DebtorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = DebtorService(db, company_id=company.id)
    return await service.update(debtor_id, data)


@router.delete("/{debtor_id}", status_code=204)
async def delete_debtor(
    debtor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    """Soft delete - record stays in DB for audit"""
    service = DebtorService(db, company_id=company.id)
    await service.soft_delete(debtor_id)
