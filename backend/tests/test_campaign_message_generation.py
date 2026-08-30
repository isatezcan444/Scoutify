"""
Unit and API integration tests for Campaign Message Generation Engine.
Tests:
- All 6 Communication Goals (FIRST_CONTACT, SERVICE_PROMOTION, DISCOVERY, OFFER, MEETING, FOLLOW_UP)
- Turkish and English message generation
- Sector-aware contextualization
- Goal-specific required field validation (HTTP 400)
- Spintax variable format safety
- Variation seed generation
- Campaign creation as DRAFT
"""
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.services.message_strategy_service import MessageStrategyService
from backend.app.schemas.campaign import GenerateMessageRequest


@pytest.mark.asyncio
async def test_generate_message_first_contact_tr():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/campaigns/generate-message", json={
            "communication_goal": "FIRST_CONTACT",
            "target_category": "Diş Klinikleri",
            "offer_title": "Dental Sarf Malzemeleri",
            "extra_information": "Uygun fiyat ve hızlı teslimat avantajlarımız mevcuttur",
            "language": "tr"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["communication_goal"] == "FIRST_CONTACT"
        assert data["language"] == "tr"
        assert "{name}" in data["generated_message"]
        assert "Dental Sarf Malzemeleri" in data["generated_message"]
        assert "Diş Klinikleri" in data["generated_message"]


@pytest.mark.asyncio
async def test_generate_message_service_promotion_tr_and_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Missing required offer_title
        err_res = await client.post("/api/v1/campaigns/generate-message", json={
            "communication_goal": "SERVICE_PROMOTION",
            "target_category": "Oteller",
            "offer_title": "",
            "key_benefit": "Hızlı check-in",
            "language": "tr"
        })
        assert err_res.status_code == 400
        assert "zorunludur" in err_res.json()["detail"]

        # Valid payload
        res = await client.post("/api/v1/campaigns/generate-message", json={
            "communication_goal": "SERVICE_PROMOTION",
            "target_category": "Diş Klinikleri",
            "offer_title": "Diş kliniği yönetim yazılımı",
            "key_benefit": "Randevu ve hasta takibini tek panelden yönetme",
            "extra_information": "Kliniklerin operasyon yükünü azaltmak",
            "language": "tr"
        })
        assert res.status_code == 200
        data = res.json()
        assert "Diş kliniği yönetim yazılımı" in data["generated_message"]
        assert "Randevu ve hasta takibini tek panelden yönetme" in data["generated_message"]


@pytest.mark.asyncio
async def test_generate_message_discovery_en_and_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Missing lead_need
        err_res = await client.post("/api/v1/campaigns/generate-message", json={
            "communication_goal": "DISCOVERY",
            "target_category": "Architecture Studios",
            "offer_title": "BIM Modeling Software",
            "lead_need": "",
            "language": "en"
        })
        assert err_res.status_code == 400

        # Valid EN Discovery
        res = await client.post("/api/v1/campaigns/generate-message", json={
            "communication_goal": "DISCOVERY",
            "target_category": "Architecture Studios",
            "offer_title": "ERP & Workflow Automation",
            "lead_need": "modern project tracking tools",
            "specific_question": "Which team oversees software implementation?",
            "language": "en"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["language"] == "en"
        assert "Regarding ERP & Workflow Automation" in data["generated_message"]
        assert "Architecture Studios" in data["generated_message"]
        assert "modern project tracking tools" in data["generated_message"]


@pytest.mark.asyncio
async def test_generate_message_offer_tr():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/campaigns/generate-message", json={
            "communication_goal": "OFFER",
            "target_category": "Restoranlar",
            "offer_title": "QR Menü ve Sipariş Sistemi",
            "key_benefit": "Yıllık abonelikte %30 indirim",
            "pricing_info": "İlk 3 ay ücretsiz deneme",
            "language": "tr"
        })
        assert res.status_code == 200
        data = res.json()
        assert "QR Menü ve Sipariş Sistemi" in data["generated_message"]
        assert "Yıllık abonelikte %30 indirim" in data["generated_message"]
        assert "İlk 3 ay ücretsiz deneme" in data["generated_message"]


@pytest.mark.asyncio
async def test_generate_message_meeting_en():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/campaigns/generate-message", json={
            "communication_goal": "MEETING",
            "target_category": "Logistics Companies",
            "offer_title": "Fleet Tracking GPS Platform",
            "meeting_purpose": "reviewing fuel cost reduction metrics",
            "preferred_channel": "a 10-minute online demo",
            "language": "en"
        })
        assert res.status_code == 200
        data = res.json()
        assert "Fleet Tracking GPS Platform" in data["generated_message"]
        assert "a 10-minute online demo" in data["generated_message"]
        assert "fuel cost reduction" in data["generated_message"]


@pytest.mark.asyncio
async def test_generate_message_follow_up_tr():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/campaigns/generate-message", json={
            "communication_goal": "FOLLOW_UP",
            "target_category": "E-Ticaret Firmaları",
            "previous_topic": "B2B Kargo Entegrasyonu",
            "key_benefit": "Teklifimizi inceleme fırsatınız oldu mu?",
            "extra_information": "Özel fiyat tarifemiz bu hafta geçerlidir",
            "language": "tr"
        })
        assert res.status_code == 200
        data = res.json()
        assert "B2B Kargo Entegrasyonu" in data["generated_message"]
        assert "bu hafta geçerlidir" in data["generated_message"]


@pytest.mark.asyncio
async def test_variation_seed_alternation():
    msg1, _ = MessageStrategyService.generate_campaign_message(
        communication_goal="FIRST_CONTACT",
        target_category="Diş Klinikleri",
        language="tr",
        variation_seed=0
    )
    msg2, _ = MessageStrategyService.generate_campaign_message(
        communication_goal="FIRST_CONTACT",
        target_category="Diş Klinikleri",
        language="tr",
        variation_seed=1
    )
    assert msg1 != msg2


@pytest.mark.asyncio
async def test_campaign_created_as_draft_without_sending():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/campaigns", json={
            "name": "Test Draft Campaign",
            "message_template": "Merhaba {name}, {category} sektöründeki firmanızla tanışmak istedik.",
            "min_delay_seconds": 45,
            "max_delay_seconds": 90
        })
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "DRAFT"
        assert data["sent_count"] == 0
        assert data["failed_count"] == 0
