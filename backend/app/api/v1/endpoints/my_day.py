"""
My Day endpoint — рабочая область менеджера на сегодня.
GET /api/v1/tasks/my-day — возвращает 3 блока: hot, today, overdue.
POST /api/v1/tasks/my-day/complete/{task_id} — закрыть задачу.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.deps import get_current_active_user, get_current_company
from app.models.user import User
from app.models.company import Company
from app.services.my_day import MyDayService

router = APIRouter(prefix="/tasks", tags=["my-day"])


@router.get("/my-day")
async def get_my_day(
    manager_id: int | None = Query(None, description="Только для ADMIN/HEAD: посмотреть план чужого менеджера"),
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(get_current_active_user),
):
    """
    Возвращает план менеджера на сегодня:
      - hot: задачи/обещания по HOT-должникам (всегда сверху)
      - today: на сегодня (обещания + задачи)
      - overdue: просроченные

    Менеджер видит только свой план. ADMIN/HEAD могут указать manager_id.
    """
    role = (user.role or "").upper()
    target_id = user.id
    if manager_id is not None:
        if role not in ("ADMIN", "HEAD"):
            raise HTTPException(403, "Только руководитель может смотреть чужой план")
        target_id = manager_id

    svc = MyDayService(db, company_id=company.id)
    return await svc.get_my_day(target_id)


@router.post("/my-day/complete/{task_id}")
async def complete_my_day_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(get_current_active_user),
):
    """Закрыть задачу из плана. Audit logged."""
    svc = MyDayService(db, company_id=company.id)
    res = await svc.complete_task(task_id, user.id)
    if not res.get("ok"):
        err = res.get("error", "unknown")
        if err == "not_found":
            raise HTTPException(404, "Задача не найдена")
        if err == "not_yours":
            raise HTTPException(403, "Это не ваша задача")
        if err == "wrong_company":
            raise HTTPException(403, "Задача из другой компании")
        raise HTTPException(400, err)
    return res
