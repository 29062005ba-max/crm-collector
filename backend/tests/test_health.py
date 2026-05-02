import pytest


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_metrics(client):
    r = await client.get("/api/v1/metrics")
    assert r.status_code == 200
    body = r.text
    assert "crm_app_info" in body
    assert "crm_companies_total" in body
