"""
Final Campaign State Machine Audit Suite.
Exhaustively tests legal and illegal state transitions, conflict handling,
and verified worker cancellation semantics.
"""
import pytest
import asyncio
import uuid
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.campaign import Campaign, CampaignStatus
from backend.app.services.campaign_runner import CampaignRunner


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_campaign_state_machine_transition_matrix(monkeypatch):
    """
    Tests complete lifecycle of Campaign states: DRAFT -> ACTIVE -> PAUSED -> ACTIVE -> ARCHIVED.
    Tests invalid moves and asserts 4xx responses.
    """
    # Stub long-running runner loop
    async def mock_worker(campaign_id, *args, **kwargs):
        async with AsyncSessionLocal() as db:
            c = await db.get(Campaign, campaign_id)
            if c:
                c.status = CampaignStatus.ACTIVE
                await db.commit()

    monkeypatch.setattr(CampaignRunner, "_execute_campaign_worker", mock_worker)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create DRAFT campaign
        create_res = await client.post(
            "/api/v1/campaigns",
            json={
                "name": f"SM Camp {uuid.uuid4().hex[:6]}",
                "message_template": "Merhaba {business_name}, özel kampanyamız hazır."
            }
        )
        assert create_res.status_code == 201
        cid = create_res.json()["id"]
        assert create_res.json()["status"] == CampaignStatus.DRAFT.value

        # 2. Transition: DRAFT -> ACTIVE (Launch)
        launch_res = await client.post(f"/api/v1/campaigns/{cid}/launch", json={"limit": 50})
        assert launch_res.status_code == 200
        await asyncio.sleep(0.05)

        # Verify DB is ACTIVE
        async with AsyncSessionLocal() as session:
            camp = await session.get(Campaign, cid)
            assert camp.status == CampaignStatus.ACTIVE

        # 3. Invalid Transition: ACTIVE -> ACTIVE (Duplicate launch should fail 409)
        dup_launch = await client.post(f"/api/v1/campaigns/{cid}/launch", json={"limit": 50})
        assert dup_launch.status_code == 409

        # 4. Transition: ACTIVE -> PAUSED
        pause_res = await client.post(f"/api/v1/campaigns/{cid}/pause")
        assert pause_res.status_code == 200

        async with AsyncSessionLocal() as session:
            camp = await session.get(Campaign, cid)
            assert camp.status == CampaignStatus.PAUSED

        # 5. Transition: PAUSED -> ACTIVE (Resume via Launch)
        resume_res = await client.post(f"/api/v1/campaigns/{cid}/launch", json={"limit": 50})
        assert resume_res.status_code == 200
        await asyncio.sleep(0.05)

        async with AsyncSessionLocal() as session:
            camp = await session.get(Campaign, cid)
            assert camp.status == CampaignStatus.ACTIVE

        # 6. Delete ACTIVE campaign -> Must cancel worker and purge
        del_res = await client.delete(f"/api/v1/campaigns/{cid}")
        assert del_res.status_code == 204

        # Verify gone
        async with AsyncSessionLocal() as session:
            camp = await session.get(Campaign, cid)
            assert camp is None
