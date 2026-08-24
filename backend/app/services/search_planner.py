"""
Hierarchical Multi-Strategy Search Planner for Business Discovery Engine V3.
Generates structured discovery queries across independent provider adapters:
1. Overpass Structured Category (OSM Bounded Geo)
2. Directory Exhaustive Category Slugs (Bulurum & Registry)
3. Local Subdivision Geographical Queries (Neighborhood Level)
4. Commercial & Contact Enrichment Queries
"""
import uuid
import logging
from typing import List, Dict, Any, Optional
from backend.app.schemas.intelligence import (
    SearchIntent,
    SearchPlan,
    ProviderQuery,
    QueryFamily
)
from backend.app.data.turkey_subdivisions import get_subdivisions_for_district

logger = logging.getLogger(__name__)


class SearchPlanner:
    """
    V3 Search Planner:
    Coordinates structured queries across Overpass, Directory, and Local Subdivisions.
    """

    @classmethod
    def create_plan(
        cls,
        intent: SearchIntent,
        city: str,
        districts: List[str],
        max_results: int = 0
    ) -> SearchPlan:
        if not city or not city.strip():
            raise ValueError("City is required for search plan")
        if not districts:
            raise ValueError("Districts list cannot be empty for search plan")

        profile = intent.category_profile
        provider_queries: List[ProviderQuery] = []

        primary_term = profile.search_terms[0] if profile.search_terms else profile.display_name
        secondary_terms = profile.search_terms[1:4] if len(profile.search_terms) > 1 else [primary_term]

        for district in districts:
            subdivisions = get_subdivisions_for_district(city, district)

            # =========================================================================
            # STRATEGY 1: OVERPASS STRUCTURED GEOGRAPHIC DISCOVERY (ROUND 1)
            # =========================================================================
            # Structured area query for all category amenity/shop tags
            provider_queries.append(ProviderQuery(
                query_id=f"q_{uuid.uuid4().hex[:8]}",
                query_family=QueryFamily.PROVIDER_TAXONOMY,
                provider_name="overpass",
                query_text=f"Overpass {profile.canonical_id} in {district}",
                district=district,
                city=city,
                round_number=1,
                limit=100
            ))

            # =========================================================================
            # STRATEGY 2: DIRECTORY PRIMARY SLUGS (ROUND 1 & 2)
            # =========================================================================
            # Query top directory slugs
            directory_slugs_to_query = profile.directory_slugs if profile.directory_slugs else [primary_term.lower().replace(" ", "-")]
            for idx, slug in enumerate(directory_slugs_to_query[:4]):
                provider_queries.append(ProviderQuery(
                    query_id=f"q_{uuid.uuid4().hex[:8]}",
                    query_family=QueryFamily.EXACT_INTENT,
                    provider_name="directory",
                    query_text=f"{slug} in {district}, {city}",
                    category_slug=slug,
                    district=district,
                    city=city,
                    round_number=1 if idx < 2 else 2,
                    limit=50
                ))

            # =========================================================================
            # STRATEGY 3: BUSINESS TERMINOLOGY (ROUND 2)
            # =========================================================================
            for term in profile.positive_concepts[:3]:
                provider_queries.append(ProviderQuery(
                    query_id=f"q_{uuid.uuid4().hex[:8]}",
                    query_family=QueryFamily.BUSINESS_TERMINOLOGY,
                    provider_name="osm",
                    query_text=f"{term} {district} {city}",
                    district=district,
                    city=city,
                    round_number=2,
                    limit=30
                ))

            # =========================================================================
            # STRATEGY 4: DIRECTORY SECONDARY & EXPANDED SLUGS (ROUND 3)
            # =========================================================================
            for slug in directory_slugs_to_query[4:8]:
                provider_queries.append(ProviderQuery(
                    query_id=f"q_{uuid.uuid4().hex[:8]}",
                    query_family=QueryFamily.PROVIDER_TAXONOMY,
                    provider_name="directory",
                    query_text=f"{slug} in {district}, {city}",
                    category_slug=slug,
                    district=district,
                    city=city,
                    round_number=3,
                    limit=50
                ))

            # =========================================================================
            # STRATEGY 4: LOCAL SUBDIVISION QUERIES (ROUND 4)
            # =========================================================================
            for sub in subdivisions[:6]:
                provider_queries.append(ProviderQuery(
                    query_id=f"q_{uuid.uuid4().hex[:8]}",
                    query_family=QueryFamily.LOCAL_SUBDIVISION,
                    provider_name="overpass",
                    query_text=f"{primary_term} {sub} {district}",
                    subdivision=sub,
                    district=district,
                    city=city,
                    round_number=4,
                    limit=30
                ))

            # =========================================================================
            # STRATEGY 5: COMMERCIAL & CONTACT ENRICHMENT (ROUND 5)
            # =========================================================================
            for suffix in ["telefon", "randevu"]:
                provider_queries.append(ProviderQuery(
                    query_id=f"q_{uuid.uuid4().hex[:8]}",
                    query_family=QueryFamily.COMMERCIAL_INTENT,
                    provider_name="directory",
                    query_text=f"{primary_term} {district} {suffix}",
                    category_slug=directory_slugs_to_query[0] if directory_slugs_to_query else primary_term.lower().replace(" ", "-"),
                    district=district,
                    city=city,
                    round_number=5,
                    limit=30
                ))

        logger.info(
            f"[SEARCH_PLANNER_V3] Generated {len(provider_queries)} multi-strategy queries "
            f"for category '{profile.canonical_id}' across {len(districts)} districts."
        )

        return SearchPlan(
            search_intent=intent,
            city=city,
            districts=districts,
            max_results=max_results,
            provider_queries=provider_queries
        )
