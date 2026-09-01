import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.campaign_group import CampaignGroup, campaign_group_leads
from backend.app.models.lead import Lead
from backend.tests.stability.conftest import unique_phone


@pytest.mark.asyncio
async def test_journey_b_c_d_campaign_group_lifecycle_and_delta_updates(client: AsyncClient, whatsapp_spy):
    """
    CRITICAL USER JOURNEYS B, C, D:
    Group Creation -> Lead Memberships -> Delta Addition Deduplication -> Campaign Handoff.
    """
    whatsapp_spy.reset()

    # 1. Seed 5 Leads in DB
    p = [unique_phone() for _ in range(5)]
    lead_ids = []
    async with AsyncSessionLocal() as session:
        for i in range(5):
            lead = Lead(
                name=f"Stabilite Test İşletmesi {i+1}",
                phone=p[i],
                phone_e164=p[i],
                category="Diş Klinikleri",
                city="İstanbul",
                district="Ataşehir",
                is_whatsapp_eligible=True
            )
            session.add(lead)
        await session.commit()
        
        leads_res = await session.execute(select(Lead).where(Lead.phone_e164.in_(p)))
        db_leads = leads_res.scalars().all()
        lead_ids = [l.id for l in db_leads]
        assert len(lead_ids) == 5

    # 2. JOURNEY B: Create Group with first 3 leads
    group_name = f"Ataşehir Diş Grubu {uuid.uuid4().hex[:6]}"
    create_payload = {
        "name": group_name,
        "target_category": "Diş Klinikleri",
        "target_location": "İstanbul, Ataşehir",
        "lead_ids": lead_ids[:3]
    }
    create_res = await client.post("/api/v1/campaign-groups", json=create_payload)
    assert create_res.status_code == 201
    group_data = create_res.json()
    group_id = group_data["id"]
    assert group_data["total_leads_count"] == 3
    assert group_data["whatsapp_eligible_count"] == 3
    assert whatsapp_spy.call_count == 0  # Invariant: Zero Send

    # 3. JOURNEY C: Delta Update (Add all 5 leads: 3 existing + 2 new)
    add_payload = {"lead_ids": lead_ids}
    add_res = await client.post(f"/api/v1/campaign-groups/{group_id}/leads", json=add_payload)
    assert add_res.status_code == 200
    delta_data = add_res.json()
    assert delta_data["added_count"] == 2
    assert delta_data["existing_count"] == 3
    assert delta_data["total_leads_count"] == 5
    assert whatsapp_spy.call_count == 0  # Invariant: Zero Send

    # 4. Invariant: Database junction table has exactly 5 unique records
    async with AsyncSessionLocal() as session:
        memberships = await session.execute(
            select(campaign_group_leads).where(campaign_group_leads.c.group_id == group_id)
        )
        all_m = memberships.fetchall()
        assert len(all_m) == 5
        unique_member_lead_ids = set(m[1] for m in all_m)
        assert len(unique_member_lead_ids) == 5

    # 5. Remove 1 lead from the group
    remove_res = await client.delete(f"/api/v1/campaign-groups/{group_id}/leads/{lead_ids[0]}")
    assert remove_res.status_code == 200
    assert remove_res.json()["total_leads_count"] == 4

    # 6. JOURNEY D: Group -> Campaign Handoff (Create Campaign referencing group_id)
    camp_payload = {
        "name": f"Kampanya from {group_name}",
        "message_template": "Merhaba {name}, grubunuz için özel teklifimiz var.",
        "status": "DRAFT",
        "group_id": group_id,
        "total_leads_target": 4
    }
    camp_res = await client.post("/api/v1/campaigns", json=camp_payload)
    assert camp_res.status_code == 201
    camp_data = camp_res.json()
    assert camp_data["status"] == "DRAFT"
    assert camp_data["group_id"] == group_id
    assert whatsapp_spy.call_count == 0  # Invariant: Zero Send


@pytest.mark.asyncio
async def test_journey_g_group_deletion_strictly_preserves_leads(client: AsyncClient, whatsapp_spy):
    """
    CRITICAL USER JOURNEY G (CORE INVARIANT):
    Deleting a CampaignGroup deletes the group and its memberships, but NEVER deletes Leads.
    """
    whatsapp_spy.reset()

    # 1. Create a lead and a group containing this lead
    phone = unique_phone()
    async with AsyncSessionLocal() as session:
        lead = Lead(
            name="Silinmeyecek Lead",
            phone=phone,
            phone_e164=phone,
            is_whatsapp_eligible=True
        )
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        lead_id = lead.id

    group_res = await client.post("/api/v1/campaign-groups", json={
        "name": f"Geçici Grup {uuid.uuid4().hex[:6]}",
        "lead_ids": [lead_id]
    })
    assert group_res.status_code == 201
    group_id = group_res.json()["id"]

    # 2. Delete the Group
    del_res = await client.delete(f"/api/v1/campaign-groups/{group_id}")
    assert del_res.status_code == 204
    assert whatsapp_spy.call_count == 0

    # 3. Verify Group is deleted
    get_group = await client.get(f"/api/v1/campaign-groups/{group_id}")
    assert get_group.status_code == 404

    # 4. HARD ASSERTION: Lead STILL EXISTS in database and CRM!
    async with AsyncSessionLocal() as session:
        lead_in_db = await session.get(Lead, lead_id)
        assert lead_in_db is not None
        assert lead_in_db.name == "Silinmeyecek Lead"
        assert lead_in_db.phone_e164 == phone

    get_lead_api = await client.get(f"/api/v1/leads/{lead_id}")
    assert get_lead_api.status_code == 200
    assert get_lead_api.json()["id"] == lead_id
