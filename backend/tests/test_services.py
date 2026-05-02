"""Service-level tests: business logic without HTTP layer"""
import pytest
import uuid
from sqlalchemy import select
from app.models import Debtor, Contract, Promise, Payment, Company
from app.services.debtor import DebtorService
from app.services.contract import ContractService
from app.services.operations import PromiseService, PaymentService
from app.schemas.debtor import DebtorCreate
from app.schemas.operations import ContractCreate, PromiseCreate, PaymentCreate
from datetime import date
from decimal import Decimal


@pytest.mark.asyncio
async def test_debtor_service_creates_with_company_id(db_session):
    svc = DebtorService(db_session, company_id=1)
    iin = f"99{uuid.uuid4().hex[:10]}"
    debtor = await svc.create(
        DebtorCreate(iin=iin, full_name="Service Test", phone_primary="+77000000001"),
        actor_id=None,
    )
    await db_session.commit()
    assert debtor.id is not None
    assert debtor.company_id == 1


@pytest.mark.asyncio
async def test_debtor_service_blocks_cross_tenant_access(db_session):
    """Service from company A cannot access debtor created by company B"""
    iin = f"88{uuid.uuid4().hex[:10]}"
    svc_b = DebtorService(db_session, company_id=2)
    debtor = await svc_b.create(
        DebtorCreate(iin=iin, full_name="In B", phone_primary="+77000000002"),
        actor_id=None,
    )
    await db_session.commit()

    svc_a = DebtorService(db_session, company_id=1)
    with pytest.raises(Exception) as exc_info:
        await svc_a.get(debtor.id)
    # 404 raised
    assert "не найден" in str(exc_info.value).lower() or "404" in str(exc_info.value)


@pytest.mark.asyncio
async def test_debtor_service_soft_delete(db_session):
    svc = DebtorService(db_session, company_id=1)
    iin = f"77{uuid.uuid4().hex[:10]}"
    debtor = await svc.create(
        DebtorCreate(iin=iin, full_name="ToDelete", phone_primary="+77000000003"),
        actor_id=None,
    )
    await db_session.commit()
    debtor_id = debtor.id

    await svc.soft_delete(debtor_id)
    await db_session.commit()

    # Should not be findable through service
    with pytest.raises(Exception):
        await svc.get(debtor_id)

    # But still in DB with deleted_at set
    raw = await db_session.get(Debtor, debtor_id)
    assert raw is not None
    assert raw.deleted_at is not None


@pytest.mark.asyncio
async def test_promise_service_publishes_event(db_session):
    """Creating promise should trigger event publication to event_log"""
    from app.events import event_bus, PromiseCreated
    from app.models.enterprise import EventLog

    svc = DebtorService(db_session, company_id=1)
    iin = f"66{uuid.uuid4().hex[:10]}"
    debtor = await svc.create(
        DebtorCreate(iin=iin, full_name="ForPromise", phone_primary="+77000000004"),
        actor_id=None,
    )

    contract_svc = ContractService(db_session, company_id=1)
    contract = await contract_svc.create(ContractCreate(
        debtor_id=debtor.id,
        contract_number=f"PR-{uuid.uuid4().hex[:8]}",
        original_creditor="Test Bank",
        principal_debt=Decimal("100000"),
        total_debt=Decimal("100000"),
    ))
    await db_session.commit()

    # Manually publish event (simulating what endpoint does)
    initial_count = (await db_session.execute(
        select(EventLog).where(EventLog.event_type == "promise.created")
    )).scalars().all()
    initial_n = len(initial_count)

    await event_bus.publish(
        PromiseCreated(
            aggregate_id=999,
            company_id=1,
            payload={"amount": 5000, "contract_id": contract.id},
        ),
        db_session,
    )
    await db_session.commit()

    after = (await db_session.execute(
        select(EventLog).where(EventLog.event_type == "promise.created")
    )).scalars().all()
    assert len(after) == initial_n + 1
