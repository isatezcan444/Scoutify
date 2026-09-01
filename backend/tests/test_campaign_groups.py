import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.lead import Lead
from backend.app.models.campaign_group import CampaignGroup


def _rnd_phone():
    return f"+90555{uuid.uuid4().int % 100000000:08d}"


@pytest.mark.asyncio
async def test_create_campaign_group_with_auto_name():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "target_category": "Diş Klinikleri",
            "target_location": "İstanbul, Ataşehir",
        }
        res = await ac.post("/api/v1/campaign-groups", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "İstanbul, Ataşehir Diş Klinikleri"
        assert data["target_category"] == "Diş Klinikleri"
        assert data["target_location"] == "İstanbul, Ataşehir"
        assert data["total_leads_count"] == 0
        assert data["whatsapp_eligible_count"] == 0


@pytest.mark.asyncio
async def test_create_campaign_group_with_initial_leads():
    p1, p2 = _rnd_phone(), _rnd_phone()
    async with AsyncSessionLocal() as db:
        l1 = Lead(name="Ataşehir Diş Polikliniği 1", phone=p1, phone_e164=p1, is_whatsapp_eligible=True)
        l2 = Lead(name="Ataşehir Diş Polikliniği 2", phone=p2, phone_e164=p2, is_whatsapp_eligible=False)
        db.add_all([l1, l2])
        await db.commit()
        await db.refresh(l1)
        await db.refresh(l2)
        lead_ids = [l1.id, l2.id]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "name": f"Ataşehir Diş Klinikleri {uuid.uuid4().hex[:4]}",
            "target_category": "Diş Klinikleri",
            "target_location": "Ataşehir",
            "lead_ids": lead_ids,
        }
        res = await ac.post("/api/v1/campaign-groups", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["total_leads_count"] == 2
        assert data["whatsapp_eligible_count"] == 1


@pytest.mark.asyncio
async def test_list_and_get_campaign_group_detail():
    p1 = _rnd_phone()
    async with AsyncSessionLocal() as db:
        l1 = Lead(name="Kadıköy Güzellik 1", phone=p1, phone_e164=p1, is_whatsapp_eligible=True)
        db.add(l1)
        await db.commit()
        await db.refresh(l1)
        lead_id = l1.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        grp_name = f"Kadıköy Güzellik {uuid.uuid4().hex[:4]}"
        create_res = await ac.post("/api/v1/campaign-groups", json={
            "name": grp_name,
            "lead_ids": [lead_id],
        })
        group_id = create_res.json()["id"]

        # List groups
        list_res = await ac.get("/api/v1/campaign-groups")
        assert list_res.status_code == 200
        groups = list_res.json()
        assert len(groups) >= 1
        matched = next((g for g in groups if g["id"] == group_id), None)
        assert matched is not None
        assert matched["total_leads_count"] == 1
        assert matched["whatsapp_eligible_count"] == 1

        # Get Detail
        detail_res = await ac.get(f"/api/v1/campaign-groups/{group_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["name"] == grp_name
        assert len(detail["leads"]) == 1
        assert detail["leads"][0]["id"] == lead_id


@pytest.mark.asyncio
async def test_add_leads_to_group_deduplication():
    p1, p2, p3 = _rnd_phone(), _rnd_phone(), _rnd_phone()
    async with AsyncSessionLocal() as db:
        l1 = Lead(name="Dedupe Lead 1", phone=p1, phone_e164=p1, is_whatsapp_eligible=True)
        l2 = Lead(name="Dedupe Lead 2", phone=p2, phone_e164=p2, is_whatsapp_eligible=True)
        l3 = Lead(name="Dedupe Lead 3", phone=p3, phone_e164=p3, is_whatsapp_eligible=True)
        db.add_all([l1, l2, l3])
        await db.commit()
        await db.refresh(l1)
        await db.refresh(l2)
        await db.refresh(l3)
        l1_id, l2_id, l3_id = l1.id, l2.id, l3.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Create empty group
        create_res = await ac.post("/api/v1/campaign-groups", json={"name": f"Dedupe {uuid.uuid4().hex[:4]}"})
        group_id = create_res.json()["id"]

        # 2. Add first 2 leads
        first_add_res = await ac.post(
            f"/api/v1/campaign-groups/{group_id}/leads",
            json={"lead_ids": [l1_id, l2_id]}
        )
        assert first_add_res.status_code == 200
        first_data = first_add_res.json()
        assert first_data["added_count"] == 2
        assert first_data["existing_count"] == 0
        assert first_data["total_leads_count"] == 2

        # 3. Add all 3 leads (l1, l2 already in group, l3 is new)
        second_add_res = await ac.post(
            f"/api/v1/campaign-groups/{group_id}/leads",
            json={"lead_ids": [l1_id, l2_id, l3_id]}
        )
        assert second_add_res.status_code == 200
        second_data = second_add_res.json()
        assert second_data["added_count"] == 1  # only l3 added
        assert second_data["existing_count"] == 2  # l1 and l2 skipped
        assert second_data["total_leads_count"] == 3


@pytest.mark.asyncio
async def test_remove_lead_from_group():
    p1, p2 = _rnd_phone(), _rnd_phone()
    async with AsyncSessionLocal() as db:
        l1 = Lead(name="Removal Lead 1", phone=p1, phone_e164=p1, is_whatsapp_eligible=True)
        l2 = Lead(name="Removal Lead 2", phone=p2, phone_e164=p2, is_whatsapp_eligible=True)
        db.add_all([l1, l2])
        await db.commit()
        await db.refresh(l1)
        await db.refresh(l2)
        l1_id, l2_id = l1.id, l2.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_res = await ac.post(
            "/api/v1/campaign-groups",
            json={"name": f"Removal {uuid.uuid4().hex[:4]}", "lead_ids": [l1_id, l2_id]}
        )
        group_id = create_res.json()["id"]

        # Remove 1 lead
        del_res = await ac.delete(f"/api/v1/campaign-groups/{group_id}/leads/{l1_id}")
        assert del_res.status_code == 200
        del_data = del_res.json()
        assert del_data["total_leads_count"] == 1

        # Verify Detail has only 1 lead
        detail_res = await ac.get(f"/api/v1/campaign-groups/{group_id}")
        detail = detail_res.json()
        assert len(detail["leads"]) == 1
        assert detail["leads"][0]["id"] == l2_id


@pytest.mark.asyncio
async def test_delete_campaign_group_preserves_leads():
    p1 = _rnd_phone()
    async with AsyncSessionLocal() as db:
        l1 = Lead(name="Preserved Lead", phone=p1, phone_e164=p1, is_whatsapp_eligible=True)
        db.add(l1)
        await db.commit()
        await db.refresh(l1)
        l1_id = l1.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        create_res = await ac.post(
            "/api/v1/campaign-groups",
            json={"name": f"To Delete {uuid.uuid4().hex[:4]}", "lead_ids": [l1_id]}
        )
        group_id = create_res.json()["id"]

        # Delete group
        delete_res = await ac.delete(f"/api/v1/campaign-groups/{group_id}")
        assert delete_res.status_code == 204

        # Group should be 404
        get_res = await ac.get(f"/api/v1/campaign-groups/{group_id}")
        assert get_res.status_code == 404

    # BUT Lead must STILL exist in database!
    async with AsyncSessionLocal() as db:
        lead_in_db = await db.get(Lead, l1_id)
        assert lead_in_db is not None
        assert lead_in_db.name == "Preserved Lead"


@pytest.mark.asyncio
async def test_bulk_delete_campaign_groups_preserves_leads():
    p1 = _rnd_phone()
    async with AsyncSessionLocal() as db:
        l1 = Lead(name="Bulk Preserved Lead", phone=p1, phone_e164=p1, is_whatsapp_eligible=True)
        db.add(l1)
        await db.commit()
        await db.refresh(l1)
        l1_id = l1.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res1 = await ac.post("/api/v1/campaign-groups", json={"name": f"Bulk Grp 1 {uuid.uuid4().hex[:4]}", "lead_ids": [l1_id]})
        res2 = await ac.post("/api/v1/campaign-groups", json={"name": f"Bulk Grp 2 {uuid.uuid4().hex[:4]}", "lead_ids": [l1_id]})
        g1_id = res1.json()["id"]
        g2_id = res2.json()["id"]

        bulk_del_res = await ac.post("/api/v1/campaign-groups/bulk-delete", json={"group_ids": [g1_id, g2_id]})
        assert bulk_del_res.status_code == 200
        assert bulk_del_res.json()["deleted_count"] == 2

        # Verify groups are gone
        assert (await ac.get(f"/api/v1/campaign-groups/{g1_id}")).status_code == 404
        assert (await ac.get(f"/api/v1/campaign-groups/{g2_id}")).status_code == 404

    # Verify lead is intact
    async with AsyncSessionLocal() as db:
        assert (await db.get(Lead, l1_id)) is not None


@pytest.mark.asyncio
async def test_bulk_delete_campaigns():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        c1 = await ac.post("/api/v1/campaigns", json={"name": f"Bulk Camp 1 {uuid.uuid4().hex[:4]}", "message_template": "Hello {name}"})
        c2 = await ac.post("/api/v1/campaigns", json={"name": f"Bulk Camp 2 {uuid.uuid4().hex[:4]}", "message_template": "Hello {name}"})
        c1_id = c1.json()["id"]
        c2_id = c2.json()["id"]

        bulk_del = await ac.post("/api/v1/campaigns/bulk-delete", json={"campaign_ids": [c1_id, c2_id]})
        assert bulk_del.status_code == 200
        assert bulk_del.json()["deleted_count"] == 2

        assert (await ac.get(f"/api/v1/campaigns/{c1_id}")).status_code == 404
        assert (await ac.get(f"/api/v1/campaigns/{c2_id}")).status_code == 404

