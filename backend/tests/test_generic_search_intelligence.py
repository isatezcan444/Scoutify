"""
Generic Search Intelligence Test Suite:
Validates relational taxonomy, dynamic semantic fallback, provider adapters,
multi-signal category relevance gating, and cross-category isolation.
"""
import pytest
from typing import Dict, Any, List

from backend.app.schemas.intelligence import (
    RelationshipType,
    CategoryMatchClassification,
    QualificationState,
    RawBusinessCandidate,
    CategoryProfile
)
from backend.app.services.taxonomy_registry import TaxonomyRegistry
from backend.app.services.intent_resolver import IntentResolver
from backend.app.services.search_planner import SearchPlanner
from backend.app.services.category_relevance_engine import CategoryRelevanceEngine
from backend.app.services.business_quality_engine import BusinessQualityEngine


class TestRelationalTaxonomy:
    """Test relational graph structure and mutual exclusivity reasoning."""

    def test_taxonomy_initialization(self):
        TaxonomyRegistry.initialize()
        node = TaxonomyRegistry.get_node("furniture")
        assert node is not None
        assert node.display_name == "Mobilya & Dekorasyon"

    def test_mutually_exclusive_relationships(self):
        """Furniture and Pet Services / Bakery / Dental must be mutually exclusive."""
        assert TaxonomyRegistry.are_mutually_exclusive("furniture", "pet_services") is True
        assert TaxonomyRegistry.are_mutually_exclusive("furniture", "bakery") is True
        assert TaxonomyRegistry.are_mutually_exclusive("furniture", "dental") is True
        assert TaxonomyRegistry.are_mutually_exclusive("furniture", "food_beverage") is True
        assert TaxonomyRegistry.are_mutually_exclusive("dental", "restaurant") is False or TaxonomyRegistry.are_mutually_exclusive("dental", "food_beverage") is True

    def test_find_node_by_turkish_alias(self):
        """Must resolve inflected Turkish search terms to canonical nodes."""
        node = TaxonomyRegistry.find_node_by_alias_or_concept("Mobilya Mağazaları & İmalatçıları")
        assert node is not None
        assert node.id == "furniture"

        node_dental = TaxonomyRegistry.find_node_by_alias_or_concept("Diş Klinikleri & Ağız Sağlığı")
        assert node_dental is not None
        assert node_dental.id == "dental"

        node_pet = TaxonomyRegistry.find_node_by_alias_or_concept("Pet Shoplar")
        assert node_pet is not None
        assert node_pet.id == "pet_services"


class TestIntentResolverAndDynamicFallback:
    """Test resolution of known and unseen categories."""

    def test_known_category_intent_resolution(self):
        intent = IntentResolver.resolve_intent("Mobilya Mağazaları & İmalatçıları")
        assert intent.canonical_category_id == "furniture"
        assert intent.category_profile.canonical_id == "furniture"
        assert "pet_services" in intent.category_profile.mutually_exclusive_categories
        assert intent.category_profile.is_dynamic is False

    def test_unseen_arbitrary_category_dynamic_profile_generation(self):
        """An arbitrary, never-before-seen category must generate a valid dynamic CategoryProfile without code change."""
        unseen_query = "Güneş Paneli Kurulum Firmaları & Solar Enerji"
        intent = IntentResolver.resolve_intent(unseen_query)
        assert intent.category_profile.is_dynamic is True
        assert "gunes" in intent.category_profile.positive_concepts or "solar" in intent.category_profile.positive_concepts
        assert len(intent.category_profile.directory_slugs) > 0
        assert len(intent.category_profile.search_terms) > 0


class TestSearchPlanner:
    """Test generic query planning."""

    def test_search_plan_generation(self):
        intent = IntentResolver.resolve_intent("Mobilya Mağazaları")
        plan = SearchPlanner.create_plan(intent, city="İstanbul", districts=["Ümraniye"], max_results=30)
        assert plan.city == "İstanbul"
        assert plan.districts == ["Ümraniye"]
        assert len(plan.provider_queries) > 0

        # Check directory and OSM queries
        dir_queries = [q for q in plan.provider_queries if q.provider_name == "directory"]
        osm_queries = [q for q in plan.provider_queries if q.provider_name == "osm"]
        assert len(dir_queries) > 0
        assert len(osm_queries) > 0
        assert any("Ümraniye" in q.query_text for q in osm_queries)


