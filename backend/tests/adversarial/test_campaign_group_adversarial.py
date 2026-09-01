"""
Adversarial Campaign Group & Lead Preservation Tests.
Validates membership integrity, junction uniqueness, lead retention on group delete, and handoff safety.
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func

from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.lead import Lead
from backend.app.models.campaign_group import CampaignGroup, campaign_group_leads
from backend.tests.adversarial.conftest import unique_phone, WhatsAppCallTracker


@pytest.mark.asyncio
async def test_adversarial_group_membership_duplicate_filtering():
    """
    Tests that passing identical lead IDs repeatedly in the payload or calling sequentially:
    - Automatically deduplicates inputs
    - Strictly creates only 1 row in campaign_group_leads
    - Accurately counts added_count vs existing_count
    """
    phone = unique_phone()
    async with AsyncSessionLocal() as session:
        lead = Lead(name="Deduplicate Group Lead", phone=phone, phone_e164=phone, is_whatsapp_eligible=True)
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        lid = lead.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create Group
        g_res = await client.post("/api/v1/campaign-groups", json={"name": f"Tekrarlı Üye Grubu {uuid.uuid4().hex[:6]}"})
        assert g_res.status_code == 201
        gid = g_res.json()["id"]

        # 2. Add array with 10 duplicate lead IDs
        add_res1 = await client.post(f"/api/v1/campaign-groups/{gid}/leads", json={"lead_ids": [lid] * 10})
        assert add_res1.status_code == 200
        assert add_res1.json()["added_count"] == 1
        assert add_res1.json()["total_leads_count"] == 1

        # 3. Add same lead ID again sequentially 5 times
        for _ in range(5):
            add_res2 = await client.post(f"/api/v1/campaign-groups/{gid}/leads", json={"lead_ids": [lid]})
            assert add_res2.status_code == 200
            assert add_res2.json()["added_count"] == 0
            assert add_res2.json()["existing_count"] == 1
            assert add_res2.json()["total_leads_count"] == 1

    # 4. Verify Database has strictly 1 junction row
    async with AsyncSessionLocal() as session:
        stmt = select(func.count()).select_from(campaign_group_leads).where(
            campaign_group_leads.c.group_id == gid,
            campaign_group_leads.c.lead_id == lid
        )
        cnt = (await session.execute(stmt)).scalar()
        assert cnt == 1


@pytest.mark.asyncio
async def test_adversarial_lead_preservation_on_group_delete():
    """
    CRITICAL INVARIANT PROOF:
    Deleting a CampaignGroup or removing a lead from a group MUST NEVER delete the Lead entity.
    """
    phone1 = unique_phone()
    phone2 = unique_phone()
    async with AsyncSessionLocal() as session:
        l1 = Lead(name="Korumalı Lead 1", phone=phone1, phone_e164=phone1, is_whatsapp_eligible=True)
        l2 = Lead(name="Korumalı Lead 2", phone=phone2, phone_e164=phone2, is_whatsapp_eligible=True)
        session.add_all([l1, l2])
        await session.commit()
        await session.refresh(l1)
        await session.refresh(l2)
        l1_id, l2_id = l1.id, l2.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create group with both leads
        g_res = await client.post("/api/v1/campaign-groups", json={
            "name": f"Korumalı Grup {uuid.uuid4().hex[:6]}",
            "lead_ids": [l1_id, l2_id]
        })
        gid = g_res.json()["id"]

        # 1. Remove l1 from group via DELETE /groups/{id}/leads/{lead_id}
        rem_res = await client.delete(f"/api/v1/campaign-groups/{gid}/leads/{l1_id}")
        assert rem_res.status_code == 200

        # Verify l1 still exists in leads CRM
        l1_fetch = await client.get(f"/api/v1/leads/{l1_id}")
        assert l1_fetch.status_code == 200
        assert l1_fetch.json()["name"] == "Korumalı Lead 1"

        # 2. Delete the entire group
        del_group = await client.delete(f"/api/v1/campaign-groups/{gid}")
        assert del_group.status_code == 204

        # Group is gone
        assert (await client.get(f"/api/v1/campaign-groups/{gid}")).status_code == 404

        # BOTH leads still 100% exist in CRM
        assert (await client.get(f"/api/v1/leads/{l1_id}")).status_code == 200
        assert (await client.get(f"/api/v1/leads/{l2_id}")).status_code == 200


@pytest.mark.asyncio
async def test_adversarial_group_to_campaign_handoff_zero_send(whatsapp_spy: WhatsAppCallTracker):
    """
    ZERO-SEND INVARIANT PROOF:
    Creating a campaign linked to a group_id MUST NOT invoke any WhatsApp dispatcher.
    """
    phone = unique_phone()
    async with AsyncSessionLocal() as session:
        lead = Lead(name="Handoff Lead", phone=phone, phone_e164=phone, is_whatsapp_eligible=True)
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        lid = lead.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        g_res = await client.post("/api/v1/campaign-groups", json={
            "name": f"Handoff Grubu {uuid.uuid4().hex[:6]}",
            "lead_ids": [lid]
        })
        gid = g_res.json()["id"]

        # Create Campaign referencing group_id
        camp_res = await client.post("/api/v1/campaigns", json={
            "name": f"Handoff Kampanyası {uuid.uuid4().hex[:6]}",
            "message_template": "Merhaba {name}",
            "group_id": gid
        })
        assert camp_res.status_code == 201

        # Strict assertion on WhatsApp dispatcher invocation
        assert whatsapp_spy.call_count == 0, f"Zero send invariant violated: {whatsapp_spy.call_count} calls recorded"
