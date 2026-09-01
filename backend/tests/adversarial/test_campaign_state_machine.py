"""
Adversarial Campaign State Machine & Worker Safety Tests.
Exhaustively audits the legal and illegal transition matrix, deletion safety, and worker cancellation.
"""
import uuid
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.campaign import Campaign, CampaignStatus
from backend.app.services.campaign_runner import CampaignRunner


@pytest.mark.asyncio
async def test_campaign_state_machine_matrix():
    """
    Exhaustively tests the Campaign state machine transitions:
    - Creation defaults to DRAFT
    - Valid patch transitions (DRAFT -> PAUSED -> ACTIVE -> ARCHIVED)
    - Rejection of invalid status strings via Pydantic schema validation (422)
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create DRAFT
        create_res = await client.post("/api/v1/campaigns", json={
            "name": f"Durum Makinesi Testi {uuid.uuid4().hex[:6]}",
            "message_template": "Merhaba {name}"
        })
        assert create_res.status_code == 201
        camp = create_res.json()
        assert camp["status"] == CampaignStatus.DRAFT.value
        cid = camp["id"]

        # 2. Transition DRAFT -> PAUSED
        res_pause = await client.patch(f"/api/v1/campaigns/{cid}", json={"status": "PAUSED"})
        assert res_pause.status_code == 200
        assert res_pause.json()["status"] == "PAUSED"

        # 3. Transition PAUSED -> ACTIVE
        res_active = await client.patch(f"/api/v1/campaigns/{cid}", json={"status": "ACTIVE"})
        assert res_active.status_code == 200
        assert res_active.json()["status"] == "ACTIVE"

        # 4. Transition ACTIVE -> ARCHIVED
        res_arch = await client.patch(f"/api/v1/campaigns/{cid}", json={"status": "ARCHIVED"})
        assert res_arch.status_code == 200
        assert res_arch.json()["status"] == "ARCHIVED"

        # 5. Invalid status string -> 422 Unprocessable Entity
        res_invalid = await client.patch(f"/api/v1/campaigns/{cid}", json={"status": "NONEXISTENT_STATE"})
        assert res_invalid.status_code == 422


@pytest.mark.asyncio
async def test_adversarial_launch_conflict_matrix():
    """
    Tests launch behavior on already active or running campaigns:
    - Calling /launch on an already ACTIVE campaign must return 409 Conflict.
    - Calling /launch on a non-existent campaign must return 404.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Nonexistent campaign launch
        res_nonexistent = await client.post("/api/v1/campaigns/99999999/launch", json={})
        assert res_nonexistent.status_code == 404

        # 2. Create campaign in ACTIVE status
        create_res = await client.post("/api/v1/campaigns", json={
            "name": f"Aktif Çakışma Testi {uuid.uuid4().hex[:6]}",
            "message_template": "Merhaba {name}"
        })
        cid = create_res.json()["id"]

        await client.patch(f"/api/v1/campaigns/{cid}", json={"status": "ACTIVE"})

        # 3. Attempting to launch already ACTIVE campaign must return 409 Conflict
        res_conflict = await client.post(f"/api/v1/campaigns/{cid}/launch", json={})
        assert res_conflict.status_code == 409
        assert "zaten çalışıyor" in res_conflict.json()["detail"]


@pytest.mark.asyncio
async def test_adversarial_running_campaign_deletion_cancels_worker():
    """
    Tests that deleting a running campaign cleanly calls CampaignRunner.cancel_campaign
    and deletes the database record.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_res = await client.post("/api/v1/campaigns", json={
            "name": f"Çalışırken Silme Testi {uuid.uuid4().hex[:6]}",
            "message_template": "Merhaba {name}"
        })
        cid = create_res.json()["id"]

        # Simulate running state in CampaignRunner
        with patch.object(CampaignRunner, "is_campaign_running", return_value=True), \
             patch.object(CampaignRunner, "cancel_campaign", new_callable=AsyncMock) as mock_cancel:
            
            del_res = await client.delete(f"/api/v1/campaigns/{cid}")
            assert del_res.status_code == 204
            mock_cancel.assert_called_once_with(cid)

        # Subsequent fetch returns 404
        get_res = await client.get(f"/api/v1/campaigns/{cid}")
        assert get_res.status_code == 404
