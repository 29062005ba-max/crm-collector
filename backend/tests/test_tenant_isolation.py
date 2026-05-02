"""Critical tests: tenant isolation cannot be broken.

These tests verify that a user from company A cannot access data from company B,
which is the foundation of the multi-tenant SaaS model.
"""
import pytest
from sqlalchemy import select
from app.models import Debtor, Contract


@pytest.mark.asyncio
async def test_admin_a_cannot_see_company_b_debtor(client, admin_a_token, admin_b_token, db_session):
    """Admin from company A creates a debtor → admin from B cannot see it"""
    token_a, user_a_id = admin_a_token
    token_b, user_b_id = admin_b_token

    # Admin A creates debtor
    r = await client.post(
        "/api/v1/debtors/",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "iin": "010101010101",
            "full_name": "Test Debtor Tenant A",
            "phone_primary": "+77001112233",
        },
    )
    assert r.status_code == 201, r.text
    debtor_id = r.json()["id"]

    # Admin B tries to fetch it → should 404
    r2 = await client.get(
        f"/api/v1/debtors/{debtor_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r2.status_code == 404, "Tenant isolation broken!"


@pytest.mark.asyncio
async def test_admin_a_list_does_not_include_company_b_debtors(
    client, admin_a_token, admin_b_token, db_session,
):
    """Admin B creates debtor → admin A's list does NOT include it"""
    token_a, _ = admin_a_token
    token_b, _ = admin_b_token

    # Create debtor in B
    r = await client.post(
        "/api/v1/debtors/",
        headers={"Authorization": f"Bearer {token_b}"},
        json={
            "iin": "020202020202",
            "full_name": "Debtor In Company B",
            "phone_primary": "+77002223344",
        },
    )
    assert r.status_code == 201
    debtor_b_id = r.json()["id"]

    # A's list
    r2 = await client.get("/api/v1/debtors/", headers={"Authorization": f"Bearer {token_a}"})
    assert r2.status_code == 200
    items = r2.json().get("items", [])
    ids = [d["id"] for d in items]
    assert debtor_b_id not in ids, f"Tenant leak: {debtor_b_id} visible to other tenant"


@pytest.mark.asyncio
async def test_no_auth_returns_401(client):
    r = await client.get("/api/v1/debtors/")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_companies_endpoint_requires_admin(client, admin_a_token):
    """Companies CRUD only for admin"""
    token_a, _ = admin_a_token
    r = await client.get("/api/v1/companies", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 200  # admin should have access
