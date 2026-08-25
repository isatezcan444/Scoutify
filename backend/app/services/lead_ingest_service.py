"""
Lead Ingestion and Deduplication Service.
Extracted from God Router endpoints to ensure Single Responsibility Principle.
"""
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from backend.app.models.lead import Lead, LeadStatus, EntityType, VerificationStatus, ConfidenceLevel
from backend.app.models.blacklist import Blacklist
from backend.app.services.phone_service import PhoneService
from backend.app.services.lead_match_policy import LeadMatchPolicy, MatchBasis

logger = logging.getLogger(__name__)


class LeadIngestService:
    """
    Handles robust lead ingestion, normalization, blacklist verification,
    deduplication, and database persistence.

    Concurrency invariant: unique constraints (place_id / phone_e164) are enforced
    per-lead inside a SAVEPOINT. A concurrent job winning the insert race can no
    longer fail the whole batch — the conflicting lead is merged instead.

    Identity invariant: whether an incoming candidate IS an existing lead is
    delegated to LeadMatchPolicy; this service never merges two distinct
    businesses sharing merely a phone line.
    """

    # DI seam: tests / alternative deployments can swap matching semantics.
    match_policy = LeadMatchPolicy()

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
        skipped_no_name = 0
        shared_line_saved = 0
        matched_by: Dict[str, int] = {basis.value: 0 for basis in MatchBasis}
        race_merged = 0

        for raw in raw_leads:
            name = (raw.get("name") or "").strip()
            if not name:
                skipped_no_name += 1
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

            # Identity resolution (policy-owned). A distinct business that merely
            # shares a line with an existing row keeps its own row; its targeting
            # number is withheld exactly like discovery-side SHARED_PHONE leads.
            verdict = await cls.match_policy.resolve(db, raw, name, e164)
            if verdict.shares_phone_line:
                e164 = None
                raw = {**raw, "phone_e164": None}
                shared_line_saved += 1

            is_wa_eligible = bool(phone_data and phone_data.get("is_whatsapp_eligible")) if phone_data else False
            is_verified = raw.get("is_verified", bool(phone_data and phone_data.get("is_valid")))

            if verdict.existing:
                cls._merge_into_existing(verdict.existing, raw, e164, is_wa_eligible, is_blacklisted)
                updated_count += 1
                matched_by[verdict.basis.value] += 1
                all_processed_leads.append(verdict.existing)
            else:
                lead, merged_into_existing = await cls._persist_new_lead(
                    db, raw, name, e164, phone_data, is_wa_eligible,
                    is_verified, is_blacklisted, source,
                    search_keyword, search_location
                )
                if merged_into_existing:
                    updated_count += 1
                    race_merged += 1
                else:
                    created_leads.append(lead)
                    new_count += 1
                all_processed_leads.append(lead)

        await db.commit()
        for l in all_processed_leads:
            await db.refresh(l)

        logger.info(
            f"[LeadIngestService] Ingest complete: total_raw={len(raw_leads)}, "
            f"new={new_count}, updated={updated_count} "
            f"(by_place={matched_by[MatchBasis.PLACE_ID.value]}, "
            f"by_phone={matched_by[MatchBasis.PHONE.value]}, "
            f"by_identity={matched_by[MatchBasis.NAME_LOCATION.value]}, "
            f"race_merged={race_merged}) "
            f"shared_line_new_rows={shared_line_saved}, skipped_no_name={skipped_no_name}"
        )
        return all_processed_leads, new_count, updated_count



    @staticmethod
    def _merge_into_existing(
        existing_lead: Lead,
        raw: Dict[str, Any],
        e164: Optional[str],
        is_wa_eligible: bool,
        is_blacklisted: bool,
    ) -> None:
        """Backfills richer details discovered on a subsequent scan of the same business."""
        maps_url = raw.get("maps_url") or raw.get("google_maps_url")
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
        if maps_url and not (existing_lead.custom_data or {}).get("maps_url"):
            existing_lead.custom_data = {**(existing_lead.custom_data or {}), "maps_url": maps_url}
        existing_lead.updated_at = datetime.utcnow()

    @staticmethod
    def _initial_custom_data(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Builds the initial custom_data payload preserving the canonical Maps URL."""
        maps_url = raw.get("maps_url") or raw.get("google_maps_url")
        return {"maps_url": maps_url} if maps_url else {}

    @classmethod
    async def _persist_new_lead(
        cls,
        db: AsyncSession,
        raw: Dict[str, Any],
        name: str,
        e164: Optional[str],
        phone_data: Optional[Dict[str, Any]],
        is_wa_eligible: bool,
        is_verified: bool,
        is_blacklisted: bool,
        source: str,
        search_keyword: Optional[str],
        search_location: Optional[str],
    ) -> Tuple[Lead, bool]:
        """
        Inserts a new lead inside a SAVEPOINT so a concurrent-job IntegrityError
        rolls back only this insert; the winner's row is then merged instead.
        Returns (lead, merged_into_existing).
        """
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
            phone_e164=e164,  # None if phone is not present — never fabricate numbers
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
            place_id=raw.get("place_id"),
            search_keyword=search_keyword or raw.get("search_keyword"),
            search_location=search_location or raw.get("search_location"),
            source=source,
            status=initial_status,
            custom_data=cls._initial_custom_data(raw),
        )

        try:
            async with db.begin_nested():
                db.add(lead)
                await db.flush()
        except IntegrityError:
            logger.warning(
                f"[LeadIngestService] Concurrent insert race detected for '{name}' "
                f"(place_id={raw.get('place_id')}, e164={e164}). Merging into winner."
            )
            verdict = await cls.match_policy.resolve(db, raw, name, e164)
            winner = verdict.existing
            if winner:
                cls._merge_into_existing(winner, raw, e164, is_wa_eligible, is_blacklisted)
                return winner, True
            raise
        return lead, False
