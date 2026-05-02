"""Tariff and company management tests"""
import pytest
import uuid


@pytest.mark.asyncio
async def test_tariff_limit_blocks_creation(client, admin_a_token, db_session):
    """When max_debtors reached, POST /debtors returns 403"""
    from app.models import Company

    # Reduce the limit for company A to force a hit
    company = await db_session.get(Company, 1)
    original_limit = company.max_debtors
    company.max_debtors = 1  # very low
    await db_session.commit()

    token, _ = admin_a_token

    # Create 1st (should succeed)
    r1 = await client.post(
        "/api/v1/debtors/",
        headers={"Authorization": f"Bearer {token}"},
        json={"iin": f"33{uuid.uuid4().hex[:10]}", "full_name": "Limit Test 1", "phone_primary": "+77000000007"},
    )
    # If existing debtors > 1 already, the first one will also fail → that's fine
    # We just want to verify that AT SOME POINT 403 is returned
    r2 = await client.post(
        "/api/v1/debtors/",
        headers={"Authorization": f"Bearer {token}"},
        json={"iin": f"22{uuid.uuid4().hex[:10]}", "full_name": "Limit Test 2", "phone_primary": "+77000000008"},
    )

    # At least one of them should be 403
    assert (r1.status_code == 403 or r2.status_code == 403), \
        f"Expected tariff limit error, got {r1.status_code} and {r2.status_code}"

    # Restore
    company.max_debtors = original_limit
    await db_session.commit()


@pytest.mark.asyncio
async def test_company_me_endpoint(client, admin_a_token):
    token, _ = admin_a_token
    r = await client.get("/api/v1/companies/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "company" in data
    assert "users_count" in data
    assert "debtors_count" in data
    assert "users_usage_pct" in data


@pytest.mark.asyncio
async def test_tariffs_list_public(client, admin_a_token):
    token, _ = admin_a_token
    r = await client.get("/api/v1/companies/tariffs/list", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "basic" in data
    assert "pro" in data
    assert "enterprise" in data
