"""
Generic Business Quality & Qualification Engine.
Evaluates entity validity, contact completeness, location validity, and computes 5 independent scores.
Enforces Hard Gates: Category mismatch or Location mismatch immediately results in REJECTION.
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from backend.app.schemas.intelligence import (
    RawBusinessCandidate,
    CategoryAssessment,
    CategoryMatchClassification,
    QualityAssessment,
    QualificationState
)
from backend.app.services.entity_resolver import EntityResolver, EntityType, SourceTrustTier

logger = logging.getLogger(__name__)


class BusinessQualityEngine:
    """
    Generic Business Quality Engine:
    1. Evaluates 5 independent dimensions (Category, Location, Entity, Contact, Source).
    2. Enforces non-negotiable Hard Gates: Category Mismatch cannot be averaged away.
    3. Produces explainable QualityAssessment.
    """

    @classmethod
    def evaluate(
        cls,
        candidate: RawBusinessCandidate,
        category_assessment: CategoryAssessment,
        location_confidence_val: str,
        phone_data: Optional[Dict[str, Any]],
        target_category_display: str
    ) -> QualityAssessment:
        positive_signals: List[str] = []
        risk_factors: List[str] = []
        rejection_reasons: List[str] = []

        # =========================================================================
        # 1. CATEGORY SCORE & HARD GATE
        # =========================================================================
        category_score = category_assessment.score
        if category_assessment.classification == CategoryMatchClassification.MISMATCH:
            rejection_reasons.append(f"Kategori uyuşmazlığı: {category_assessment.reason}")
        elif category_score >= 0.7:
            positive_signals.append(f"Kategori tam uyumu ({int(category_score * 100)}%)")

        # =========================================================================
        # 2. LOCATION SCORE & HARD GATE
        # =========================================================================
        loc_conf = location_confidence_val.upper()
        if "EXACT" in loc_conf:
            location_score = 1.0
            positive_signals.append("Hedef ilçe coğrafi doğrulaması tam (EXACT_DISTRICT)")
        elif "CITY" in loc_conf:
            location_score = 0.7
            positive_signals.append("İl geneli coğrafi uyum (CITY_ONLY)")
        elif "OUTSIDE" in loc_conf:
            location_score = 0.0
            rejection_reasons.append("Hedef lokasyon dışı (OUTSIDE_TARGET)")
        else:
            location_score = 0.4
            risk_factors.append("Lokasyon kesinliği zayıf (UNKNOWN)")

        # =========================================================================
        # 3. ENTITY TYPE & RESOLUTION
        # =========================================================================
        entity_type_enum, entity_reasons = EntityResolver.detect_entity_type(
            name=candidate.clean_name,
            category=target_category_display,
            address=candidate.raw_address or "",
            website=candidate.raw_website
        )
        entity_type = entity_type_enum.value

        if entity_type in (EntityType.CLINIC.value, EntityType.COMPANY.value):
            entity_score = 1.0
            positive_signals.append(f"Doğrulanmış ticari kuruluş tipi: {entity_type}")
        elif entity_type == EntityType.BUSINESS.value:
            entity_score = 0.9
            positive_signals.append("Doğrulanmış ticari işletme tipi: BUSINESS")
        elif entity_type == EntityType.PERSON.value:
            entity_score = 0.2
            risk_factors.append("Şahıs/Doktor profili (PERSON != BUSINESS). Ticari işletme doğrulanmadı.")
        else:
            entity_score = 0.3
            risk_factors.append("Tanımsız entity profili")

        # =========================================================================
        # 4. CONTACT SCORE
        # =========================================================================
        has_phone = bool(phone_data and phone_data.get("e164"))
        has_addr = bool(candidate.raw_address and len(candidate.raw_address.strip()) > 8)
        has_web = bool(candidate.raw_website and len(candidate.raw_website.strip()) > 5)

        contact_score = 0.0
        if has_phone:
            contact_score += 0.6
            positive_signals.append(f"E.164 telefon mevcut: {phone_data['e164']}")
            if phone_data.get("is_mobile"):
                contact_score += 0.1
                positive_signals.append("WhatsApp uyumlu mobil GSM")
        else:
            risk_factors.append("Telefon numarası eksik")

        if has_addr:
            contact_score += 0.2
            positive_signals.append("Fiziksel açık adres mevcut")
        if has_web:
            contact_score += 0.1
            positive_signals.append("Web sitesi mevcut")

        contact_score = min(contact_score, 1.0)

        # =========================================================================
        # 5. SOURCE SCORE
        # =========================================================================
        source_tier = EntityResolver.get_source_tier(candidate.provider, has_official_website=has_web)
        if source_tier == SourceTrustTier.TIER_1_STRONG:
            source_score = 1.0
            positive_signals.append("Tier 1 Güçlü Kaynak (Maps / Resmi Web)")
        elif source_tier == SourceTrustTier.TIER_2_SUPPORTING:
            source_score = 0.8
            positive_signals.append("Tier 2 Destekleyici Kaynak (B2B Dizin / OSM)")
        else:
            source_score = 0.5
            risk_factors.append("Tier 3 Zayıf Kaynak")

        # =========================================================================
        # HARD GATES & FINAL QUALIFICATION STATE
        # =========================================================================
        is_hard_rejected = False

        if category_assessment.classification == CategoryMatchClassification.MISMATCH:
            is_hard_rejected = True
        if location_score == 0.0:
            is_hard_rejected = True

        if is_hard_rejected:
            qualification_state = QualificationState.REJECTED
            overall_quality_score = 0
            is_verified = False
        else:
            # Weighted Overall Score
            raw_weighted = (
                category_score * 0.35 +
                location_score * 0.25 +
                entity_score * 0.20 +
                contact_score * 0.10 +
                source_score * 0.10
            )
            overall_quality_score = int(raw_weighted * 100)

            if entity_type == EntityType.PERSON.value or overall_quality_score < 50:
                qualification_state = QualificationState.UNVERIFIED
                is_verified = False
            elif overall_quality_score >= 65 and category_score >= 0.6:
                qualification_state = QualificationState.QUALIFIED
                is_verified = True
            else:
                qualification_state = QualificationState.CANDIDATE
                is_verified = False

        return QualityAssessment(
            category_score=round(category_score, 3),
            location_score=round(location_score, 3),
            entity_score=round(entity_score, 3),
            contact_score=round(contact_score, 3),
            source_score=round(source_score, 3),
            overall_quality_score=overall_quality_score,
            qualification_state=qualification_state,
            entity_type=entity_type,
            is_verified=is_verified,
            positive_signals=positive_signals,
            risk_factors=risk_factors,
            rejection_reasons=rejection_reasons
        )
