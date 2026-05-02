"""GDPR / Закон о персональных данных РК - export and right to erasure.

Provides:
- GET  /gdpr/export       — full data export (JSON) for the current company
- POST /gdpr/erase-debtor/{id} — irreversibly delete a debtor's PII (compliance only)
"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_roles, get_current_company
from app.models import (
    User, Debtor, Contract, Promise, Payment, CallLog,
    Task, Notification, ActivityLog, PaymentSchedule, Company,
)

router = APIRouter(prefix="/gdpr", tags=["gdpr"])


@router.get("/export")
async def export_company_data(
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    current_user: User = Depends(require_roles("admin")),
):
    """Export all data for current company as a single JSON.

    Returns a downloadable file. Includes: users, debtors, contracts,
    promises, payments, calls, tasks, notifications, activity logs.
    """
    cid = company.id
    data = {
        "company": _to_dict(company),
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "users": [],
        "debtors": [],
        "contracts": [],
        "promises": [],
        "payments": [],
        "call_logs": [],
        "tasks": [],
        "notifications": [],
        "activity_logs": [],
        "payment_schedules": [],
    }

    # Users
    users = (await db.execute(select(User).where(User.company_id == cid))).scalars().all()
    data["users"] = [_to_dict(u, exclude={"hashed_password"}) for u in users]

    # Debtors (including soft-deleted for compliance)
    debtors = (await db.execute(select(Debtor).where(Debtor.company_id == cid))).scalars().all()
    data["debtors"] = [_to_dict(d) for d in debtors]

    # Contracts
    contracts = (await db.execute(select(Contract).where(Contract.company_id == cid))).scalars().all()
    data["contracts"] = [_to_dict(c) for c in contracts]

    # Promises, Payments, CallLogs
    for entity, key in [(Promise, "promises"), (Payment, "payments"), (CallLog, "call_logs")]:
        rows = (await db.execute(select(entity).where(entity.company_id == cid))).scalars().all()
        data[key] = [_to_dict(r) for r in rows]

    # Tasks, Notifications, ActivityLogs
    for entity, key in [(Task, "tasks"), (Notification, "notifications"),
                        (ActivityLog, "activity_logs"), (PaymentSchedule, "payment_schedules")]:
        rows = (await db.execute(select(entity).where(entity.company_id == cid))).scalars().all()
        data[key] = [_to_dict(r) for r in rows]

    return Response(
        content=json.dumps(data, default=str, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="company_{cid}_export_{datetime.utcnow().strftime("%Y%m%d")}.json"'
        },
    )


@router.post("/erase-debtor/{debtor_id}")
async def erase_debtor_pii(
    debtor_id: int,
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    current_user: User = Depends(require_roles("admin")),
):
    """Right to be forgotten: anonymize a debtor's PII (irreversible).

    Replaces full_name, phone_*, address, email with anonymized placeholders.
    Does NOT delete the record entirely — keeps financial audit trail.
    """
    debtor = await db.get(Debtor, debtor_id)
    if not debtor or debtor.company_id != company.id:
        raise HTTPException(404, "Debtor not found")

    # Anonymize PII fields
    debtor.full_name = f"<ERASED-{debtor_id}>"
    if hasattr(debtor, "phone_primary"):
        debtor.phone_primary = None
    if hasattr(debtor, "phone_secondary"):
        debtor.phone_secondary = None
    if hasattr(debtor, "address"):
        debtor.address = None
    if hasattr(debtor, "email"):
        debtor.email = None
    if hasattr(debtor, "employer"):
        debtor.employer = None
    if hasattr(debtor, "employer_phone"):
        debtor.employer_phone = None
    if hasattr(debtor, "iin"):
        debtor.iin = f"ERASED-{debtor_id}"
    debtor.deleted_at = datetime.utcnow()

    # Audit log
    log = ActivityLog(
        actor_id=current_user.id,
        action="gdpr_erased",
        entity_type="debtor",
        entity_id=debtor_id,
        description=f"PII erased per GDPR/right to be forgotten request",
        company_id=company.id,
    )
    db.add(log)
    await db.commit()
    return {"erased": True, "debtor_id": debtor_id}


def _to_dict(obj, exclude: set | None = None) -> dict:
    """Convert SQLAlchemy model to dict, excluding specified fields"""
    exclude = exclude or set()
    return {
        c.name: _serialize(getattr(obj, c.name))
        for c in obj.__table__.columns
        if c.name not in exclude
    }


def _serialize(v):
    if isinstance(v, datetime):
        return v.isoformat() + "Z"
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v
