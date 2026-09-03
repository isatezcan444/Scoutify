"""
Lead Ingestion and Deduplication Service.
Extracted from God Router endpoints to ensure Single Responsibility Principle.
"""
import logging
from typing import List, Dict, Any, Tuple, Optional, Callable, Awaitable, Set
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from backend.app.models.lead import Lead, LeadStatus, EntityType, VerificationStatus, ConfidenceLevel
from backend.app.models.blacklist import Blacklist
from backend.app.services.phone_service import PhoneService
from backend.app.services.lead_match_policy import LeadMatchPolicy, MatchBasis
from backend.app.scrapers.google_maps_playwright_scraper import strip_leading_business_name

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
        progress_callback: Optional[Callable[[int, int], Awaitable[None]]] = None,
    ) -> Tuple[List[Lead], int, int]:
        """
        Processes and saves raw leads into the database.
        Returns:
            (created_leads, total_new_count, total_updated_count)

        progress_callback (optional) receives (processed_count, total) roughly
        every 10 leads so long Supabase round-trips never look like a hang.
        """
        if not raw_leads:
            return [], 0, 0

        total = len(raw_leads)
        if progress_callback:
            await progress_callback(0, total)

        # Pre-pass 1: normalize phones once (sync, cheap) so blacklist lookup
        # collapses from N round-trips into ONE batched query.
        prepared: List[Tuple[Dict[str, Any], str, Optional[str]]] = []
        wanted_e164s: Set[str] = set()
        for raw in raw_leads:
            name = (raw.get("name") or "").strip()
            raw_phone = raw.get("phone")
            phone_data = PhoneService.normalize_to_e164(raw_phone) if raw_phone else None
            e164 = phone_data["e164"] if (phone_data and phone_data["is_valid"]) else raw.get("phone_e164")
            prepared.append((raw, name, e164))
            if e164:
                wanted_e164s.add(e164)

        blacklisted: Set[str] = set()
        if wanted_e164s:
            bl_rows = (
                await db.execute(
                    select(Blacklist.phone_e164).where(Blacklist.phone_e164.in_(wanted_e164s))
                )
            ).scalars().all()
            blacklisted = set(bl_rows)

        all_processed_leads: List[Lead] = []
        created_leads: List[Lead] = []
        new_count = 0
        updated_count = 0
        skipped_no_name = 0
        shared_line_saved = 0
        matched_by: Dict[str, int] = {basis.value: 0 for basis in MatchBasis}
        race_merged = 0
        assigned_batch_e164s: Set[str] = set()

        for idx, (raw, name, e164) in enumerate(prepared):
            if not name:
                skipped_no_name += 1
                continue

            raw_phone = raw.get("phone")
            phone_data = PhoneService.normalize_to_e164(raw_phone) if raw_phone else None

            # Check blacklist (prefetched set — zero extra round-trips)
            is_blacklisted = bool(e164 and e164 in blacklisted)

            # Identity resolution (policy-owned). A distinct business that merely
            # shares a line with an existing row keeps its own row; its targeting
            # number is withheld exactly like discovery-side SHARED_PHONE leads.
            verdict = await cls.match_policy.resolve(db, raw, name, e164)
            if verdict.shares_phone_line:
                e164 = None
                raw = {**raw, "phone_e164": None}
                shared_line_saved += 1

            # Strict phone unique index guard:
            # If e164 is already allocated to another lead in this batch, or already exists on a
            # DIFFERENT row in the database, withhold phone_e164 (None) to satisfy the ix_leads_phone_e164
            # unique constraint while preserving the display phone and creating/updating the lead row.
            if e164:
                target_lead_id = verdict.existing.id if verdict.existing else None
                conflict = False
                if e164 in assigned_batch_e164s:
                    conflict = True
                else:
                    phone_query = select(Lead.id).where(Lead.phone_e164 == e164)
                    if target_lead_id:
                        phone_query = phone_query.where(Lead.id != target_lead_id)
                    # Fail-safe limit(1): legacy prod rows may hold duplicates;
                    # any hit means conflict — never raise "Multiple rows...".
                    phone_query = phone_query.order_by(Lead.id).limit(1)
                    existing_by_phone = (await db.execute(phone_query)).scalar_one_or_none()
                    if existing_by_phone:
                        conflict = True

                if conflict:
                    e164 = None
                    raw = {**raw, "phone_e164": None}
                    shared_line_saved += 1
                else:
                    assigned_batch_e164s.add(e164)

            is_wa_eligible = bool(phone_data and phone_data.get("is_whatsapp_eligible")) if (phone_data and e164) else False
            is_verified = raw.get("is_verified", bool(phone_data and phone_data.get("is_valid")))

            if verdict.existing:
                cls._merge_into_existing(verdict.existing, raw, e164, is_wa_eligible, is_blacklisted)
                if verdict.existing.phone_e164:
                    assigned_batch_e164s.add(verdict.existing.phone_e164)
                updated_count += 1
                matched_by[verdict.basis.value] += 1
                all_processed_leads.append(verdict.existing)
            else:
                lead, merged_into_existing = await cls._persist_new_lead(
                    db, raw, name, e164, phone_data, is_wa_eligible,
                    is_verified, is_blacklisted, source,
                    search_keyword, search_location
                )
                if lead.phone_e164:
                    assigned_batch_e164s.add(lead.phone_e164)
                if merged_into_existing:
                    updated_count += 1
                    race_merged += 1
                else:
                    created_leads.append(lead)
                    new_count += 1
                all_processed_leads.append(lead)

            if progress_callback and (idx + 1 == total or (idx + 1) % 10 == 0):
                await progress_callback(idx + 1, total)

        await db.commit()
        # Single batched re-read instead of N per-row refresh round-trips
        # (matters on remote Postgres: N RTTs looked like a post-scan hang).
        if all_processed_leads:
            ids_in_order = [l.id for l in all_processed_leads]
            rows = (
                await db.execute(select(Lead).where(Lead.id.in_(ids_in_order)))
            ).scalars().all()
            by_id = {r.id: r for r in rows}
            all_processed_leads = [by_id.get(l.id, l) for l in all_processed_leads]

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
        # Self-healing: rows stored before the name-prefix strip carry
        # "Business Name, street...". Normalize them on contact — pure removal
        # of a proven prefix, never injecting new content.
        if existing_lead.address:
            healed = strip_leading_business_name(existing_lead.name, existing_lead.address)
            if healed and healed != existing_lead.address:
                existing_lead.address = healed
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

        # Defensive truncation: protect all VARCHAR-bounded columns from overflow
        def _trunc(val: Optional[str], limit: int) -> Optional[str]:
            if val is None:
                return None
            # Also strip embedded newlines that can corrupt single-line fields
            val = val.split("\n")[0].strip()
            return val[:limit]

        lead = Lead(
            name=name,  # text (unlimited)
            category=raw.get("category"),  # text (unlimited)
            canonical_category=raw.get("canonical_category"),  # text
            category_score=raw.get("category_score", 1.0),
            category_classification=_trunc(raw.get("category_classification", "MATCH"), 50),
            entity_type=_trunc(raw.get("entity_type", EntityType.BUSINESS.value), 50),
            verification_status=_trunc(raw.get("verification_status", VerificationStatus.VERIFIED.value if is_verified else VerificationStatus.UNVERIFIED.value), 50),
            confidence_level=_trunc(raw.get("confidence_level", ConfidenceLevel.HIGH.value if (is_verified and is_wa_eligible) else ConfidenceLevel.MEDIUM.value), 20),
            confidence_score=raw.get("confidence_score", 90 if (is_verified and is_wa_eligible) else 60),
            is_verified=is_verified,
            discovered_from=_trunc(raw.get("discovered_from", source), 100),
            verified_by=raw.get("verified_by"),
            phone=_trunc(raw.get("phone") or (e164 or "Belirtilmemiş"), 50),
            phone_e164=_trunc(e164, 30),  # None if phone is not present — never fabricate numbers
            is_mobile=phone_data.get("is_mobile", False) if phone_data else False,
            is_whatsapp_eligible=is_wa_eligible,
            address=raw.get("address"),  # text
            city=_trunc(raw.get("city"), 100),
            district=_trunc(raw.get("district"), 100),
            latitude=raw.get("latitude"),
            longitude=raw.get("longitude"),
            website=raw.get("website"),  # text
            rating=raw.get("rating"),
            reviews_count=raw.get("reviews_count", 0),
            place_id=_trunc(raw.get("place_id"), 255),
            search_keyword=_trunc(search_keyword or raw.get("search_keyword"), 200),
            search_location=_trunc(search_location or raw.get("search_location"), 200),
            source=_trunc(source, 50),
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
