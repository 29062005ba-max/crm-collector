"""Companies (tenants) management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.core.deps import get_db, get_current_active_user, require_roles
from app.models import User, Debtor, Company, TARIFF_LIMITS

router = APIRouter(prefix="/companies", tags=["companies"])


class CompanyCreate(BaseModel):
    name: str
    slug: str
    tariff: str = "basic"
    contact_email: str | None = None
    contact_phone: str | None = None
    address: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    tariff: str | None = None
    is_active: bool | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    address: str | None = None


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    tariff: str
    max_users: int
    max_debtors: int
    is_active: bool
    contact_email: str | None
    contact_phone: str | None
    address: str | None
    created_at: datetime


class CompanyStats(BaseModel):
    company: CompanyResponse
    users_count: int
    debtors_count: int
    users_limit: int
    debtors_limit: int
    users_usage_pct: float
    debtors_usage_pct: float


@router.get("", response_model=list[CompanyResponse])
async def list_companies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """List all companies (admin only)"""
    result = await db.execute(select(Company).order_by(Company.name))
    return result.scalars().all()


@router.post("", response_model=CompanyResponse, status_code=201)
async def create_company(
    data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """Create new company (admin only)"""
    # Check slug uniqueness
    existing = await db.execute(select(Company).where(Company.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Company with slug '{data.slug}' already exists")

    if data.tariff not in TARIFF_LIMITS:
        raise HTTPException(400, f"Invalid tariff. Must be one of: {list(TARIFF_LIMITS.keys())}")

    limits = TARIFF_LIMITS[data.tariff]
    company = Company(
        name=data.name,
        slug=data.slug,
        tariff=data.tariff,
        max_users=limits["max_users"],
        max_debtors=limits["max_debtors"],
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        address=data.address,
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company


@router.get("/me", response_model=CompanyStats)
async def my_company(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get current user's company with usage stats"""
    company = await db.get(Company, current_user.company_id)
    if not company:
        raise HTTPException(404, "Company not found")

    users_count = (await db.execute(
        select(func.count(User.id)).where(User.company_id == company.id, User.is_active == True)
    )).scalar() or 0

    debtors_count = (await db.execute(
        select(func.count(Debtor.id)).where(
            Debtor.company_id == company.id,
            Debtor.is_active == True,
            Debtor.deleted_at.is_(None),
        )
    )).scalar() or 0

    return {
        "company": company,
        "users_count": users_count,
        "debtors_count": debtors_count,
        "users_limit": company.max_users,
        "debtors_limit": company.max_debtors,
        "users_usage_pct": round((users_count / company.max_users * 100) if company.max_users else 0, 1),
        "debtors_usage_pct": round((debtors_count / company.max_debtors * 100) if company.max_debtors else 0, 1),
    }


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    data: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    """Update company (admin only)"""
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(404, "Company not found")

    update_data = data.model_dump(exclude_unset=True)

    # If tariff changed, update limits
    if "tariff" in update_data and update_data["tariff"] != company.tariff:
        if update_data["tariff"] not in TARIFF_LIMITS:
            raise HTTPException(400, "Invalid tariff")
        limits = TARIFF_LIMITS[update_data["tariff"]]
        company.max_users = limits["max_users"]
        company.max_debtors = limits["max_debtors"]

    for field, value in update_data.items():
        setattr(company, field, value)

    await db.commit()
    await db.refresh(company)
    return company


@router.get("/tariffs/list")
async def list_tariffs():
    """List available tariffs"""
    return TARIFF_LIMITS
