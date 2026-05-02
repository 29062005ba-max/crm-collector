from fastapi import APIRouter, Depends, Request, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.operations import (
    PromiseCreate, PromiseUpdate, PromiseResponse,
    PaymentCreate, PaymentResponse,
    CallLogCreate, CallLogResponse,
    CsiCaseCreate, CsiCaseUpdate, CsiCaseResponse,
)
from app.services.operations import PromiseService, PaymentService, CallLogService, CsiCaseService
from app.core.deps import get_current_active_user, get_current_company
from app.models.user import User
from app.models.company import Company
from app.services.saas import ActivityLogService, NotificationService

# --- Promises ---
promises_router = APIRouter(prefix="/promises", tags=["promises"])


@promises_router.post("/", response_model=PromiseResponse, status_code=201)
async def create_promise(
    data: PromiseCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    """Create promise with idempotency support."""
    from app.core.idempotency import check_idempotency, save_idempotency_response
    from app.events import event_bus, PromiseCreated
    from app.models import Contract, Debtor

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

    service = PromiseService(db, company_id=company.id)
    promise = await service.create(data, current_user.id)

    contract = await db.get(Contract, data.contract_id)
    if contract:
        log = ActivityLogService(db, company_id=company.id)
        await log.log(
            actor_id=current_user.id, action="created", entity_type="promise",
            entity_id=promise.id,
            description=f"Создано обещание на {data.amount} ₸ к {data.promise_date}",
            debtor_id=contract.debtor_id,
            ip_address=request.client.host if request.client else None,
        )
        # Update kanban
        debtor = await db.get(Debtor, contract.debtor_id)
        if debtor and debtor.kanban_status in ("new", "contact"):
            debtor.kanban_status = "promise"

        # Publish event
        try:
            await event_bus.publish(
                PromiseCreated(
                    aggregate_id=promise.id,
                    company_id=company.id,
                    actor_id=current_user.id,
                    payload={
                        "amount": float(promise.amount),
                        "promise_date": str(promise.promise_date),
                        "contract_id": data.contract_id,
                        "debtor_id": contract.debtor_id,
                    },
                    idempotency_key=idem_key,
                ),
                db,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to publish PromiseCreated: {e}")

    # Save idempotency response
    if idem_key:
        response_body = {
            "id": promise.id, "contract_id": promise.contract_id,
            "amount": float(promise.amount), "promise_date": str(promise.promise_date),
            "status": promise.status,
        }
        await save_idempotency_response(
            db, idem_key, request, body_dict, response_body,
            status=201, user_id=current_user.id, company_id=company.id,
        )

    await db.commit()
    return promise


@promises_router.get("/contract/{contract_id}", response_model=list[PromiseResponse])
async def list_promises(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = PromiseService(db, company_id=company.id)
    return await service.list_by_contract(contract_id)


@promises_router.get("/all")
async def list_all_promises(
    status: str = Query(default=None),
    manager_id: int = Query(default=None),
    page: int = Query(default=1),
    page_size: int = Query(default=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    from sqlalchemy import select, func, and_
    from app.models.operations import Promise, Assignment
    from app.models.contract import Contract
    from app.models.debtor import Debtor

    q = (
        select(Promise, Contract.contract_number, Debtor.full_name, Debtor.id.label("debtor_id"))
        .join(Contract, Contract.id == Promise.contract_id)
        .join(Debtor, Debtor.id == Contract.debtor_id)
    )
    filters = [Promise.company_id == company.id, Promise.deleted_at.is_(None)]
    if status:
        filters.append(Promise.status == status)
    if current_user.role.upper() == "MANAGER":
        assigned = select(Assignment.contract_id).where(
            and_(Assignment.manager_id == current_user.id, Assignment.is_active == True)
        )
        filters.append(Promise.contract_id.in_(assigned))
    elif manager_id:
        assigned = select(Assignment.contract_id).where(
            and_(Assignment.manager_id == manager_id, Assignment.is_active == True)
        )
        filters.append(Promise.contract_id.in_(assigned))
    if filters:
        q = q.where(and_(*filters))

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.order_by(Promise.promise_date.desc()).offset((page-1)*page_size).limit(page_size))).all()

    return {
        "total": total,
        "page": page,
        "items": [
            {
                "id": r.Promise.id,
                "contract_id": r.Promise.contract_id,
                "contract_number": r.contract_number,
                "debtor_name": r.full_name,
                "debtor_id": r.debtor_id,
                "amount": float(r.Promise.amount),
                "promise_date": str(r.Promise.promise_date),
                "status": r.Promise.status,
                "notes": r.Promise.notes,
            }
            for r in rows
        ]
    }


@promises_router.patch("/{promise_id}", response_model=PromiseResponse)
async def update_promise(
    promise_id: int,
    data: PromiseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = PromiseService(db, company_id=company.id)
    return await service.update(promise_id, data)


@promises_router.delete("/{promise_id}")
async def delete_promise(
    promise_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    from sqlalchemy import delete as sql_delete
    from app.models.operations import Promise
    await db.execute(sql_delete(Promise).where(Promise.id == promise_id))
    await db.commit()
    return {"deleted": True}


@promises_router.post("/process-overdue")
async def process_overdue_promises(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = PromiseService(db, company_id=company.id)
    count = await service.process_overdue()
    return {"marked_overdue": count}


# --- Payments ---
payments_router = APIRouter(prefix="/payments", tags=["payments"])


@payments_router.post("/", response_model=PaymentResponse, status_code=201)
async def create_payment(
    data: PaymentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    """Create payment with idempotency + concurrency safety.

    Pass `Idempotency-Key` header for safe retry. Same key + same body → returns saved response.
    """
    from app.core.idempotency import check_idempotency, save_idempotency_response
    from app.core.locking import get_for_update
    from app.events import event_bus, PaymentCreated
    from app.models import Contract, Debtor

    # 1. Idempotency check
    body_dict = data.model_dump(mode="json")
    existing, idem_key = await check_idempotency(
        db, request, body=body_dict,
        user_id=current_user.id, company_id=company.id,
    )
    if existing:
        # Return saved response
        from fastapi import Response
        import json
        return Response(
            content=json.dumps(existing.response_body, default=str),
            status_code=existing.response_status,
            media_type="application/json",
            headers={"X-Idempotent-Replay": "true"},
        )

    # 2. Lock contract row to prevent concurrent payment creation
    contract = await get_for_update(db, Contract, data.contract_id)
    if not contract or contract.company_id != company.id:
        raise HTTPException(404, "Contract not found")

    # 3. Create payment
    service = PaymentService(db, company_id=company.id)
    payment = await service.create(data, current_user.id)

    # 4. Activity log
    log = ActivityLogService(db, company_id=company.id)
    await log.log(
        actor_id=current_user.id, action="created", entity_type="payment",
        entity_id=payment.id,
        description=f"Платёж {data.amount} ₸ ({data.source})",
        debtor_id=contract.debtor_id,
        ip_address=request.client.host if request.client else None,
    )

    # 5. If full debt paid → mark debtor paid (within same transaction = atomic)
    from sqlalchemy import select, func as sa_func
    from app.models import Payment as PaymentModel
    total_paid = (await db.execute(
        select(sa_func.coalesce(sa_func.sum(PaymentModel.amount), 0))
        .where(PaymentModel.contract_id == contract.id, PaymentModel.deleted_at.is_(None))
    )).scalar() or 0
    if float(total_paid) >= float(contract.total_debt or 0):
        debtor = await get_for_update(db, Debtor, contract.debtor_id)
        if debtor and debtor.kanban_status != "paid":
            debtor.kanban_status = "paid"

    # 6. Publish event (async handlers will react via Celery)
    try:
        await event_bus.publish(
            PaymentCreated(
                aggregate_id=payment.id,
                company_id=company.id,
                actor_id=current_user.id,
                payload={
                    "amount": float(payment.amount),
                    "source": payment.source,
                    "contract_id": data.contract_id,
                    "debtor_id": contract.debtor_id,
                },
                idempotency_key=idem_key,
            ),
            db,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to publish PaymentCreated: {e}")

    # 7. Save idempotency response
    response_body = {
        "id": payment.id,
        "contract_id": payment.contract_id,
        "amount": float(payment.amount),
        "payment_date": str(payment.payment_date),
        "source": payment.source,
        "notes": payment.notes,
    }
    if idem_key:
        await save_idempotency_response(
            db, idem_key, request, body_dict, response_body,
            status=201, user_id=current_user.id, company_id=company.id,
        )

    await db.commit()
    return payment


@payments_router.get("/contract/{contract_id}", response_model=list[PaymentResponse])
async def list_payments(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = PaymentService(db, company_id=company.id)
    return await service.list_by_contract(contract_id)


@payments_router.get("/all")
async def list_all_payments(
    manager_id: int = Query(default=None),
    date_from: str = Query(default=None),
    date_to: str = Query(default=None),
    source: str = Query(default=None),
    page: int = Query(default=1),
    page_size: int = Query(default=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    from sqlalchemy import select, func, and_
    from datetime import date as date_cls
    from app.models.operations import Payment, Assignment
    from app.models.contract import Contract
    from app.models.debtor import Debtor

    from app.models.user import User as UserModel
    q = (
        select(Payment, Contract.contract_number, Debtor.full_name, Debtor.id.label("debtor_id"), UserModel.full_name.label("manager_name"))
        .join(Contract, Contract.id == Payment.contract_id)
        .join(Debtor, Debtor.id == Contract.debtor_id)
        .outerjoin(UserModel, UserModel.id == Payment.registered_by_id)
    )
    filters = [Payment.company_id == company.id, Payment.deleted_at.is_(None)]
    if date_from:
        try:
            filters.append(Payment.payment_date >= date_cls.fromisoformat(date_from))
        except Exception:
            pass
    if date_to:
        try:
            filters.append(Payment.payment_date <= date_cls.fromisoformat(date_to))
        except Exception:
            pass
    if source:
        filters.append(Payment.source == source)
    if current_user.role.upper() == "MANAGER":
        assigned = select(Assignment.contract_id).where(
            and_(Assignment.manager_id == current_user.id, Assignment.is_active == True)
        )
        filters.append(Payment.contract_id.in_(assigned))
    elif manager_id:
        assigned = select(Assignment.contract_id).where(
            and_(Assignment.manager_id == manager_id, Assignment.is_active == True)
        )
        filters.append(Payment.contract_id.in_(assigned))
    if filters:
        q = q.where(and_(*filters))

    # Сохраняем subquery один раз чтобы фильтры применялись везде
    filtered_subq = q.subquery()
    total = (await db.execute(select(func.count()).select_from(filtered_subq))).scalar_one()
    total_amount_result = (await db.execute(
        select(func.sum(filtered_subq.c.amount))
    )).scalar_one() or 0
    rows = (await db.execute(q.order_by(Payment.payment_date.desc()).offset((page-1)*page_size).limit(page_size))).all()

    return {
        "total": total,
        "total_amount": float(total_amount_result),
        "page": page,
        "items": [
            {
                "id": r.Payment.id,
                "contract_id": r.Payment.contract_id,
                "contract_number": r.contract_number,
                "debtor_name": r.full_name,
                "debtor_id": r.debtor_id,
                "amount": float(r.Payment.amount),
                "payment_date": str(r.Payment.payment_date),
                "source": r.Payment.source,
                "manager_name": r.manager_name or "—",
                "receipt_path": r.Payment.receipt_path,
                "notes": r.Payment.notes,
            }
            for r in rows
        ]
    }


@payments_router.post("/{payment_id}/receipt")
async def upload_receipt(
    payment_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    """Загрузить чек к платежу."""
    import os, uuid
    from fastapi import UploadFile, File
    from sqlalchemy import select
    from app.models.operations import Payment

    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment or payment.company_id != company.id or getattr(payment, "deleted_at", None) is not None:
        from fastapi import HTTPException
        raise HTTPException(404, "Платёж не найден")

    # Сохраняем файл
    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    allowed = {".jpg", ".jpeg", ".png", ".pdf", ".heic"}
    if ext not in allowed:
        from fastapi import HTTPException
        raise HTTPException(400, f"Разрешены только: {', '.join(allowed)}")

    receipts_dir = "/app/receipts"
    os.makedirs(receipts_dir, exist_ok=True)
    filename = f"payment_{payment_id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(receipts_dir, filename)

    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    payment.receipt_path = filename
    await db.commit()

    return {"receipt_path": filename, "url": f"/api/v1/payments/{payment_id}/receipt/view"}


@payments_router.get("/{payment_id}/receipt/view")
async def view_receipt(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    """Показать чек платежа."""
    import os
    from fastapi.responses import Response
    from fastapi import HTTPException
    from sqlalchemy import select
    from app.models.operations import Payment

    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()
    if not payment or not payment.receipt_path or payment.company_id != company.id or getattr(payment, "deleted_at", None) is not None:
        raise HTTPException(404, "Чек не найден")

    filepath = f"/app/receipts/{payment.receipt_path}"
    if not os.path.exists(filepath):
        raise HTTPException(404, "Файл чека не найден")

    ext = os.path.splitext(payment.receipt_path)[1].lower()
    content_types = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
    mime = content_types.get(ext, "application/octet-stream")

    with open(filepath, "rb") as f:
        data = f.read()

    return Response(content=data, media_type=mime, headers={"Content-Disposition": "inline"})

@payments_router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = PaymentService(db, company_id=company.id)
    return await service.get(payment_id)


# --- Call Logs ---
calls_router = APIRouter(prefix="/calls", tags=["calls"])


@calls_router.post("/", response_model=CallLogResponse, status_code=201)
async def create_call_log(
    data: CallLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = CallLogService(db, company_id=company.id)
    return await service.create(data, current_user.id)


@calls_router.get("/contract/{contract_id}", response_model=list[CallLogResponse])
async def list_call_logs(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = CallLogService(db, company_id=company.id)
    return await service.list_by_contract(contract_id)


# --- CSI Cases ---
csi_router = APIRouter(prefix="/csi", tags=["csi"])


@csi_router.post("/", response_model=CsiCaseResponse, status_code=201)
async def create_csi_case(
    data: CsiCaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = CsiCaseService(db, company_id=company.id)
    return await service.create(data)


@csi_router.get("/debtor/{debtor_id}", response_model=list[CsiCaseResponse])
async def list_csi_cases(
    debtor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = CsiCaseService(db, company_id=company.id)
    return await service.list_by_debtor(debtor_id)


@csi_router.patch("/{case_id}", response_model=CsiCaseResponse)
async def update_csi_case(
    case_id: int,
    data: CsiCaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    company: Company = Depends(get_current_company),
):
    service = CsiCaseService(db, company_id=company.id)
    return await service.update(case_id, data)
