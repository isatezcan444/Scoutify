import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.lead import Lead, LeadStatus
from backend.app.models.blacklist import Blacklist
from backend.app.services.lead_ingest_service import LeadIngestService
from backend.tests.stability.conftest import unique_phone


@pytest.mark.asyncio
async def test_journey_a_discovery_to_crm_lifecycle(client: AsyncClient):
    """
    CRITICAL USER JOURNEY A:
    Discovery -> Lead Ingest -> Normalization -> Deduplication -> CRM Presentation -> Mutations.
    """
    phone1 = unique_phone()
    phone2 = unique_phone()
    place_id_1 = f"place_test_{uuid.uuid4().hex[:12]}"
    place_id_2 = f"place_test_{uuid.uuid4().hex[:12]}"

    suffix = uuid.uuid4().hex[:6]
    name1 = f"Ataşehir Özel Diş Kliniği {suffix}"
    name2 = f"Ataşehir Sabit Hatlı Merkez {suffix}"
    name3 = f"Ataşehir Numarasız Şube {suffix}"

    raw_candidates = [
        {
            "name": name1,
            "phone": phone1,
            "place_id": place_id_1,
            "category": "Diş Hekimi",
            "city": "İstanbul",
            "district": "Ataşehir",
            "address": "Atatürk Mah. No:1, Ataşehir/İstanbul",
            "rating": 4.8,
            "reviews_count": 55,
        },
        {
            "name": name2,
            "phone": phone2,
            "place_id": place_id_2,
            "category": "Sağlık Merkezi",
            "city": "İstanbul",
            "district": "Ataşehir",
            "address": "Barbaros Mah. No:2, Ataşehir/İstanbul",
        },
        {
            "name": name3,
            "phone": "",  # No phone -> phone_e164 = None, is_whatsapp_eligible = False
            "place_id": f"place_test_{uuid.uuid4().hex[:12]}",
            "category": "Diş Hekimi",
            "city": "İstanbul",
            "district": "Ataşehir",
        }
    ]

    # 1. Ingest Raw Candidates
    async with AsyncSessionLocal() as session:
        leads_1, new_1, updated_1 = await LeadIngestService.ingest_leads(
            db=session,
            raw_leads=raw_candidates,
            search_keyword="Diş Klinikleri",
            search_location="İstanbul, Ataşehir"
        )
        await session.commit()
        assert new_1 == 3
        assert updated_1 == 0

    # 2. Verify Deduplication on Rescan (Re-ingesting same place_ids)
    async with AsyncSessionLocal() as session:
        leads_2, new_2, updated_2 = await LeadIngestService.ingest_leads(
            db=session,
            raw_leads=raw_candidates,
            search_keyword="Diş Klinikleri",
            search_location="İstanbul, Ataşehir"
        )
        await session.commit()
        assert new_2 == 0
        assert updated_2 == 3  # All detected as existing and merged/updated

    # 3. Verify CRM Presentation via REST API
    res = await client.get("/api/v1/leads", params={"search": name1})
    assert res.status_code == 200
    crm_data = res.json()
    assert crm_data["total"] >= 1
    found_lead = next((l for l in crm_data["items"] if l["name"] == name1), None)
    assert found_lead is not None
    assert found_lead["name"] == name1
    assert found_lead["is_whatsapp_eligible"] is True
    lead_id = found_lead["id"]

    # 4. Verify Landline lead eligibility in CRM
    res_landline = await client.get("/api/v1/leads", params={"search": name2})
    assert res_landline.status_code == 200
    landline_items = res_landline.json()["items"]
    assert len(landline_items) >= 1
    assert landline_items[0]["is_whatsapp_eligible"] is False

    # 5. Mutate Lead Details (PATCH)
    patch_res = await client.patch(f"/api/v1/leads/{lead_id}", json={
        "status": "INTERESTED",
        "notes": "Harness audit note: validated successfully"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "INTERESTED"
    assert patch_res.json()["notes"] == "Harness audit note: validated successfully"

    # 6. Delete Lead and verify cleanup
    del_res = await client.delete(f"/api/v1/leads/{lead_id}")
    assert del_res.status_code in (200, 204)

    # 7. Verify Lead is removed from CRM
    verify_del = await client.get(f"/api/v1/leads/{lead_id}")
    assert verify_del.status_code == 404
