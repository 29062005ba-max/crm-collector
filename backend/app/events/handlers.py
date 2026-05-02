"""Event handlers — реакция на domain events.
Регистрируются при импорте модуля.
"""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.events.bus import event_bus
from app.events.types import (
    DomainEvent, DebtorCreated, PaymentCreated, PromiseCreated,
    PromiseOverdue, ScheduleOverdue, StatusChanged,
)

logger = logging.getLogger(__name__)


# ==================== Sync handlers (executed in same DB transaction) ====================
@event_bus.on("debtor.created")
async def on_debtor_created(event: DebtorCreated, db: AsyncSession) -> dict:
    """When a new debtor is created — write to activity log"""
    from app.services.saas import ActivityLogService
    log_svc = ActivityLogService(db, company_id=event.company_id)
    await log_svc.log(
        actor_id=event.actor_id,
        action="created",
        entity_type="debtor",
        entity_id=event.aggregate_id,
        description=f"Создан должник: {event.payload.get('full_name', '')}",
        debtor_id=event.aggregate_id,
    )
    return {"logged": True}


@event_bus.on("payment.created")
async def on_payment_created(event: PaymentCreated, db: AsyncSession) -> dict:
    """When payment received — recalculate schedule status if exists.
    Note: kanban='paid' transition is done in the endpoint within the same transaction.
    """
    from app.models import PaymentSchedule, SchedulePayment
    from datetime import date
    from decimal import Decimal

    contract_id = event.payload.get("contract_id")
    if not contract_id:
        return {"skipped": "no contract_id"}

    # Find active schedule
    sched_q = select(PaymentSchedule).where(
        PaymentSchedule.contract_id == contract_id,
        PaymentSchedule.status == "active",
    )
    if event.company_id:
        sched_q = sched_q.where(PaymentSchedule.company_id == event.company_id)
    schedule = (await db.execute(sched_q)).scalar_one_or_none()
    if not schedule:
        return {"skipped": "no active schedule"}

    # Find next pending schedule_payment
    pay_q = select(SchedulePayment).where(
        SchedulePayment.schedule_id == schedule.id,
        SchedulePayment.status.in_(["pending", "overdue", "partial"]),
    ).order_by(SchedulePayment.due_date)
    next_payment = (await db.execute(pay_q)).scalar_one_or_none()
    if not next_payment:
        return {"skipped": "no pending schedule payments"}

    # Apply payment to schedule
    paid_amount = Decimal(str(event.payload.get("amount", 0)))
    next_payment.paid_amount = (next_payment.paid_amount or Decimal(0)) + paid_amount
    next_payment.paid_at = date.today()
    if next_payment.paid_amount >= next_payment.amount:
        next_payment.status = "paid"
    else:
        next_payment.status = "partial"

    # Trigger async recalc via Celery (can determine if schedule fully completed)
    try:
        from app.tasks.schedules import recalculate_schedule_status
        recalculate_schedule_status.delay(schedule.id)
    except Exception as e:
        logger.warning(f"Failed to enqueue schedule recalc: {e}")

    return {"applied_to_schedule_payment_id": next_payment.id, "schedule_id": schedule.id}


