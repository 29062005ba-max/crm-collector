"""Billing endpoints: subscription status, Stripe webhook handler.

Stripe integration is OPTIONAL. Without STRIPE_SECRET_KEY env, this provides
read-only views and manual tariff management for testing.
"""
import os
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Request, HTTPException, Header
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_roles, get_current_company
from app.models import User, Company, Subscription, Invoice, StripeWebhookEvent

router = APIRouter(prefix="/billing", tags=["billing"])
logger = logging.getLogger(__name__)

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


@router.get("/subscription")
async def get_my_subscription(
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    current_user: User = Depends(require_roles("admin", "head")),
):
    """Get current company's subscription status"""
    sub = (await db.execute(
        select(Subscription).where(Subscription.company_id == company.id)
    )).scalar_one_or_none()
    if not sub:
        return {
            "status": "no_subscription",
            "company_tariff": company.tariff,
            "trial_available": True,
        }
    return {
        "id": sub.id,
        "tariff": sub.tariff,
        "status": sub.status,
        "current_period_start": sub.current_period_start,
        "current_period_end": sub.current_period_end,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "trial_ends_at": sub.trial_ends_at,
        "amount_per_month": float(sub.amount_per_month) if sub.amount_per_month else None,
        "currency": sub.currency,
    }


@router.get("/invoices")
async def list_invoices(
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    current_user: User = Depends(require_roles("admin", "head")),
):
    """List company invoices (most recent first)"""
    rows = (await db.execute(
        select(Invoice).where(Invoice.company_id == company.id).order_by(desc(Invoice.created_at)).limit(100)
    )).scalars().all()
    return [
        {
            "id": i.id,
            "invoice_number": i.invoice_number,
            "amount": float(i.amount),
            "currency": i.currency,
            "status": i.status,
            "period_start": i.period_start,
            "period_end": i.period_end,
            "paid_at": i.paid_at,
            "pdf_url": i.pdf_url,
            "created_at": i.created_at,
        }
        for i in rows
    ]


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Stripe webhook receiver.
    Processes: customer.subscription.created/updated/deleted, invoice.paid, invoice.payment_failed
    Verifies signature using STRIPE_WEBHOOK_SECRET.
    Idempotent — uses Stripe event_id as dedup key.
    """
    payload = await request.body()

    # Verify signature
    if STRIPE_WEBHOOK_SECRET:
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, STRIPE_WEBHOOK_SECRET
            )
        except Exception as e:
            raise HTTPException(400, f"Invalid signature: {e}")
    else:
        # Dev mode — accept without verification
        event = json.loads(payload.decode())

    event_id = event.get("id")
    event_type = event.get("type")

    # Idempotency check
    existing = (await db.execute(
        select(StripeWebhookEvent).where(StripeWebhookEvent.stripe_event_id == event_id)
    )).scalar_one_or_none()
    if existing and existing.processed:
        return {"received": True, "duplicate": True}

    # Persist event
    if not existing:
        wh = StripeWebhookEvent(
            stripe_event_id=event_id,
            event_type=event_type,
            payload=event,
        )
        db.add(wh)
        await db.flush()
    else:
        wh = existing

    # Dispatch to handlers
    try:
        if event_type == "customer.subscription.created":
            await _handle_subscription_created(db, event["data"]["object"])
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(db, event["data"]["object"])
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(db, event["data"]["object"])
        elif event_type == "invoice.paid":
            await _handle_invoice_paid(db, event["data"]["object"])
        elif event_type == "invoice.payment_failed":
            await _handle_invoice_payment_failed(db, event["data"]["object"])
        else:
            logger.info(f"Unhandled Stripe event type: {event_type}")

        wh.processed = True
        wh.processed_at = datetime.utcnow()
        await db.commit()
        return {"received": True, "processed": True}
    except Exception as e:
        wh.error = str(e)
        await db.commit()
        logger.exception(f"Webhook handler error: {e}")
        raise HTTPException(500, "Webhook processing error")


# ==================== Webhook handlers ====================
async def _handle_subscription_created(db: AsyncSession, obj: dict):
    customer_id = obj.get("customer")
    sub_id = obj.get("id")
    metadata = obj.get("metadata", {})
    company_id = int(metadata.get("company_id", 0))
    if not company_id:
        return
    sub = (await db.execute(
        select(Subscription).where(Subscription.company_id == company_id)
    )).scalar_one_or_none()
    if not sub:
        sub = Subscription(company_id=company_id)
        db.add(sub)
    sub.stripe_customer_id = customer_id
    sub.stripe_subscription_id = sub_id
    sub.status = obj.get("status", "active")
    sub.tariff = metadata.get("tariff", "pro")
    if obj.get("current_period_start"):
        sub.current_period_start = datetime.fromtimestamp(obj["current_period_start"])
    if obj.get("current_period_end"):
        sub.current_period_end = datetime.fromtimestamp(obj["current_period_end"])
    await db.flush()


async def _handle_subscription_updated(db: AsyncSession, obj: dict):
    sub = (await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == obj["id"])
    )).scalar_one_or_none()
    if not sub:
        return
    sub.status = obj.get("status", sub.status)
    sub.cancel_at_period_end = obj.get("cancel_at_period_end", False)
    if obj.get("current_period_end"):
        sub.current_period_end = datetime.fromtimestamp(obj["current_period_end"])


async def _handle_subscription_deleted(db: AsyncSession, obj: dict):
    sub = (await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == obj["id"])
    )).scalar_one_or_none()
    if sub:
        sub.status = "canceled"


async def _handle_invoice_paid(db: AsyncSession, obj: dict):
    inv = Invoice(
        company_id=int(obj.get("metadata", {}).get("company_id", 0)) or 1,
        stripe_invoice_id=obj.get("id"),
        invoice_number=obj.get("number") or obj.get("id"),
        amount=obj.get("amount_paid", 0) / 100,
        currency=obj.get("currency", "kzt").upper(),
        status="paid",
        paid_at=datetime.utcnow(),
        pdf_url=obj.get("invoice_pdf"),
    )
    db.add(inv)


async def _handle_invoice_payment_failed(db: AsyncSession, obj: dict):
    sub_id = obj.get("subscription")
    if not sub_id:
        return
    sub = (await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == sub_id)
    )).scalar_one_or_none()
    if sub:
        sub.status = "past_due"
