"""
Lead Identity Resolution Policy (database level).

Single decision point answering: "Is this freshly discovered business the SAME
lead as a row that already exists in the database?"

Extracted from LeadIngestService for Single Responsibility: matching semantics
live here, persistence lives there. The policy mirrors the discovery-side
invariant documented in GoogleMapsScraper — a shared phone line never collapses
two distinct businesses; it only flags the number.
"""
import enum
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.lead import Lead


class MatchBasis(str, enum.Enum):
    PLACE_ID = "PLACE_ID"            # Canonical Google Maps place identity.
    PHONE = "PHONE"                  # Same number AND same/unknown place identity.
    NAME_LOCATION = "NAME_LOCATION"  # Identical name within the same city+district.


@dataclass(frozen=True)
class MatchVerdict:
    """Outcome of resolving one incoming candidate against persisted leads."""
    existing: Optional[Lead] = None         # Row to merge into, when matched.
    basis: Optional[MatchBasis] = None      # Which rule produced the match.
    shares_phone_line: bool = False         # Distinct business on an already-saved line.


class LeadMatchPolicy:
    """
    Deduplication cascade with an anti-collapsing guard:

    1. ``place_id`` hit → same physical listing → merge.
    2. ``phone_e164`` hit → merge ONLY when place identities agree or either side
       is unknown. Two different place_ids sharing one number (franchise 0850
       call-center lines, shared building lines) remain separate rows: the later
       candidate keeps its display phone but gets its targeting e164 withheld by
       the caller — identical to the discovery-side SHARED_PHONE treatment.
    3. Exact ``(name, city, district)`` triple → same listing entry → merge.

    Rationale: merging on a bare phone number silently absorbed distinct
    businesses into an earlier row, which surfaced to users as "found N
    businesses but saved fewer than N" data loss across repeated scans.
    """

    async def resolve(
        self,
        db: AsyncSession,
        raw: dict,
        name: str,
        e164: Optional[str],
    ) -> MatchVerdict:
        place_id = raw.get("place_id")

        if place_id:
            existing = await self._first(
                db, select(Lead).where(Lead.place_id == place_id)
            )
            if existing:
                return MatchVerdict(existing=existing, basis=MatchBasis.PLACE_ID)

        if e164:
            existing = await self._first(
                db, select(Lead).where(Lead.phone_e164 == e164)
            )
            if existing:
                identities_agree = (
                    not existing.place_id
                    or not place_id
                    or existing.place_id == place_id
                )
                if identities_agree:
                    return MatchVerdict(existing=existing, basis=MatchBasis.PHONE)
                # Different physical places share the line → never collapse them.
                return MatchVerdict(shares_phone_line=True)

        existing = await self._first(
            db,
            select(Lead).where(
                Lead.name == name,
                Lead.city == raw.get("city"),
                Lead.district == raw.get("district"),
            ),
        )
        if existing:
            return MatchVerdict(existing=existing, basis=MatchBasis.NAME_LOCATION)

        return MatchVerdict()

    @staticmethod
    async def _first(db: AsyncSession, stmt) -> Optional[Lead]:
        return (await db.execute(stmt)).scalar_one_or_none()
