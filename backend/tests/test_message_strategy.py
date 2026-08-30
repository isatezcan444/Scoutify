"""
Tests for Category-Aware Message Strategy Engine (Phase 5).
"""
import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.lead import Lead, LeadStatus, EntityType
from backend.app.schemas.smart_outreach import BusinessGoal
from backend.app.services.message_strategy_service import MessageStrategyService


def test_message_strategy_hotel_vs_corporate_vip_transfer():
    """
    Verifies that the same offer ('VIP Transfer') generates distinct, category-appropriate
    contexts for Hotels vs Corporate Companies.
    """
    hotel_res = MessageStrategyService.generate_recommendation(
        lead_id=10,
        lead_name="Grand Bosphorus Hotel",
        target_category="Oteller & Konaklama Tesisleri",
        offer_title="Vito VIP Transfer Hizmeti",
        business_goal=BusinessGoal.DISCOVERY
    )
    assert "Grand Bosphorus Hotel" in hotel_res.recommended_message
    assert any(w in hotel_res.recommended_message.lower() for w in ["misafir", "havalimani", "konaklayan"])
    assert hotel_res.alternative_message != ""

    corp_res = MessageStrategyService.generate_recommendation(
        lead_id=11,
        lead_name="Anadolu Holding A.Ş.",
        target_category="Kurumsal Şirketler",
        offer_title="Vito VIP Transfer Hizmeti",
        business_goal=BusinessGoal.DISCOVERY
    )
    assert "Anadolu Holding A.Ş." in corp_res.recommended_message
    from backend.app.data.turkey_locations import normalize_turkish
    norm_corp_msg = normalize_turkish(corp_res.recommended_message.lower())
    assert any(w in norm_corp_msg for w in ["yonetici", "ortak", "sirket"])
    assert hotel_res.recommended_message != corp_res.recommended_message


def test_message_strategy_architecture_software():
    """
    Verifies that software offer targeting architecture category yields project workflow context.
    """
    arch_res = MessageStrategyService.generate_recommendation(
        lead_id=12,
        lead_name="Artı Mimarlık Bürosu",
        target_category="Mimarlık Ofisleri",
        offer_title="Kurumsal Yazılım Çözümü",
        business_goal=BusinessGoal.DISCOVERY
    )
    assert "Artı Mimarlık Bürosu" in arch_res.recommended_message
    assert any(w in arch_res.recommended_message.lower() for w in ["mimarlik", "is akis", "proje"])
    # Verify no fitscore / risk factor leakage
    assert "%" not in arch_res.recommended_message
    assert "risk" not in arch_res.recommended_message.lower()
    assert "uygun" in arch_res.recommended_message.lower()


def test_message_strategy_goals_differ():
    """
    Verifies that DISCOVERY vs OFFER goals generate different message structures.
    """
    discovery_res = MessageStrategyService.generate_recommendation(
        lead_id=13,
        lead_name="Örnek Klinik",
        target_category="Dental Klinikler",
        offer_title="Dental Sarf Malzemeleri",
        business_goal=BusinessGoal.DISCOVERY
    )
    offer_res = MessageStrategyService.generate_recommendation(
        lead_id=13,
        lead_name="Örnek Klinik",
        target_category="Dental Klinikler",
        offer_title="Dental Sarf Malzemeleri",
        business_goal=BusinessGoal.OFFER
    )
    assert discovery_res.recommended_message != offer_res.recommended_message
    assert "?" in discovery_res.recommended_message


def test_message_strategy_missing_lead_name():
    """
    Verifies clean greeting when business name is missing or unknown.
    """
    res = MessageStrategyService.generate_recommendation(
        lead_id=14,
        lead_name="",
        target_category="Mimarlık Ofisleri",
        offer_title="Kurumsal Yazılım",
        business_goal=BusinessGoal.DISCOVERY
    )
    assert res.recommended_message.startswith("Merhaba,")


@pytest.mark.asyncio
async def test_recommend_message_api_endpoint():
    """
    Integration test with existing lead in database.
    """
    import random
    rand_phone = f"+90533{random.randint(1000000, 9999999)}"
    async with AsyncSessionLocal() as db:
        lead = Lead(
            name="Test Architecture Lab",
            category="Mimarlık Ofisleri",
            city="Ankara",
            phone=rand_phone,
            phone_e164=rand_phone,
            is_whatsapp_eligible=True,
            status=LeadStatus.NEW
        )
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        lead_id = lead.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/smart-outreach/recommend-message", json={
            "lead_id": lead_id,
            "offer_title": "Kurumsal Yazılım Çözümü",
            "business_goal": "DISCOVERY"
        })

    assert response.status_code == 200
    data = response.json()
    assert data["lead_id"] == lead_id
    assert "Test Architecture Lab" in data["recommended_message"]
    assert data["alternative_message"] != ""

