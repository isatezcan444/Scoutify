"""
Intent Resolver & Dynamic Semantic Fallback Engine.
Transforms arbitrary user search text into structured SearchIntent & CategoryProfile
without requiring code modifications for new/unseen categories.
"""
import re
import logging
from typing import Dict, Any, List, Optional
from backend.app.schemas.intelligence import (
    SearchIntent,
    CategoryProfile
)
from backend.app.services.taxonomy_registry import TaxonomyRegistry
from backend.app.data.turkey_locations import normalize_turkish

logger = logging.getLogger(__name__)


class IntentResolver:
    """
    Generic Intent Resolver:
    1. Normalizes user business query (removes stopwords, conjunctions, punctuation).
    2. Matches against Relational Taxonomy.
    3. If unseen/unknown category, dynamically synthesizes an on-the-fly CategoryProfile.
    """

    STOPWORDS = {
        "ve", "ile", "veya", "için", "olan", "tüm", "en", "iyi", "özel", "genel",
        "hizmetleri", "firmaları", "şirketleri", "merkezleri", "yerleri", "dükkanları"
    }

    @classmethod
    def clean_query_text(cls, raw_query: str) -> str:
        """Cleans and standardizes raw user business query."""
        if not raw_query:
            return ""
        # Remove special noise characters while preserving Turkish letters
        cleaned = re.sub(r'[\&\|\,\+\-\/\(\)\"\']', ' ', raw_query)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    @classmethod
    def is_generic_single_token(cls, token: str) -> bool:
        """Determines if a single token is too generic to be used as a standalone query term."""
        norm_t = normalize_turkish(token.strip())
        if not norm_t or len(norm_t) <= 2:
            return True
        if norm_t in TaxonomyRegistry.GENERIC_WORDS:
            return True
        # Check plural or derived suffix forms of generic words
        for g in TaxonomyRegistry.GENERIC_WORDS:
            if norm_t.startswith(g) and len(norm_t) <= len(g) + 6:
                return True
        # Entity structural suffixes
        if norm_t in {
            "bayi", "bayii", "bayiler", "bayileri", "sirket", "sirketi", "sirketler", "sirketleri",
            "ofis", "ofisi", "ofisler", "ofisleri", "magaza", "magazasi", "magazalar", "magazalari",
            "hizmet", "hizmeti", "hizmetler", "hizmetleri", "urun", "urunu", "urunler", "urunleri",
            "nokta", "noktasi", "noktalar", "noktalari", "atolye", "atolyesi", "atolyeler", "atolyeleri"
        }:
            return True
        return False

    @classmethod
    def extract_semantic_tokens(cls, text: str) -> List[str]:
        """Extracts significant semantic concept tokens from text."""
        norm = normalize_turkish(text)
        tokens = [t for t in norm.split() if len(t) > 2 and t not in cls.STOPWORDS]
        return tokens

    @classmethod
    def create_dynamic_profile(cls, raw_query: str) -> CategoryProfile:
        """
        Dynamically constructs a CategoryProfile on-the-fly for any arbitrary unseen category
        (e.g. 'Solar Panel Installers', 'Endüstriyel CNC İmalatı', 'Soğuk Hava Depoları').
        Guarantees that generic single tokens are suppressed while full phrases are preserved.
        """
        clean_text = cls.clean_query_text(raw_query)
        norm_text = normalize_turkish(clean_text)
        tokens = cls.extract_semantic_tokens(clean_text)

        slug = norm_text.replace(" ", "-")
        canonical_id = f"dynamic_{norm_text.replace(' ', '_')[:32]}"

        # Always preserve full-phrase search term
        search_terms = [clean_text]
        for t in tokens:
            if not cls.is_generic_single_token(t) and t not in search_terms:
                search_terms.append(t)

        # Always preserve full-phrase directory slug
        directory_slugs = [slug]
        for t in tokens:
            if not cls.is_generic_single_token(t):
                t_slug = t.replace(" ", "-")
                if t_slug not in directory_slugs:
                    directory_slugs.append(t_slug)

        # Semantic concepts: keep non-generic tokens and full phrase
        non_generic_tokens = [t for t in tokens if not cls.is_generic_single_token(t)]
        positive_concepts = non_generic_tokens + [norm_text] if non_generic_tokens else [norm_text]

        logger.info(f"[INTENT_RESOLVER] Generated dynamic CategoryProfile for unseen category: '{raw_query}' (id: {canonical_id})")

        return CategoryProfile(
            canonical_id=canonical_id,
            display_name=clean_text.title(),
            semantic_description=f"Dynamically generated semantic profile for '{clean_text}'",
            profile_version="dynamic_1.0",
            is_dynamic=True,
            positive_concepts=positive_concepts,
            negative_concepts=[],
            search_terms=search_terms[:6],
            directory_slugs=directory_slugs[:5],
            osm_amenities=[],
            osm_shops=[],
            mutually_exclusive_categories=[],
            related_categories=[]
        )

    @classmethod
    def resolve_intent(cls, raw_query: str) -> SearchIntent:
        """
        Resolves raw business category query into a structured SearchIntent with full CategoryProfile.
        """
        if not raw_query or not raw_query.strip():
            raise ValueError("Business category query cannot be empty")

        clean_text = cls.clean_query_text(raw_query)
        norm_text = normalize_turkish(clean_text)

        # 1. Try matching with the Relational Taxonomy
        matched_node = TaxonomyRegistry.find_node_by_alias_or_concept(clean_text)

        if matched_node:
            profile = TaxonomyRegistry.build_profile_from_node(matched_node)
            logger.info(f"[INTENT_RESOLVER] Resolved '{raw_query}' to taxonomy category: '{profile.canonical_id}'")
        else:
            # 2. Dynamic Semantic Fallback for unseen category
            profile = cls.create_dynamic_profile(raw_query)

        return SearchIntent(
            raw_query=raw_query.strip(),
            normalized_query=norm_text,
            canonical_category_id=profile.canonical_id,
            category_profile=profile,
            location_required=True,
            intent_type="business_discovery"
        )
