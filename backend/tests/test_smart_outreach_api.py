"""
API Tests for Smart Outreach & Category Confirmation Endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.mark.asyncio
async def test_recommend_categories_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/smart-outreach/recommend-categories", json={
            "offer_title": "Vito VIP Transfer Hizmeti",
            "offer_description": "Havalimanı transferi",
            "business_goal": "DISCOVERY"
        })

    assert response.status_code == 200
    data = response.json()
    assert data["offer_title"] == "Vito VIP Transfer Hizmeti"
    assert len(data["discovered_categories"]) >= 3
    assert any(c["category_id"] == "hotels" for c in data["discovered_categories"])


@pytest.mark.asyncio
async def test_match_leads_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/smart-outreach/match-leads", json={
            "offer_title": "Dental Sarf Malzemeleri",
            "business_goal": "DISCOVERY",
            "min_fit_score": 10
        })

    assert response.status_code == 200
    data = response.json()
    assert "total_evaluated" in data
    assert "high_fit_count" in data
    assert "leads" in data
