"""
Unit & Integration Tests for Targeted Discovery Pipeline (Phase 3).
"""
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.blacklist import ScraperJob, ScraperJobStatus
from backend.app.models.lead import Lead, LeadStatus
from backend.app.services.lead_ingest_service import LeadIngestService


@pytest.mark.asyncio
async def test_targeted_discovery_endpoint_approved_only():
    """
    Verifies that start-targeted-discovery only creates jobs for approved & user-added categories.
    """
    transport = ASGITransport(app=app)
    with patch("backend.app.api.v1.endpoints.smart_outreach.run_scraper_task") as mock_task:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/v1/smart-outreach/start-targeted-discovery", json={
                "offer_title": "Kurumsal yazılım çözümü",
                "offer_description": "İş süreçlerini dijitalleştiren yazılım",
                "business_goal": "DISCOVERY",
                "city": "Ankara",
                "districts": ["Çankaya"],
                "approved_target_categories": ["Güzellik Merkezleri", "Perakende"],
                "user_added_categories": ["Mimarlık Ofisleri"]
            })

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert data["approved_categories_count"] == 3
    assert len(data["job_ids"]) == 3

    # Check ScraperJob records in database
    async with AsyncSessionLocal() as db:
        for job_id in data["job_ids"]:
            job = await db.get(ScraperJob, job_id)
            assert job is not None
            assert job.city == "Ankara"
            assert "Çankaya" in (job.districts_json or [])
            assert job.keyword in {"Güzellik Merkezleri", "Perakende", "Mimarlık Ofisleri"}


@pytest.mark.asyncio
async def test_targeted_discovery_empty_categories_rejected():
    """
    Verifies that calling discovery with 0 approved categories fails with 400.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/smart-outreach/start-targeted-discovery", json={
            "offer_title": "Kurumsal yazılım çözümü",
            "city": "Ankara",
            "approved_target_categories": [],
            "user_added_categories": []
        })

    assert response.status_code == 400
    assert "onaylanmış hedef kategori" in response.json()["detail"]


@pytest.mark.asyncio
async def test_discovery_deduplication():
    """
    Verifies that duplicate raw leads from multiple queries are merged cleanly by LeadIngestService.
    """
    import uuid
    import random
    uid = uuid.uuid4().hex[:6]
    rand_digits = f"{random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}"
    phone_num = f"0533 {rand_digits}"
    place_id = f"test_place_unique_{uid}"

    async with AsyncSessionLocal() as db:
        raw_leads_1 = [
            {
                "place_id": place_id,
                "name": f"Örnek Mimarlık {uid} A.Ş.",
                "phone": phone_num,
                "city": "Ankara",
                "district": "Çankaya",
                "address": "Çankaya, Ankara",
                "category": "Mimarlık Ofisleri"
            }
        ]

        all_1, new_1, upd_1 = await LeadIngestService.ingest_leads(
            db=db,
            raw_leads=raw_leads_1,
            source="GOOGLE_MAPS",
            search_keyword="Mimarlık Ofisleri",
            search_location="Ankara Çankaya"
        )
        assert new_1 == 1

        # Second ingestion with same place_id from an expanded query
        raw_leads_2 = [
            {
                "place_id": place_id,
                "name": f"Örnek Mimarlık {uid} A.Ş.",
                "phone": phone_num,
                "city": "Ankara",
                "district": "Çankaya",
                "address": "Çankaya, Ankara",
                "category": "Mimarlık Bürosu"
            }
        ]

        all_2, new_2, upd_2 = await LeadIngestService.ingest_leads(
            db=db,
            raw_leads=raw_leads_2,
            source="GOOGLE_MAPS",
            search_keyword="Mimarlık Bürosu",
            search_location="Ankara Çankaya"
        )
        assert new_2 == 0
        assert upd_2 == 1

        # Verify only 1 lead exists in DB for this place_id
        q = select(Lead).where(Lead.place_id == place_id)
        leads = (await db.execute(q)).scalars().all()
        assert len(leads) == 1
