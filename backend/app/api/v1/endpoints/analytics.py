"""
Analytics endpoints — контрольная панель руководителя.
Все endpoints требуют роль ADMIN или HEAD.
Tenant isolation через company_id.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.deps import get_current_company, require_roles
from app.models.user import User
from app.models.company import Company
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/manager-performance")
async def manager_performance(
    period: str = Query("day", regex="^(day|week|month)$"),
    source: str = Query("live", regex="^(live|snapshot)$"),
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(require_roles("ADMIN", "HEAD")),
):
    """
    KPI всех менеджеров компании за period (day/week/month).
    source=live — точные актуальные данные (медленнее).
    source=snapshot — из manager_kpi_snapshots (быстрее, обновляется раз в час).
    Возвращает leaderboard, отсортированный по сбору.
    """
    svc = AnalyticsService(db, company_id=company.id)
    if source == "snapshot":
        data = await svc.manager_performance_snapshot(period)
        if not data:
            # Fallback: snapshots ещё не считались
            data = await svc.manager_performance_live(period)
    else:
        data = await svc.manager_performance_live(period)
    return data


@router.get("/broken-promises")
async def broken_promises(
    limit: int = Query(100, ge=1, le=500),
    manager_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(require_roles("ADMIN", "HEAD")),
):
    """Список сорванных обещаний с указанием ответственного менеджера (Leakage)."""
    svc = AnalyticsService(db, company_id=company.id)
    return await svc.broken_promises(limit=limit, manager_id=manager_id)


@router.get("/control-panel")
async def control_panel_summary(
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(require_roles("ADMIN", "HEAD")),
):
    """Сводка для верхушки контрольной панели — ключевые цифры компании."""
    svc = AnalyticsService(db, company_id=company.id)
    return await svc.control_panel_summary()


@router.get("/daily-collection")
async def daily_collection(
    days: int = Query(30, ge=7, le=180),
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(require_roles("ADMIN", "HEAD")),
):
    """Динамика сбора по дням (для графика)."""
    svc = AnalyticsService(db, company_id=company.id)
    return await svc.daily_collection(days=days)


@router.post("/snapshot/recalculate")
async def trigger_snapshot_recalc(
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(require_roles("ADMIN", "HEAD")),
):
    """Запустить пересчёт snapshots вручную (синхронно для текущей компании)."""
    from app.services.kpi_snapshot import KpiSnapshotService
    svc = KpiSnapshotService(db, company_id=company.id)
    return await svc.recalculate()
