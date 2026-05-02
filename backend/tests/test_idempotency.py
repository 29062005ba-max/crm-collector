"""Tests for Idempotency-Key behavior on critical endpoints"""
import pytest
import uuid


@pytest.mark.asyncio
async def test_payment_idempotency_returns_same_result(client, admin_a_token):
    """Same Idempotency-Key + same body → second call returns cached response, no duplicate"""
    token, _ = admin_a_token

    # First create a debtor + contract for the test
    rd = await client.post(
        "/api/v1/debtors/",
        headers={"Authorization": f"Bearer {token}"},
        json={"iin": "030303030303", "full_name": "Idem Test", "phone_primary": "+77003334455"},
    )
    assert rd.status_code == 201
    debtor_id = rd.json()["id"]

    rc = await client.post(
        "/api/v1/contracts/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "debtor_id": debtor_id,
            "contract_number": f"IDEM-{uuid.uuid4().hex[:8]}",
            "original_creditor": "Test Bank",
            "principal_debt": "100000",
            "total_debt": "100000",
        },
    )
    assert rc.status_code == 201, rc.text
    contract_id = rc.json()["id"]

    idem_key = f"test-payment-{uuid.uuid4().hex}"
    body = {
        "contract_id": contract_id,
        "amount": "10000",
        "payment_date": "2026-04-25",
        "source": "cash",
    }

    # First request
    r1 = await client.post(
        "/api/v1/payments/",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idem_key},
        json=body,
    )
    assert r1.status_code == 201, r1.text
    payment_id_1 = r1.json()["id"]

    # Second request with same idempotency key
    r2 = await client.post(
        "/api/v1/payments/",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idem_key},
        json=body,
    )
    assert r2.status_code == 201
    assert r2.headers.get("X-Idempotent-Replay") == "true", "Should mark as idempotent replay"
    assert r2.json()["id"] == payment_id_1, "Should return same payment, not create new one"


@pytest.mark.asyncio
async def test_idempotency_conflict_with_different_body(client, admin_a_token):
    """Same key but different body → 409 Conflict"""
    token, _ = admin_a_token

    rd = await client.post(
        "/api/v1/debtors/",
        headers={"Authorization": f"Bearer {token}"},
        json={"iin": "040404040404", "full_name": "Idem Conflict", "phone_primary": "+77004445566"},
    )
    debtor_id = rd.json()["id"]

    rc = await client.post(
        "/api/v1/contracts/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "debtor_id": debtor_id,
            "contract_number": f"IDEM-CONFL-{uuid.uuid4().hex[:8]}",
            "original_creditor": "Bank",
            "principal_debt": "50000",
            "total_debt": "50000",
        },
    )
    contract_id = rc.json()["id"]

    idem_key = f"test-conflict-{uuid.uuid4().hex}"

    r1 = await client.post(
        "/api/v1/payments/",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idem_key},
        json={"contract_id": contract_id, "amount": "1000", "payment_date": "2026-04-25", "source": "cash"},
    )
    assert r1.status_code == 201

    # Same key, DIFFERENT amount → 409
    r2 = await client.post(
        "/api/v1/payments/",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idem_key},
        json={"contract_id": contract_id, "amount": "9999", "payment_date": "2026-04-25", "source": "cash"},
    )
    assert r2.status_code == 409, "Should reject same key with different body"


@pytest.mark.asyncio
async def test_no_idempotency_key_works_normally(client, admin_a_token):
    """Without Idempotency-Key header, multiple calls create multiple payments"""
    token, _ = admin_a_token

    rd = await client.post(
        "/api/v1/debtors/",
        headers={"Authorization": f"Bearer {token}"},
        json={"iin": "050505050505", "full_name": "No Idem", "phone_primary": "+77005556677"},
    )
    debtor_id = rd.json()["id"]

    rc = await client.post(
        "/api/v1/contracts/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "debtor_id": debtor_id,
            "contract_number": f"NOIDEM-{uuid.uuid4().hex[:8]}",
            "original_creditor": "Bank",
            "principal_debt": "10000",
            "total_debt": "10000",
        },
    )
    contract_id = rc.json()["id"]
    body = {"contract_id": contract_id, "amount": "100", "payment_date": "2026-04-25", "source": "cash"}

    r1 = await client.post(
        "/api/v1/payments/",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
    )
    r2 = await client.post(
        "/api/v1/payments/",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"], "Without idempotency key, should create separate records"
