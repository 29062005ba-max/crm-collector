from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta
from app.db.session import get_db
from app.core.deps import get_current_active_user, require_roles
from app.services.assignment_service import AssignmentService
from app.services.kpi_service import KpiService
from app.models.user import User

router = APIRouter(prefix="/management", tags=["management"])


@router.post("/auto-assign")
async def auto_assign(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "head")),
):
    """Автораспределить все договора без менеджера."""
    svc = AssignmentService(db)
    return await svc.auto_assign_all()


@router.get("/manager-loads")
async def manager_loads(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Нагрузка по менеджерам."""
    svc = AssignmentService(db)
    return await svc.get_manager_loads()


@router.post("/reassign")
async def reassign(
    from_manager_id: int,
    to_manager_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "head")),
):
    """Переназначить все договора от одного менеджера другому."""
    svc = AssignmentService(db)
    return await svc.reassign_manager(from_manager_id, to_manager_id)


@router.get("/kpi")
async def get_kpi(
    date_from: date = Query(default=None),
    date_to: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """KPI всех менеджеров за период."""
    if not date_from:
        date_from = date.today().replace(day=1)
    if not date_to:
        date_to = date.today()
    svc = KpiService(db)
    return await svc.get_all_kpi(date_from, date_to)


@router.patch("/contracts/{contract_id}/status")
async def update_contract_status(
    contract_id: int,
    status: str,
    comment: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Сменить статус договора (досудебный / судебный / закрыт)."""
    from sqlalchemy import select
    from app.models.contract import Contract
    from app.models.operations import StatusHistory

    allowed = ["active", "litigation", "closed", "written_off"]
    if status not in allowed:
        from fastapi import HTTPException
        raise HTTPException(400, f"Статус должен быть одним из: {allowed}")

    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        from fastapi import HTTPException
        raise HTTPException(404, "Договор не найден")

    old_status = contract.status
    contract.status = status

    history = StatusHistory(
        contract_id=contract_id,
        old_status=old_status,
        new_status=status,
        changed_by_id=current_user.id,
        comment=comment or None,
    )
    db.add(history)
    await db.flush()

    labels = {"active": "Досудебный", "litigation": "Судебный", "closed": "Закрыт", "written_off": "Списан"}
    return {
        "contract_id": contract_id,
        "old_status": old_status,
        "new_status": status,
        "label": labels.get(status, status),
    }


@router.delete("/assignments/clear")
async def clear_all_assignments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "head")),
):
    """Снять всех менеджеров со всех договоров."""
    from sqlalchemy import update
    from app.models.operations import Assignment
    result = await db.execute(
        update(Assignment).where(Assignment.is_active == True).values(is_active=False)
    )
    await db.commit()
    return {"cleared": result.rowcount}
