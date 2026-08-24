"""
Lead Ingestion and Deduplication Service.
Extracted from God Router endpoints to ensure Single Responsibility Principle.
"""
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from backend.app.models.lead import Lead, LeadStatus, EntityType, VerificationStatus, ConfidenceLevel
from backend.app.models.blacklist import Blacklist
from backend.app.services.phone_service import PhoneService

logger = logging.getLogger(__name__)


class LeadIngestService:
    """
    Handles robust lead ingestion, normalization, blacklist verification,
    deduplication, and database persistence.
    """

    @classmethod
    async def ingest_leads(
        cls,
        db: AsyncSession,
        raw_leads: List[Dict[str, Any]],
        source: str = "GOOGLE_MAPS",
        search_keyword: Optional[str] = None,
        search_location: Optional[str] = None,
    ) -> Tuple[List[Lead], int, int]:
        """
        Processes and saves raw leads into the database.
        Returns:
            (created_leads, total_new_count, total_updated_count)
        """
        if not raw_leads:
            return [], 0, 0

        all_processed_leads: List[Lead] = []
        created_leads: List[Lead] = []
        new_count = 0
        updated_count = 0

        for raw in raw_leads:
            name = (raw.get("name") or "").strip()
            if not name:
                continue

            raw_phone = raw.get("phone")
            phone_data = PhoneService.normalize_to_e164(raw_phone) if raw_phone else None
            e164 = phone_data["e164"] if (phone_data and phone_data["is_valid"]) else raw.get("phone_e164")
            
            # Check blacklist
            is_blacklisted = False
            if e164:
                bl_stmt = select(Blacklist).where(Blacklist.phone_e164 == e164)
                bl_res = await db.execute(bl_stmt)
                if bl_res.scalar_one_or_none():
                    is_blacklisted = True

            # Deduplication lookup
            existing_lead = None
            place_id = raw.get("place_id")
            
            if place_id:
                stmt = select(Lead).where(Lead.place_id == place_id)
                res = await db.execute(stmt)
                existing_lead = res.scalar_one_or_none()

            if not existing_lead and e164:
                stmt = select(Lead).where(Lead.phone_e164 == e164)
                res = await db.execute(stmt)
                existing_lead = res.scalar_one_or_none()

            if not existing_lead:
                # Deduplicate by clean name + district + city
                city = raw.get("city")
                district = raw.get("district")
                stmt = select(Lead).where(
                    Lead.name == name,
                    Lead.city == city,
                    Lead.district == district
                )
                res = await db.execute(stmt)
                existing_lead = res.scalar_one_or_none()

            is_wa_eligible = bool(phone_data and phone_data.get("is_whatsapp_eligible")) if phone_data else False
            is_verified = raw.get("is_verified", bool(phone_data and phone_data.get("is_valid")))

            if existing_lead:
                # Update details if richer data discovered
                if not existing_lead.phone_e164 and e164:
                    existing_lead.phone_e164 = e164
                    existing_lead.phone = e164
                    existing_lead.is_whatsapp_eligible = is_wa_eligible
                if not existing_lead.website and raw.get("website"):
                    existing_lead.website = raw.get("website")
                if not existing_lead.address and raw.get("address"):
                    existing_lead.address = raw.get("address")
                if raw.get("rating") and not existing_lead.rating:
                    existing_lead.rating = raw.get("rating")
                if is_blacklisted:
                    existing_lead.status = LeadStatus.UNSUBSCRIBED
                existing_lead.updated_at = datetime.utcnow()
                updated_count += 1
                all_processed_leads.append(existing_lead)
            else:
                initial_status = LeadStatus.UNSUBSCRIBED if is_blacklisted else LeadStatus.NEW
                
                lead = Lead(
                    name=name,
                    category=raw.get("category"),
                    canonical_category=raw.get("canonical_category"),
                    category_score=raw.get("category_score", 1.0),
                    category_classification=raw.get("category_classification", "MATCH"),
                    entity_type=raw.get("entity_type", EntityType.BUSINESS.value),
                    verification_status=raw.get("verification_status", VerificationStatus.VERIFIED.value if is_verified else VerificationStatus.UNVERIFIED.value),
                    confidence_level=raw.get("confidence_level", ConfidenceLevel.HIGH.value if (is_verified and is_wa_eligible) else ConfidenceLevel.MEDIUM.value),
                    confidence_score=raw.get("confidence_score", 90 if (is_verified and is_wa_eligible) else 60),
                    is_verified=is_verified,
                    discovered_from=raw.get("discovered_from", source),
                    verified_by=raw.get("verified_by"),
                    phone=raw.get("phone") or (e164 or "Belirtilmemiş"),
                    phone_e164=e164,  # None if phone is not present
                    is_mobile=phone_data.get("is_mobile", False) if phone_data else False,
                    is_whatsapp_eligible=is_wa_eligible,
                    address=raw.get("address"),
                    city=raw.get("city"),
                    district=raw.get("district"),
                    latitude=raw.get("latitude"),
                    longitude=raw.get("longitude"),
                    website=raw.get("website"),
                    rating=raw.get("rating"),
                    reviews_count=raw.get("reviews_count", 0),
                    place_id=place_id,
                    search_keyword=search_keyword or raw.get("search_keyword"),
                    search_location=search_location or raw.get("search_location"),
                    source=source,
                    status=initial_status,
                )
                db.add(lead)
                created_leads.append(lead)
                all_processed_leads.append(lead)
                new_count += 1

        await db.commit()
        for l in all_processed_leads:
            await db.refresh(l)

        logger.info(f"[LeadIngestService] Ingest complete: total_raw={len(raw_leads)}, new={new_count}, updated={updated_count}")
        return all_processed_leads, new_count, updated_count
