"""Scoring API — debtor priority endpoint"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.deps import get_current_active_user, get_current_company, require_roles
from app.models.user import User
from app.models.company import Company
from app.services.scoring import ScoringService

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.get("/priority")
async def list_priority(
    tier: str | None = Query(None, regex="^(hot|medium|low)$"),
    manager_id: int | None = Query(None),
    limit: int = Query(200, ge=1, le=2000),
    only_mine: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(get_current_active_user),
):
    """Должники, отсортированные по приоритету взыскания."""
    svc = ScoringService(db, company_id=company.id)
    mid = user.id if only_mine else manager_id
    return await svc.list_priority(tier=tier, manager_id=mid, limit=limit)


@router.get("/summary")
async def tier_summary(
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(get_current_active_user),
):
    svc = ScoringService(db, company_id=company.id)
    return await svc.tier_summary()


@router.post("/recalculate")
async def recalculate(
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(require_roles("ADMIN", "HEAD")),
):
    """Запустить пересчёт скоринга вручную (для всей компании)."""
    svc = ScoringService(db, company_id=company.id)
    return await svc.recalculate_all()


@router.post("/recalculate/{debtor_id}")
async def recalculate_one(
    debtor_id: int,
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(get_current_active_user),
):
    svc = ScoringService(db, company_id=company.id)
    return await svc.calculate(debtor_id)