class TestCategoryRelevanceAndHardMismatch:
    """Test multi-signal evaluation and Hard Gate Mismatch rejection."""

    def test_exact_category_match(self):
        intent = IntentResolver.resolve_intent("Mobilya Mağazaları")
        candidate = RawBusinessCandidate(
            candidate_id="test_1",
            provider="directory",
            provider_query="mobilya-magazalari in Ümraniye, İstanbul",
            raw_name="Ofis Center Büro Mobilyaları ve Tasarım Showroom",
            clean_name="Ofis Center Büro Mobilyaları",
            raw_category="Mobilya Mağazaları",
            raw_address="İmes Sanayi Sitesi, Ümraniye/İstanbul",
            raw_phone="02165000000"
        )
        assessment = CategoryRelevanceEngine.evaluate(intent.category_profile, candidate)
        assert assessment.classification == CategoryMatchClassification.MATCH
        assert assessment.score >= 0.7
        assert len(assessment.positive_evidence) > 0

    def test_permanent_regression_mobilya_vs_pet_shop_and_bakery(self):
        """
        PERMANENT REGRESSION TEST:
        Target: Mobilya Mağazaları & İmalatçıları
        Location: Ümraniye
        Candidates:
        1. 'Atakent Pet Shop' -> Must be MISMATCH (score 0.0)
        2. 'Merry Dolci Tasarım Pasta Dükkanı' -> Must be MISMATCH (score 0.0)
        """
        intent = IntentResolver.resolve_intent("Mobilya Mağazaları & İmalatçıları")
        profile = intent.category_profile

        # Candidate 1: Pet Shop
        pet_candidate = RawBusinessCandidate(
            candidate_id="test_pet",
            provider="directory",
            provider_query="mobilya in Ümraniye",
            raw_name="Atakent Pet Shop ve Akvaryum Dünyası",
            clean_name="Atakent Pet Shop",
            raw_category="Pet Shop",
            raw_address="Atakent Mah. Ümraniye/İstanbul",
            raw_phone="02164000000"
        )
        pet_assessment = CategoryRelevanceEngine.evaluate(profile, pet_candidate)
        assert pet_assessment.classification == CategoryMatchClassification.MISMATCH
        assert pet_assessment.score == 0.0
        assert "MUTUALLY_EXCLUSIVE" in pet_assessment.reason or "pet_services" in pet_assessment.reason

        # Candidate 2: Bakery / Pasta Dükkanı
        bakery_candidate = RawBusinessCandidate(
            candidate_id="test_bakery",
            provider="directory",
            provider_query="mobilya in Ümraniye",
            raw_name="Merry Dolci Tasarım Pasta Dükkanı ve Butik Pastane",
            clean_name="Merry Dolci Tasarım Pasta Dükkanı",
            raw_category="Pastane & Pasta Dükkanı",
            raw_address="Ihlamurkuyu Mah. Ümraniye/İstanbul",
            raw_phone="02163000000"
        )
        bakery_assessment = CategoryRelevanceEngine.evaluate(profile, bakery_candidate)
        assert bakery_assessment.classification == CategoryMatchClassification.MISMATCH
        assert bakery_assessment.score == 0.0


class TestCrossCategoryMatrix:
    """8 Targets x 8 Candidates Cross-Category Matrix to ensure zero contamination."""

    CATEGORIES = [
        ("Mobilya Mağazaları", "İstikbal Mobilya Showroom"),
        ("Diş Klinikleri", "Ataşehir Dental Ağız ve Diş Sağlığı"),
        ("Pet Shoplar", "Pati Dünyası Pet Shop ve Mama"),
        ("Restoranlar", "Boğaziçi Kebap ve Izgara Restoranı"),
        ("Pastaneler", "Lalezar Butik Pastane ve Fırın"),
        ("Avukatlık Büroları", "Adalet Hukuk ve Avukatlık Bürosu"),
        ("Kuaförler & Güzellik", "Paris Kuaför ve Güzellik Salonu"),
        ("Oto Servisleri", "Bosch Car Service Oto Tamir ve Bakım")
    ]

    def test_cross_category_isolation(self):
        for target_query, _ in self.CATEGORIES:
            intent = IntentResolver.resolve_intent(target_query)
            profile = intent.category_profile

            for other_query, other_biz_name in self.CATEGORIES:
                cand = RawBusinessCandidate(
                    candidate_id="matrix_test",
                    provider="directory",
                    provider_query="test",
                    raw_name=other_biz_name,
                    clean_name=other_biz_name,
                    raw_category=other_query
                )
                assessment = CategoryRelevanceEngine.evaluate(profile, cand)

                if target_query == other_query:
                    assert assessment.classification in (CategoryMatchClassification.MATCH, CategoryMatchClassification.PARTIAL_MATCH)
                    assert assessment.score >= 0.6
                else:
                    # Different categories with mutual exclusivity must be MISMATCH
                    if TaxonomyRegistry.are_mutually_exclusive(profile.canonical_id, IntentResolver.resolve_intent(other_query).canonical_category_id):
                        assert assessment.classification == CategoryMatchClassification.MISMATCH
                        assert assessment.score == 0.0


class TestBusinessQualityHardGates:
    """Test that high business quality cannot compensate for category or location mismatch."""

    def test_category_mismatch_triggers_hard_rejection(self):
        candidate = RawBusinessCandidate(
            candidate_id="cand_1",
            provider="directory",
            provider_query="test",
            raw_name="Atakent Pet Shop",
            clean_name="Atakent Pet Shop",
            raw_address="Atakent Mah. Ümraniye/İstanbul",
            raw_phone="02164000000",
            raw_website="https://atakentpetshop.com"
        )
        mismatch_assessment = CategoryRelevanceEngine.evaluate(
            IntentResolver.resolve_intent("Mobilya").category_profile,
            candidate
        )
        assert mismatch_assessment.classification == CategoryMatchClassification.MISMATCH

        phone_data = {"e164": "+902164000000", "is_mobile": False, "is_whatsapp_eligible": False}
        quality = BusinessQualityEngine.evaluate(
            candidate=candidate,
            category_assessment=mismatch_assessment,
            location_confidence_val="EXACT_DISTRICT",
            phone_data=phone_data,
            target_category_display="Mobilya & Dekorasyon"
        )
        assert quality.qualification_state == QualificationState.REJECTED
        assert quality.overall_quality_score == 0
        assert quality.is_verified is False
        assert len(quality.rejection_reasons) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
