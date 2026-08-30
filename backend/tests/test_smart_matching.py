"""
Tests for Deterministic Smart Matching Service & Real Lead Qualification (Phase 4).
"""
import pytest
from backend.app.models.lead import Lead, LeadStatus, EntityType, VerificationStatus
from backend.app.schemas.smart_outreach import BusinessGoal, CategoryFitLevel, CategorySource
from backend.app.services.smart_matching_service import SmartMatchingService
from backend.app.core.database import AsyncSessionLocal


def test_evaluate_lead_high_fit():
    lead = Lead(
        id=1,
        name="Kadıköy Dental Ağız ve Diş Sağlığı Merkezi",
        category="Diş Klinikleri & Ağız Sağlığı",
        canonical_category="dental",
        category_score=0.95,
        entity_type=EntityType.CLINIC.value,
        verification_status=VerificationStatus.VERIFIED.value,
        is_verified=True,
        phone="02163334455",
        phone_e164="+905321112233",
        is_whatsapp_eligible=True,
        city="İstanbul",
        district="Kadıköy",
        website="https://kadikoydental.com",
        rating=4.9,
        reviews_count=45,
        status=LeadStatus.NEW
    )

    assessment = SmartMatchingService.evaluate_lead(
        lead=lead,
        offer_title="Dental Sarf Malzemeleri ve İmplant Tedariki",
        offer_description="Toptan diş malzemeleri",
        business_goal=BusinessGoal.DISCOVERY,
        approved_target_categories=["dental", "diş klinikleri"],
        target_city="İstanbul"
    )

    assert assessment.fit_score >= 80
    assert assessment.fit_level == CategoryFitLevel.HIGH
    assert assessment.recommended_intent == BusinessGoal.DISCOVERY
    assert len(assessment.positive_signals) >= 3
    assert any("Onaylanmış hedef kategori" in s for s in assessment.positive_signals)
    assert any("WhatsApp" in s for s in assessment.positive_signals)


def test_evaluate_lead_low_fit_unrelated_sector():
    lead = Lead(
        id=2,
        name="Lider Mobilya Showroom",
        category="Mobilya & Dekorasyon",
        canonical_category="furniture",
        category_score=0.9,
        entity_type=EntityType.BUSINESS.value,
        phone="02124445566",
        phone_e164="+905445556677",
        is_whatsapp_eligible=True,
        city="Ankara",
        district="Çankaya",
        website=None,
        status=LeadStatus.NEW
    )

    assessment = SmartMatchingService.evaluate_lead(
        lead=lead,
        offer_title="Vito VIP Transfer Hizmeti",
        business_goal=BusinessGoal.DISCOVERY,
        approved_target_categories=["hotels", "turizm"],
        target_city="Ankara"
    )

    # Low score because furniture is unrelated to transfer
    assert assessment.fit_score < 75
    assert any("Kategori" in r for r in assessment.risk_factors)


def test_evaluate_lead_wrong_location_penalized():
    lead = Lead(
        id=3,
        name="Anadolu Lojistik ve Dağıtım Ltd.",
        category="Lojistik Firmaları",
        entity_type=EntityType.BUSINESS.value,
        phone="02124440011",
        phone_e164="+905329998877",
        is_whatsapp_eligible=True,
        city="İstanbul",
        district="Ataşehir",
        website="https://anadolulojistik.com",
        status=LeadStatus.NEW
    )

    # User target is Ankara, lead is in Istanbul
    assessment = SmartMatchingService.evaluate_lead(
        lead=lead,
        offer_title="Kurumsal Yazılım Çözümü",
        business_goal=BusinessGoal.DISCOVERY,
        approved_target_categories=["Lojistik Firmaları"],
        target_city="Ankara"
    )

    assert any("Farklı şehir" in r for r in assessment.risk_factors)


def test_evaluate_lead_person_entity():
    lead = Lead(
        id=4,
        name="Ahmet Yılmaz (Bireysel Danışman)",
        category="Danışmanlık",
        entity_type=EntityType.PERSON.value,
        phone="05321110000",
        phone_e164="+905321110000",
        is_whatsapp_eligible=True,
        city="Ankara",
        district="Çankaya",
        website=None,
        status=LeadStatus.NEW
    )

    assessment = SmartMatchingService.evaluate_lead(
        lead=lead,
        offer_title="Kurumsal Yazılım Çözümü",
        business_goal=BusinessGoal.DISCOVERY,
        approved_target_categories=["Danışmanlık"],
        target_city="Ankara"
    )

    assert any("Şahıs" in r for r in assessment.risk_factors)


def test_evaluate_lead_no_whatsapp_and_no_phone():
    lead_no_phone = Lead(
        id=5,
        name="Gizli Tasarım Ofisi",
        category="Mimarlık",
        entity_type=EntityType.BUSINESS.value,
        phone=None,
        phone_e164=None,
        is_whatsapp_eligible=False,
        city="Ankara",
        status=LeadStatus.NEW
    )

    assessment = SmartMatchingService.evaluate_lead(
        lead=lead_no_phone,
        offer_title="Mimarlık Yazılımı",
        business_goal=BusinessGoal.DISCOVERY,
        approved_target_categories=["Mimarlık"],
        target_city="Ankara"
    )

    assert any("Telefon numarası bulunmuyor" in r for r in assessment.risk_factors)
    assert not any("WhatsApp erişimi doğrulanmış" in s for s in assessment.positive_signals)


@pytest.mark.asyncio
async def test_match_and_rank_leads_db_flow():
    async with AsyncSessionLocal() as db:
        matched = await SmartMatchingService.match_and_rank_leads(
            db=db,
            offer_title="Kurumsal yazılım çözümü",
            offer_description="KOBİ dijital dönüşüm çözümleri",
            business_goal=BusinessGoal.DISCOVERY,
            approved_target_categories=["Mimarlık Ofisleri", "Perakende"],
            city="Ankara",
            min_fit_score=30
        )

        assert isinstance(matched, list)
        # Verify descending order of fit scores
        for i in range(len(matched) - 1):
            assert matched[i].fit_assessment.fit_score >= matched[i + 1].fit_assessment.fit_score
