"""Tasks extra endpoints (Pack 2):
- GET    /tasks/stats             — статистика для текущего пользователя
- GET    /tasks/created           — задачи которые я создал
- PATCH  /tasks/{task_id}/status  — быстрая смена статуса
- GET    /tasks                   — список с пагинацией и фильтрами

Backward-compatible: старые статусы (open, etc.) работают как прежде.
Новые статусы (new, on_review) можно использовать в новых задачах.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, and_, or_, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.deps import get_db, get_current_active_user, get_current_company
from app.models import User, Debtor, Task, Company, Contract


# ==================== Status mapping (backward compat) ====================
# Старые → новые: при чтении статус нормализуется
LEGACY_STATUS_MAP = {
    "open": "new",      # старый open → отображается как new
    "todo": "new",
    "pending": "new",
}

# Допустимые статусы (новые + старые для совместимости)
VALID_STATUSES = {"new", "in_progress", "on_review", "done", "cancelled", "open"}
VALID_PRIORITIES = {"low", "medium", "high", "urgent", "normal"}  # normal = legacy
VALID_TYPES = {"call", "meeting", "document", "review", "payment_control", "other", "followup"}


def normalize_status(s: str) -> str:
    """Преобразует legacy статусы в новые для отображения."""
    if not s:
        return "new"
    return LEGACY_STATUS_MAP.get(s.lower(), s.lower())


# ==================== Schemas ====================
class TaskStatusUpdate(BaseModel):
    status: str = Field(..., description="new | in_progress | on_review | done | cancelled")


class TaskStatsResponse(BaseModel):
    total: int
    by_status: dict
    by_priority: dict
    overdue: int
    due_today: int
    completed_today: int


# ==================== Router ====================
router = APIRouter(prefix="/tasks", tags=["tasks-extra"])


# ---------- GET /tasks/stats — статистика по текущему пользователю ----------
@router.get("/stats", response_model=TaskStatsResponse)
async def task_stats(
    scope: str = Query("my", description="my | all (HEAD/ADMIN only)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    """Статистика задач."""
    is_admin = current_user.role.upper() in ("ADMIN", "HEAD")

    base = select(Task).where(
        Task.company_id == company.id,
        Task.deleted_at.is_(None) if hasattr(Task, "deleted_at") else True,
    )
    if scope == "my" or not is_admin:
        base = base.where(
            or_(Task.assignee_id == current_user.id, Task.created_by_id == current_user.id)
        )

    rows = (await db.execute(base)).scalars().all()
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    overdue = 0
    due_today = 0
    completed_today = 0

    for t in rows:
        norm_status = normalize_status(t.status)
        by_status[norm_status] = by_status.get(norm_status, 0) + 1
        by_priority[t.priority or "medium"] = by_priority.get(t.priority or "medium", 0) + 1

        # Пропускаем done/cancelled при подсчёте просрочки
        if norm_status in ("done", "cancelled"):
            if t.completed_at and today_start <= t.completed_at < today_end:
                completed_today += 1
            continue

        if t.due_date:
            if t.due_date < now:
                overdue += 1
            elif today_start <= t.due_date < today_end:
                due_today += 1

    return TaskStatsResponse(
        total=len(rows),
        by_status=by_status,
        by_priority=by_priority,
        overdue=overdue,
        due_today=due_today,
        completed_today=completed_today,
    )


# ---------- GET /tasks/created — задачи которые я создал ----------
@router.get("/created")
async def tasks_created_by_me(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    """Задачи, которые я создал (для head'ов чтобы отслеживать делегирование)."""
    q = select(Task).where(
        Task.company_id == company.id,
        Task.created_by_id == current_user.id,
    )
    if hasattr(Task, "deleted_at"):
        q = q.where(Task.deleted_at.is_(None))
    if status:
        # Поддерживаем legacy: если передали "new" — ищем и "open"
        if status == "new":
            q = q.where(or_(Task.status == "new", Task.status == "open"))
        else:
            q = q.where(Task.status == status)

    total = (await db.execute(select(sa_func.count()).select_from(q.subquery()))).scalar() or 0
    q = q.order_by(Task.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(q)).scalars().all()

    # Подгрузка имён должника + assignee
    debtor_ids = [t.debtor_id for t in rows if t.debtor_id]
    assignee_ids = [t.assignee_id for t in rows if t.assignee_id]

    debtors_map = {}
    if debtor_ids:
        d_rows = (await db.execute(select(Debtor.id, Debtor.full_name).where(Debtor.id.in_(debtor_ids)))).all()
        debtors_map = {r.id: r.full_name for r in d_rows}

    assignees_map = {}
    if assignee_ids:
        a_rows = (await db.execute(select(User.id, User.full_name).where(User.id.in_(assignee_ids)))).all()
        assignees_map = {r.id: r.full_name for r in a_rows}

    items = []
    for t in rows:
        items.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "type": t.type,
            "status": normalize_status(t.status),
            "raw_status": t.status,
            "priority": t.priority,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "assignee_id": t.assignee_id,
            "assignee_name": assignees_map.get(t.assignee_id),
            "debtor_id": t.debtor_id,
            "debtor_name": debtors_map.get(t.debtor_id),
            "contract_id": t.contract_id,
        })
    return {"items": items, "total": total, "page": page, "per_page": per_page}


