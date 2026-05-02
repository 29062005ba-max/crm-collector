"""SaaS API endpoints with full tenant isolation"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_active_user, get_current_company
from app.models import User, Debtor, Task, Notification, Company, Contract
from app.schemas.saas import (
    TaskCreate, TaskUpdate, TaskResponse,
    NotificationResponse,
    PaymentScheduleCreate, PaymentScheduleResponse,
    AssignManagerRequest, KanbanStatusUpdate,
)
from app.services.saas import (
    TaskService, NotificationService, ActivityLogService,
    PaymentScheduleService, WorkflowService, DashboardKPIService,
)


# ==================== Tasks ====================
tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])


@tasks_router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    data: TaskCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    """Create task with idempotency support."""
    from app.core.idempotency import check_idempotency, save_idempotency_response

    body_dict = data.model_dump(mode="json")
    existing, idem_key = await check_idempotency(
        db, request, body=body_dict,
        user_id=current_user.id, company_id=company.id,
    )
    if existing:
        from fastapi import Response
        import json
        return Response(
            content=json.dumps(existing.response_body, default=str),
            status_code=existing.response_status,
            media_type="application/json",
            headers={"X-Idempotent-Replay": "true"},
        )

    # Tenant validation
    if data.debtor_id:
        debtor = await db.get(Debtor, data.debtor_id)
        if not debtor or debtor.company_id != company.id:
            raise HTTPException(404, "Debtor not found")
    if data.contract_id:
        contract = await db.get(Contract, data.contract_id)
        if not contract or contract.company_id != company.id:
            raise HTTPException(404, "Contract not found")
    if data.assignee_id:
        assignee = await db.get(User, data.assignee_id)
        if not assignee or assignee.company_id != company.id:
            raise HTTPException(404, "Assignee not found")

    svc = TaskService(db, company_id=company.id)
    task = await svc.create(data, created_by_id=current_user.id)

    if idem_key:
        await save_idempotency_response(
            db, idem_key, request, body_dict,
            {"id": task.id, "title": task.title, "status": task.status},
            status=201, user_id=current_user.id, company_id=company.id,
        )
        await db.commit()
    return task


@tasks_router.get("/my")
async def my_tasks(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    svc = TaskService(db, company_id=company.id)
    return await svc.list_for_user(current_user.id, status=status, only_assigned=True)


@tasks_router.get("/all")
async def all_tasks(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    if current_user.role.upper() not in ("ADMIN", "HEAD"):
        raise HTTPException(403, "Forbidden")
    svc = TaskService(db, company_id=company.id)
    return await svc.list_for_user(current_user.id, status=status, only_assigned=False)


@tasks_router.get("/by-debtor/{debtor_id}")
async def tasks_by_debtor(
    debtor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    # Verify debtor tenant
    debtor = await db.get(Debtor, debtor_id)
    if not debtor or debtor.company_id != company.id:
        raise HTTPException(404, "Debtor not found")
    q = select(Task).where(
        Task.debtor_id == debtor_id,
        Task.company_id == company.id,
    ).order_by(Task.created_at.desc())
    return (await db.execute(q)).scalars().all()


@tasks_router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    # Verify task belongs to tenant
    task = await db.get(Task, task_id)
    if not task or task.company_id != company.id:
        raise HTTPException(404, "Task not found")

    svc = TaskService(db, company_id=company.id)
    updated = await svc.update(task_id, data)
    if not updated:
        raise HTTPException(404, "Task not found")
    return updated


@tasks_router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    task = await db.get(Task, task_id)
    if not task or task.company_id != company.id:
        raise HTTPException(404, "Task not found")
    svc = TaskService(db, company_id=company.id)
    ok = await svc.delete(task_id)
    if not ok:
        raise HTTPException(404, "Task not found")
    return {"deleted": True}


# ==================== Notifications ====================
notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


@notifications_router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    # Notifications are always personal (user_id), but also filter by company for safety
    svc = NotificationService(db, company_id=company.id)
    return await svc.list_for_user(current_user.id, unread_only=unread_only, limit=limit)


@notifications_router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    svc = NotificationService(db, company_id=company.id)
    return {"count": await svc.unread_count(current_user.id)}


@notifications_router.post("/{notif_id}/read")
async def mark_read(
    notif_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    svc = NotificationService(db, company_id=company.id)
    ok = await svc.mark_read(notif_id, current_user.id)
    if not ok:
        raise HTTPException(404, "Not found")
    return {"ok": True}


@notifications_router.post("/mark-all-read")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    svc = NotificationService(db, company_id=company.id)
    return {"marked": await svc.mark_all_read(current_user.id)}


# ==================== Activity Logs ====================
activity_router = APIRouter(prefix="/activity-logs", tags=["activity"])


@activity_router.get("/by-debtor/{debtor_id}")
async def activity_by_debtor(
    debtor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    debtor = await db.get(Debtor, debtor_id)
    if not debtor or debtor.company_id != company.id:
        raise HTTPException(404, "Debtor not found")
    svc = ActivityLogService(db, company_id=company.id)
    return await svc.list_for_debtor(debtor_id)


@activity_router.get("/recent")
async def recent_activity(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    svc = ActivityLogService(db, company_id=company.id)
    return await svc.list_recent(limit=limit)


# ==================== Payment Schedules ====================
schedules_router = APIRouter(prefix="/schedules", tags=["schedules"])


@schedules_router.post("", response_model=PaymentScheduleResponse, status_code=201)
async def create_schedule(
    data: PaymentScheduleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    """Create payment schedule with idempotency support."""
    from app.core.idempotency import check_idempotency, save_idempotency_response

    body_dict = data.model_dump(mode="json")
    existing, idem_key = await check_idempotency(
        db, request, body=body_dict,
        user_id=current_user.id, company_id=company.id,
    )
    if existing:
        from fastapi import Response
        import json
        return Response(
            content=json.dumps(existing.response_body, default=str),
            status_code=existing.response_status,
            media_type="application/json",
            headers={"X-Idempotent-Replay": "true"},
        )

    contract = await db.get(Contract, data.contract_id)
    if not contract or contract.company_id != company.id:
        raise HTTPException(404, "Contract not found")

    svc = PaymentScheduleService(db, company_id=company.id)
    schedule = await svc.create(data, created_by_id=current_user.id)
    log_svc = ActivityLogService(db, company_id=company.id)
    await log_svc.log(
        actor_id=current_user.id,
        action="created",
        entity_type="payment_schedule",
        entity_id=schedule.id,
        description=f"Создан график: {data.months} мес × {data.monthly_payment}",
        debtor_id=contract.debtor_id,
        ip_address=request.client.host if request.client else None,
    )

    if idem_key:
        await save_idempotency_response(
            db, idem_key, request, body_dict,
            {"id": schedule.id, "contract_id": schedule.contract_id, "months": schedule.months},
            status=201, user_id=current_user.id, company_id=company.id,
        )
        await db.commit()
    return schedule


@schedules_router.get("/contract/{contract_id}")
async def get_schedule(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    contract = await db.get(Contract, contract_id)
    if not contract or contract.company_id != company.id:
        raise HTTPException(404, "Contract not found")
    svc = PaymentScheduleService(db, company_id=company.id)
    return await svc.get_for_contract(contract_id)


@schedules_router.post("/payment/{payment_id}/mark-paid")
async def mark_payment(
    payment_id: int,
    paid_amount: float,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    from decimal import Decimal
    svc = PaymentScheduleService(db, company_id=company.id)
    sp = await svc.mark_payment(payment_id, Decimal(str(paid_amount)))
    if not sp:
        raise HTTPException(404, "Not found")
    return sp


# ==================== Kanban / Manager Assignment ====================
kanban_router = APIRouter(prefix="/kanban", tags=["kanban"])


@kanban_router.get("")
async def kanban_board(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    """Get all debtors grouped by kanban_status (current tenant only)"""
    from sqlalchemy import func as sa_func

    q = select(
        Debtor.id, Debtor.full_name, Debtor.iin, Debtor.phone_primary,
        Debtor.kanban_status, Debtor.assigned_manager_id,
        sa_func.coalesce(sa_func.sum(Contract.total_debt), 0).label("total_debt"),
    ).outerjoin(Contract, Contract.debtor_id == Debtor.id) \
     .where(
        Debtor.is_active == True,
        Debtor.company_id == company.id,
        Debtor.deleted_at.is_(None),
    ).group_by(Debtor.id)

    # Manager → only own debtors
    if current_user.role.upper() == "MANAGER":
        q = q.where(Debtor.assigned_manager_id == current_user.id)

    rows = (await db.execute(q)).all()
    columns = {
        "new": [], "contact": [], "promise": [],
        "schedule": [], "overdue": [], "paid": [],
    }
    for r in rows:
        status = r.kanban_status or "new"
        if status not in columns:
            columns[status] = []
        columns[status].append({
            "id": r.id, "full_name": r.full_name, "iin": r.iin,
            "phone": r.phone_primary,
            "total_debt": float(r.total_debt or 0),
            "assigned_manager_id": r.assigned_manager_id,
        })
    return columns


@kanban_router.patch("/debtor/{debtor_id}/status")
async def update_kanban_status(
    debtor_id: int,
    data: KanbanStatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    valid = {"new", "contact", "promise", "schedule", "overdue", "paid"}
    if data.kanban_status not in valid:
        raise HTTPException(400, f"Invalid status. Must be one of {valid}")
    debtor = await db.get(Debtor, debtor_id)
    if not debtor or debtor.company_id != company.id:
        raise HTTPException(404, "Debtor not found")
    old = debtor.kanban_status
    debtor.kanban_status = data.kanban_status

    log_svc = ActivityLogService(db, company_id=company.id)
    await log_svc.log(
        actor_id=current_user.id,
        action="status_changed",
        entity_type="debtor",
        entity_id=debtor_id,
        description=f"Канбан-статус: {old} → {data.kanban_status}",
        changes={"kanban_status": [old, data.kanban_status]},
        debtor_id=debtor_id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return {"ok": True, "kanban_status": debtor.kanban_status}


@kanban_router.patch("/debtor/{debtor_id}/assign")
async def assign_manager(
    debtor_id: int,
    data: AssignManagerRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    if current_user.role.upper() not in ("ADMIN", "HEAD"):
        raise HTTPException(403, "Only admin/head can assign managers")
    debtor = await db.get(Debtor, debtor_id)
    if not debtor or debtor.company_id != company.id:
        raise HTTPException(404, "Debtor not found")
    # Verify manager belongs to same tenant
    if data.manager_id:
        manager = await db.get(User, data.manager_id)
        if not manager or manager.company_id != company.id:
            raise HTTPException(404, "Manager not found")

    old = debtor.assigned_manager_id
    debtor.assigned_manager_id = data.manager_id
    if data.manager_id:
        notif_svc = NotificationService(db, company_id=company.id)
        await notif_svc.create(
            user_id=data.manager_id,
            type="task_assigned",
            title="Новый должник",
            message=f"Вам назначен должник: {debtor.full_name}",
            link=f"/debtors/{debtor_id}",
            debtor_id=debtor_id,
        )
    log_svc = ActivityLogService(db, company_id=company.id)
    await log_svc.log(
        actor_id=current_user.id,
        action="assigned",
        entity_type="debtor",
        entity_id=debtor_id,
        description=f"Менеджер: {old} → {data.manager_id}",
        changes={"assigned_manager_id": [old, data.manager_id]},
        debtor_id=debtor_id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return {"ok": True}


# ==================== Dashboard KPI ====================
dashboard_kpi_router = APIRouter(prefix="/dashboard-kpi", tags=["dashboard"])


@dashboard_kpi_router.get("")
async def dashboard_kpi(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    svc = DashboardKPIService(db, company_id=company.id)
    return await svc.get_dashboard_kpi()


@dashboard_kpi_router.get("/managers")
async def managers_kpi(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    if current_user.role.upper() not in ("ADMIN", "HEAD"):
        raise HTTPException(403, "Forbidden")
    svc = DashboardKPIService(db, company_id=company.id)
    return await svc.get_managers_kpi()


# ==================== Workflow Triggers ====================
workflow_router = APIRouter(prefix="/workflow", tags=["workflow"])


@workflow_router.post("/process-all")
async def process_all_workflows(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    """Manually trigger workflow checks for current tenant"""
    if current_user.role.upper() not in ("ADMIN", "HEAD"):
        raise HTTPException(403, "Forbidden")
    svc = WorkflowService(db, company_id=company.id)
    promises_count = await svc.process_overdue_promises()
    schedules_count = await svc.process_overdue_schedules()
    return {
        "overdue_promises_processed": promises_count,
        "overdue_schedule_payments": schedules_count,
    }