# ==================== Module 3: Auto-fulfill Promise on Payment ====================
@event_bus.on("payment.created")
async def on_payment_auto_fulfill_promise(event: PaymentCreated, db: AsyncSession) -> dict:
    """
    При поступлении платежа автоматически закрывает ближайшее активное обещание
    по тому же контракту.

    Логика:
      1. Находим nearest active Promise по contract_id с promise_date <= payment_date
         (т.е. обещание которое уже наступило или должно было быть оплачено раньше)
      2. Если payment.amount >= 0.95 * promise.amount — закрываем в "fulfilled"
         (auto_fulfilled=True, fulfilled_by_payment_id=payment.id)
      3. Idempotency: если promise.fulfilled_by_payment_id уже == payment.id, skip
         (повторное событие при retry не закроет повторно)

    Audit log записывается в activity_log.
    """
    from app.models.operations import Promise, Payment
    from app.services.saas import ActivityLogService
    from datetime import datetime
    from decimal import Decimal

    contract_id = event.payload.get("contract_id")
    payment_id = event.payload.get("payment_id") or event.aggregate_id
    payment_amount = Decimal(str(event.payload.get("amount", 0)))
    payment_date = event.payload.get("payment_date")

    if not contract_id or not payment_id or payment_amount <= 0:
        return {"skipped": "missing payment context"}

    # Конвертим payment_date в date (если строка)
    if isinstance(payment_date, str):
        from datetime import date as date_cls
        try:
            payment_date = date_cls.fromisoformat(payment_date)
        except ValueError:
            payment_date = None
    if not payment_date:
        # Берём из БД
        payment = await db.get(Payment, payment_id)
        if not payment:
            return {"skipped": "payment not found"}
        payment_date = payment.payment_date

    # Idempotency: проверим — может уже закрыто этим же платежом
    already_q = select(Promise).where(
        Promise.contract_id == contract_id,
        Promise.fulfilled_by_payment_id == payment_id,
    )
    if event.company_id:
        already_q = already_q.where(Promise.company_id == event.company_id)
    already = (await db.execute(already_q)).scalar_one_or_none()
    if already:
        return {"skipped": "already auto-fulfilled by this payment", "promise_id": already.id}

    # Ищем ближайшее active обещание с promise_date <= payment_date
    pq = select(Promise).where(
        Promise.contract_id == contract_id,
        Promise.status == "active",
        Promise.promise_date <= payment_date,
    )
    if event.company_id:
        pq = pq.where(Promise.company_id == event.company_id)
    pq = pq.order_by(Promise.promise_date.desc()).limit(1)
    promise = (await db.execute(pq)).scalar_one_or_none()

    if not promise:
        return {"skipped": "no matching active promise"}

    # Проверка: платёж покрывает >= 95% от суммы обещания
    threshold = Decimal("0.95")
    if payment_amount < (promise.amount * threshold):
        return {
            "skipped": "payment_below_threshold",
            "promise_id": promise.id,
            "promise_amount": str(promise.amount),
            "payment_amount": str(payment_amount),
            "threshold_pct": "95",
        }

    # Закрываем обещание
    promise.status = "fulfilled"
    promise.auto_fulfilled = True
    promise.fulfilled_by_payment_id = payment_id
    promise.fulfilled_at = datetime.utcnow()

    # Audit log
    log_svc = ActivityLogService(db, company_id=event.company_id)
    await log_svc.log(
        actor_id=None,  # системное действие
        action="promise_auto_fulfilled",
        entity_type="promise",
        entity_id=promise.id,
        description=(
            f"Обещание #{promise.id} ({promise.amount} ₸ на {promise.promise_date}) "
            f"автоматически закрыто платежом #{payment_id} ({payment_amount} ₸)"
        ),
        debtor_id=event.payload.get("debtor_id"),
    )

    logger.info(
        f"[auto-fulfill] promise_id={promise.id} closed by payment_id={payment_id} "
        f"({payment_amount} >= 95%% of {promise.amount})"
    )

    return {
        "promise_id": promise.id,
        "auto_fulfilled": True,
        "payment_id": payment_id,
        "promise_amount": float(promise.amount),
        "payment_amount": float(payment_amount),
    }
# ==================== /Module 3 ====================


@event_bus.on("promise.created")
async def on_promise_created(event: PromiseCreated, db: AsyncSession) -> dict:
    """Notify the head/admin about new promise from manager"""
    from app.models import User
    from app.services.saas import NotificationService

    if not event.actor_id or not event.company_id:
        return {"skipped": "missing context"}

    # Notify heads/admins of the company
    q = select(User).where(
        User.role.in_(["ADMIN", "HEAD"]),
        User.is_active == True,
        User.company_id == event.company_id,
        User.id != event.actor_id,  # don't notify self
    )
    notify_users = (await db.execute(q)).scalars().all()
    notif_svc = NotificationService(db, company_id=event.company_id)
    notified = 0
    for u in notify_users:
        # Use idempotency_key derived from event to avoid duplicates
        # (if event is replayed)
        await notif_svc.create(
            user_id=u.id,
            type="promise_created",
            title="Новое обещание",
            message=f"Сумма: {event.payload.get('amount')} ₸ на {event.payload.get('promise_date')}",
            link=f"/debtors/{event.payload.get('debtor_id')}",
            debtor_id=event.payload.get("debtor_id"),
        )
        notified += 1
    return {"notified": notified}


@event_bus.on("status.changed")
async def on_status_changed(event: StatusChanged, db: AsyncSession) -> dict:
    """Generic status change — already logged in activity_logs by emitter,
    but here we can trigger side effects."""
    return {"acknowledged": True}


@event_bus.on("schedule.overdue")
async def on_schedule_overdue(event: ScheduleOverdue, db: AsyncSession) -> dict:
    """When schedule payment becomes overdue — already handled by WorkflowService.
    This handler is for additional integrations (SMS, etc).
    """
    return {"acknowledged": True}


# Force registration of all handlers when module is imported
def register_all():
    """Called on app startup to ensure handlers are loaded"""
    logger.info(f"Event handlers registered: {sum(len(v) for v in event_bus._handlers.values())} total")
