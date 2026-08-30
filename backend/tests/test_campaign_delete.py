import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.services.campaign_runner import CampaignRunner


@pytest.mark.asyncio
async def test_delete_existing_campaign_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create a campaign
        create_res = await ac.post("/api/v1/campaigns", json={
            "name": "Diş Klinikleri Q3 Tanıtım",
            "message_template": "Merhaba {name}, {district} kliniğinize özel...",
            "min_delay_seconds": 45,
            "max_delay_seconds": 90,
            "typing_delay_seconds": 4,
            "working_hours_enabled": True
        })
        assert create_res.status_code == 201
        created = create_res.json()
        campaign_id = created["id"]

        # 2. Verify campaign exists
        get_res = await ac.get(f"/api/v1/campaigns/{campaign_id}")
        assert get_res.status_code == 200

        # 3. Call DELETE endpoint
        del_res = await ac.delete(f"/api/v1/campaigns/{campaign_id}")
        assert del_res.status_code == 204

        # 4. Verify it no longer exists (404)
        get_after_res = await ac.get(f"/api/v1/campaigns/{campaign_id}")
        assert get_after_res.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_campaign_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.delete("/api/v1/campaigns/999999")
        assert res.status_code == 404
        data = res.json()
        assert "bulunamadı" in data.get("detail", "").lower() or "not found" in data.get("detail", "").lower()


@pytest.mark.asyncio
async def test_delete_campaign_cancels_running_worker(monkeypatch):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create a campaign
        create_res = await ac.post("/api/v1/campaigns", json={
            "name": "Active Dispatch Campaign",
            "message_template": "Hello {name}",
            "min_delay_seconds": 30,
            "max_delay_seconds": 60,
            "typing_delay_seconds": 3,
            "working_hours_enabled": True
        })
        assert create_res.status_code == 201
        campaign_id = create_res.json()["id"]

        # 2. Mock CampaignRunner to simulate running state and track cancellation
        cancelled_ids = []

        def mock_is_running(cid):
            return cid == campaign_id

        async def mock_cancel(cid):
            cancelled_ids.append(cid)

        monkeypatch.setattr(CampaignRunner, "is_campaign_running", mock_is_running)
        monkeypatch.setattr(CampaignRunner, "cancel_campaign", mock_cancel)

        # 3. Call DELETE
        res = await ac.delete(f"/api/v1/campaigns/{campaign_id}")
        assert res.status_code == 204

        # 4. Verify cancel was called and record is deleted
        assert campaign_id in cancelled_ids

        get_res = await ac.get(f"/api/v1/campaigns/{campaign_id}")
        assert get_res.status_code == 404

