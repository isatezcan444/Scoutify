import asyncio
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.lead import Lead
from backend.app.models.campaign import Campaign
from backend.app.models.campaign_group import CampaignGroup, campaign_group_leads
from backend.tests.stability.conftest import unique_phone


@pytest.mark.asyncio
async def test_concurrent_group_membership_additions_race_condition():
    """
    MEDIUM-01 REGRESSION PROOF:
    Proves that concurrent requests adding the same lead to a group:
    1. ALL succeed with HTTP 200 (zero HTTP 500 errors, zero unhandled IntegrityErrors).
    2. Result in exactly ONE membership entry in the database (no duplicate junction rows).
    3. Return consistent, deterministic response counts.
    """
    phone = unique_phone()
    async with AsyncSessionLocal() as session:
        lead = Lead(name="Eşzamanlı Test Lead", phone=phone, phone_e164=phone, is_whatsapp_eligible=True)
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        lead_id = lead.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        group_res = await ac.post("/api/v1/campaign-groups", json={"name": f"Yarış Testi {uuid.uuid4().hex[:6]}"})
        assert group_res.status_code == 201
        group_id = group_res.json()["id"]

        # Run 3 concurrent requests trying to add the exact same lead_id
        async def add_lead_req():
            return await ac.post(f"/api/v1/campaign-groups/{group_id}/leads", json={"lead_ids": [lead_id]})

        results = await asyncio.gather(add_lead_req(), add_lead_req(), add_lead_req())
        
        # Invariant: Every concurrent request MUST succeed with 200 OK, zero 500 errors
        for r in results:
            assert r.status_code == 200, f"Expected 200 OK, got {r.status_code}: {r.text}"
            data = r.json()
            assert data["group_id"] == group_id
            assert data["total_leads_count"] == 1

        # Across the 3 requests, exactly 1 reported added_count=1, and the others reported existing_count=1
        added_sum = sum(r.json()["added_count"] for r in results)
        assert added_sum == 1, f"Expected exactly 1 added_count across race, got {added_sum}"

    # Invariant: Database junction table strictly enforces uniqueness (strictly 1 membership row)
    async with AsyncSessionLocal() as session:
        memberships = await session.execute(
            select(campaign_group_leads).where(
                campaign_group_leads.c.group_id == group_id,
                campaign_group_leads.c.lead_id == lead_id
            )
        )
        all_rows = memberships.fetchall()
        assert len(all_rows) == 1, f"Expected 1 membership row, found {len(all_rows)}"


@pytest.mark.asyncio
async def test_concurrent_mixed_group_membership_additions():
    """
    Proves concurrent requests with overlapping/mixed lead IDs:
    All succeed with 200 OK, DB integrity is preserved, exactly unique count of rows created.
    """
    async with AsyncSessionLocal() as session:
        leads = []
        for i in range(4):
            p = unique_phone()
            leads.append(Lead(name=f"Karma Lead {i}", phone=p, phone_e164=p, is_whatsapp_eligible=True))
        session.add_all(leads)
        await session.commit()
        for l in leads:
            await session.refresh(l)
        l_ids = [l.id for l in leads]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        group_res = await ac.post("/api/v1/campaign-groups", json={"name": f"Karma Yarış {uuid.uuid4().hex[:6]}"})
        assert group_res.status_code == 201
        group_id = group_res.json()["id"]

        # Request 1 adds [lead_0, lead_1]
        # Request 2 adds [lead_1, lead_2]
        # Request 3 adds [lead_2, lead_3]
        # Request 4 adds [lead_0, lead_1, lead_2, lead_3]
        reqs = [
            ac.post(f"/api/v1/campaign-groups/{group_id}/leads", json={"lead_ids": [l_ids[0], l_ids[1]]}),
            ac.post(f"/api/v1/campaign-groups/{group_id}/leads", json={"lead_ids": [l_ids[1], l_ids[2]]}),
            ac.post(f"/api/v1/campaign-groups/{group_id}/leads", json={"lead_ids": [l_ids[2], l_ids[3]]}),
            ac.post(f"/api/v1/campaign-groups/{group_id}/leads", json={"lead_ids": l_ids}),
        ]
        results = await asyncio.gather(*reqs)

        for r in results:
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
            assert r.json()["total_leads_count"] <= 4

    # Verify Database: Exactly 4 unique memberships in group
    async with AsyncSessionLocal() as session:
        memberships = await session.execute(
            select(campaign_group_leads).where(campaign_group_leads.c.group_id == group_id)
        )
        all_rows = memberships.fetchall()
        assert len(all_rows) == 4



@pytest.mark.asyncio
async def test_concurrent_campaign_deletions_idempotency():
    """
    Proves that simultaneous DELETE requests on the same campaign execute safely:
    first one succeeds (200/204), subsequent ones return 404, zero 500 errors.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        camp_res = await ac.post("/api/v1/campaigns", json={
            "name": f"Eşzamanlı Silme Kampanyası {uuid.uuid4().hex[:6]}",
            "message_template": "Test mesajı",
            "status": "DRAFT"
        })
        assert camp_res.status_code == 201
        camp_id = camp_res.json()["id"]

        async def del_req():
            return await ac.delete(f"/api/v1/campaigns/{camp_id}")

        results = await asyncio.gather(del_req(), del_req())
        status_codes = [r.status_code for r in results]
        assert any(code in (200, 204) for code in status_codes)
        assert all(code in (200, 204, 404) for code in status_codes)
        assert 500 not in status_codes
