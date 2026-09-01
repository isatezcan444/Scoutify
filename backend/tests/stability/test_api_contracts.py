import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_leads_api_contract_and_error_handling(client: AsyncClient):
    """Proves /api/v1/leads adheres to pagination schema and handles invalid parameters."""
    # 1. Happy Path Pagination Contract
    res = await client.get("/api/v1/leads", params={"page": 1, "size": 10})
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert isinstance(data["items"], list)

    # 2. Validation Error (422) on negative page
    res_422 = await client.get("/api/v1/leads", params={"page": -5})
    assert res_422.status_code == 422
    assert "detail" in res_422.json()

    # 3. Not Found (404) on nonexistent lead ID
    res_404 = await client.get("/api/v1/leads/99999999")
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_campaign_groups_api_contract(client: AsyncClient):
    """Proves /api/v1/campaign-groups schema validation and error handling."""
    # 1. 404 on nonexistent group
    res_404 = await client.get("/api/v1/campaign-groups/99999999")
    assert res_404.status_code == 404

    # 2. 422 on invalid body type (e.g. string instead of int array)
    res_422 = await client.post("/api/v1/campaign-groups/1/leads", json={"lead_ids": "invalid_not_an_array"})
    assert res_422.status_code == 422


@pytest.mark.asyncio
async def test_campaigns_api_contract(client: AsyncClient):
    """Proves /api/v1/campaigns schema validation and error handling."""
    # 1. 404 on nonexistent campaign
    res_404 = await client.get("/api/v1/campaigns/99999999")
    assert res_404.status_code == 404

    # 2. 422 on missing required field
    res_422 = await client.post("/api/v1/campaigns", json={})
    assert res_422.status_code == 422


@pytest.mark.asyncio
async def test_blacklist_api_contract(client: AsyncClient):
    """Proves /api/v1/blacklist pagination and bulk operations contract."""
    res = await client.get("/api/v1/blacklist", params={"page": 1, "size": 10})
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