# ---------- PATCH /tasks/{task_id}/status — быстрая смена статуса ----------
@router.patch("/{task_id}/status")
async def update_task_status(
    task_id: int,
    data: TaskStatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    """Быстрая смена статуса задачи. Manager может менять только свои."""
    new_status = data.status.lower()
    if new_status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of {sorted(VALID_STATUSES)}")

    task = await db.get(Task, task_id)
    if not task or task.company_id != company.id:
        raise HTTPException(404, "Task not found")
    if hasattr(task, "deleted_at") and task.deleted_at is not None:
        raise HTTPException(404, "Task not found")

    # Manager может менять только свои задачи (assigned_to или created_by)
    is_admin = current_user.role.upper() in ("ADMIN", "HEAD")
    if not is_admin and task.assignee_id != current_user.id and task.created_by_id != current_user.id:
        raise HTTPException(403, "You can only change status of your own tasks")

    old_status = task.status
    task.status = new_status

    # При завершении — фиксируем completed_at
    if new_status in ("done", "cancelled") and not task.completed_at:
        task.completed_at = datetime.utcnow()
    elif new_status not in ("done", "cancelled"):
        task.completed_at = None  # снято с завершённого

    # Audit log (если сервис доступен)
    try:
        from app.services.saas import ActivityLogService
        log_svc = ActivityLogService(db, company_id=company.id)
        await log_svc.log(
            actor_id=current_user.id,
            action="status_changed",
            entity_type="task",
            entity_id=task_id,
            description=f"Статус задачи: {old_status} → {new_status}",
            changes={"status": [old_status, new_status]},
            ip_address=request.client.host if request.client else None,
        )
    except Exception:
        pass  # не валим запрос если audit не работает

    await db.commit()
    return {"ok": True, "id": task.id, "status": new_status, "completed_at": task.completed_at}


# ---------- GET /tasks (список с фильтрами и пагинацией) ----------
@router.get("")
async def list_tasks(
    scope: str = Query("my", description="my | all | created"),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    assignee_id: Optional[int] = Query(None),
    debtor_id: Optional[int] = Query(None),
    due_from: Optional[str] = Query(None),
    due_to: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("due_date", description="due_date | priority | created_at | status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    """Список задач с фильтрами и пагинацией."""
    is_admin = current_user.role.upper() in ("ADMIN", "HEAD")

    q = select(Task).where(Task.company_id == company.id)
    if hasattr(Task, "deleted_at"):
        q = q.where(Task.deleted_at.is_(None))

    # Scope
    if scope == "my":
        q = q.where(Task.assignee_id == current_user.id)
    elif scope == "created":
        q = q.where(Task.created_by_id == current_user.id)
    elif scope == "all":
        if not is_admin:
            q = q.where(Task.assignee_id == current_user.id)

    # Filters
    if status:
        if status == "new":
            q = q.where(or_(Task.status == "new", Task.status == "open"))
        else:
            q = q.where(Task.status == status)
    if priority:
        q = q.where(Task.priority == priority)
    if task_type:
        q = q.where(Task.type == task_type)
    if assignee_id and is_admin:
        q = q.where(Task.assignee_id == assignee_id)
    if debtor_id:
        q = q.where(Task.debtor_id == debtor_id)
    if due_from:
        try:
            q = q.where(Task.due_date >= datetime.fromisoformat(due_from))
        except ValueError:
            pass
    if due_to:
        try:
            q = q.where(Task.due_date <= datetime.fromisoformat(due_to))
        except ValueError:
            pass
    if search:
        q = q.where(Task.title.ilike(f"%{search}%"))

    # Total
    total = (await db.execute(select(sa_func.count()).select_from(q.subquery()))).scalar() or 0

    # Sort
    sort_map = {
        "due_date": Task.due_date.asc().nullslast(),
        "priority": Task.priority.desc(),
        "created_at": Task.created_at.desc(),
        "status": Task.status.asc(),
    }
    q = q.order_by(sort_map.get(sort_by, Task.created_at.desc()))
    q = q.offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(q)).scalars().all()

    # Enrichment
    debtor_ids = list({t.debtor_id for t in rows if t.debtor_id})
    assignee_ids = list({t.assignee_id for t in rows if t.assignee_id})
    debtors_map = {}
    if debtor_ids:
        d_rows = (await db.execute(select(Debtor.id, Debtor.full_name).where(Debtor.id.in_(debtor_ids)))).all()
        debtors_map = {r.id: r.full_name for r in d_rows}
    assignees_map = {}
    if assignee_ids:
        a_rows = (await db.execute(select(User.id, User.full_name).where(User.id.in_(assignee_ids)))).all()
        assignees_map = {r.id: r.full_name for r in a_rows}

    items = []
    for t in rows:
        items.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "type": t.type,
            "status": normalize_status(t.status),
            "raw_status": t.status,
            "priority": t.priority,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "assignee_id": t.assignee_id,
            "assignee_name": assignees_map.get(t.assignee_id),
            "created_by_id": t.created_by_id,
            "debtor_id": t.debtor_id,
            "debtor_name": debtors_map.get(t.debtor_id),
            "contract_id": t.contract_id,
        })
    return {"items": items, "total": total, "page": page, "per_page": per_page}
