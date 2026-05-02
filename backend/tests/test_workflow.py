"""Workflow engine tests: overdue promise/schedule processing"""
import pytest
import uuid
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import select
from app.models import Debtor, Contract, Promise
from app.services.saas import WorkflowService
from app.services.debtor import DebtorService
from app.services.contract import ContractService
from app.services.operations import PromiseService
from app.schemas.debtor import DebtorCreate
from app.schemas.operations import ContractCreate, PromiseCreate


@pytest.mark.asyncio
async def test_workflow_marks_overdue_promises(db_session, admin_a_token):
    """Promise with promise_date < today → status='overdue' after WorkflowService.process_overdue_promises()"""
    _, admin_id = admin_a_token

    # Create debtor + contract + overdue promise
    debtor_svc = DebtorService(db_session, company_id=1)
    iin = f"55{uuid.uuid4().hex[:10]}"
    debtor = await debtor_svc.create(
        DebtorCreate(iin=iin, full_name="Overdue Test", phone_primary="+77000000005"),
        actor_id=admin_id,
    )

    contract_svc = ContractService(db_session, company_id=1)
    contract = await contract_svc.create(ContractCreate(
        debtor_id=debtor.id,
        contract_number=f"OVR-{uuid.uuid4().hex[:8]}",
        original_creditor="Bank",
        principal_debt=Decimal("50000"),
        total_debt=Decimal("50000"),
    ))

    promise_svc = PromiseService(db_session, company_id=1)
    promise = await promise_svc.create(
        PromiseCreate(
            contract_id=contract.id,
            amount=Decimal("10000"),
            promise_date=date.today() - timedelta(days=3),  # past date
        ),
        created_by_id=admin_id,
    )
    await db_session.commit()
    promise_id = promise.id

    # Run workflow
    wf_svc = WorkflowService(db_session, company_id=1)
    count = await wf_svc.process_overdue_promises()
    await db_session.commit()

    # Reload promise
    refreshed = await db_session.get(Promise, promise_id)
    assert refreshed.status == "overdue"


@pytest.mark.asyncio
async def test_workflow_isolated_per_tenant(db_session):
    """WorkflowService(company_id=1) does NOT touch promises of company 2"""
    debtor_svc_b = DebtorService(db_session, company_id=2)
    iin = f"44{uuid.uuid4().hex[:10]}"
    debtor_b = await debtor_svc_b.create(
        DebtorCreate(iin=iin, full_name="In B", phone_primary="+77000000006"),
        actor_id=None,
    )
    contract_svc_b = ContractService(db_session, company_id=2)
    contract_b = await contract_svc_b.create(ContractCreate(
        debtor_id=debtor_b.id,
        contract_number=f"B-{uuid.uuid4().hex[:8]}",
        original_creditor="Bank B",
        principal_debt=Decimal("30000"),
        total_debt=Decimal("30000"),
    ))
    promise_svc_b = PromiseService(db_session, company_id=2)
    promise_b = await promise_svc_b.create(
        PromiseCreate(
            contract_id=contract_b.id,
            amount=Decimal("5000"),
            promise_date=date.today() - timedelta(days=5),
        ),
        created_by_id=None,
    )
    await db_session.commit()
    promise_b_id = promise_b.id

    # Run workflow for company A only
    wf_a = WorkflowService(db_session, company_id=1)
    await wf_a.process_overdue_promises()
    await db_session.commit()

    # Promise B should still be 'active' (not touched by A's workflow)
    refreshed = await db_session.get(Promise, promise_b_id)
    assert refreshed.status == "active", "Workflow leaked across tenants!"
