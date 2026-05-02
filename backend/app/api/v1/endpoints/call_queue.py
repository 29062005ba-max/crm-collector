"""Call Queue API — auto-dial module"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.deps import get_current_active_user, get_current_company, require_roles
from app.models.user import User
from app.models.company import Company
from app.schemas.call_queue import (
    CallQueueCreate, CallQueueUpdate,
    CallQueuePopulate,
    TakeNextRequest, CallResultSubmit, CallResultResponse,
)
from app.services.call_queue import CallQueueService


router = APIRouter(prefix="/call-queue", tags=["call-queue"])


# ============ Queues CRUD ============
@router.get("/queues")
async def list_queues(
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(get_current_active_user),
):
    svc = CallQueueService(db, company_id=company.id)
    return await svc.list_queues()


@router.post("/queues", status_code=201)
async def create_queue(
    data: CallQueueCreate,
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(require_roles("ADMIN", "HEAD")),
):
    svc = CallQueueService(db, company_id=company.id)
    queue = await svc.create_queue(data, created_by_id=user.id)
    return {c.name: getattr(queue, c.name) for c in queue.__table__.columns}


@router.patch("/queues/{queue_id}")
async def update_queue(
    queue_id: int,
    data: CallQueueUpdate,
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(require_roles("ADMIN", "HEAD")),
):
    svc = CallQueueService(db, company_id=company.id)
    queue = await svc.update_queue(queue_id, data)
    if not queue:
        raise HTTPException(404, "Очередь не найдена")
    return {c.name: getattr(queue, c.name) for c in queue.__table__.columns}


@router.delete("/queues/{queue_id}")
async def delete_queue(
    queue_id: int,
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(require_roles("ADMIN", "HEAD")),
):
    svc = CallQueueService(db, company_id=company.id)
    ok = await svc.delete_queue(queue_id)
    if not ok:
        raise HTTPException(404, "Очередь не найдена")
    return {"ok": True}


@router.post("/queues/{queue_id}/populate")
async def populate_queue(
    queue_id: int,
    params: CallQueuePopulate,
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(require_roles("ADMIN", "HEAD")),
):
    svc = CallQueueService(db, company_id=company.id)
    added = await svc.populate(queue_id, params)
    return {"added": added}


@router.get("/queues/{queue_id}/items")
async def list_queue_items(
    queue_id: int,
    status: str | None = Query(None),
    manager_id: int | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(get_current_active_user),
):
    svc = CallQueueService(db, company_id=company.id)
    return await svc.list_items(queue_id, status=status, manager_id=manager_id, limit=limit)


# ============ Manager workflow ============
@router.post("/take-next")
async def take_next(
    body: TakeNextRequest,
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(get_current_active_user),
):
    svc = CallQueueService(db, company_id=company.id)
    item = await svc.take_next(manager_id=user.id, queue_id=body.queue_id)
    if not item:
        return {"item": None, "message": "В очереди нет доступных должников"}
    return {"item": item}


@router.post("/submit-result", response_model=CallResultResponse)
async def submit_result(
    data: CallResultSubmit,
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(get_current_active_user),
):
    svc = CallQueueService(db, company_id=company.id)
    return await svc.submit_result(user, data)


@router.post("/release/{item_id}")
async def release_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(get_current_active_user),
):
    """Менеджер пропускает текущего должника (release lock)."""
    svc = CallQueueService(db, company_id=company.id)
    ok = await svc.release(item_id, user.id)
    return {"released": ok}


@router.get("/my-progress")
async def my_progress(
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(get_current_active_user),
):
    svc = CallQueueService(db, company_id=company.id)
    return await svc.manager_progress(user.id)


@router.get("/all-progress")
async def all_progress(
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(require_roles("ADMIN", "HEAD")),
):
    svc = CallQueueService(db, company_id=company.id)
    return await svc.all_managers_progress()


@router.get("/dashboard-stats")
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(get_current_active_user),
):
    """Сводная статистика звонков за сегодня (для блока на дашборде)."""
    svc = CallQueueService(db, company_id=company.id)
    return await svc.dashboard_call_stats()
