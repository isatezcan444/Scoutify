"""
Business Discovery Engine V2 Test Suite:
Validates Multi-Family Query Planning, Subdivisions, Coverage Engine,
Entity Graph Merging with Provenance, and Golden Dataset Scenarios.
"""
import pytest
from typing import Dict, Any, List

from backend.app.schemas.intelligence import (
    QueryFamily,
    CategoryMatchClassification,
    QualificationState,
    RawBusinessCandidate,
    CandidateEntity,
    CategoryProfile
)
from backend.app.data.turkey_subdivisions import get_subdivisions_for_district
from backend.app.services.taxonomy_registry import TaxonomyRegistry
from backend.app.services.intent_resolver import IntentResolver
from backend.app.services.search_planner import SearchPlanner
from backend.app.services.coverage_engine import CoverageEngine
from backend.app.services.entity_graph_merger import EntityGraphMerger
from backend.app.services.category_relevance_engine import CategoryRelevanceEngine
from backend.app.services.business_quality_engine import BusinessQualityEngine


class TestSubdivisionsAndQueryFamilies:
    """Test data-driven subdivision mappings and 5 query families."""

    def test_atasehir_subdivisions_present(self):
        subs = get_subdivisions_for_district("İstanbul", "Ataşehir")
        assert len(subs) >= 5
        assert "Barbaros" in subs
        assert "İçerenköy" in subs
        assert "Küçükbakkalköy" in subs

    def test_umraniye_subdivisions_present(self):
        subs = get_subdivisions_for_district("İstanbul", "Ümraniye")
        assert len(subs) >= 5
        assert "Dudullu" in subs
        assert "Modoko" in subs
        assert "Atakent" in subs

    def test_search_planner_generates_all_five_query_families(self):
        intent = IntentResolver.resolve_intent("Diş Klinikleri & Ağız Sağlığı")
        plan = SearchPlanner.create_plan(intent, "İstanbul", ["Ataşehir"], max_results=30)
        
        families = {q.query_family for q in plan.provider_queries}
        assert QueryFamily.EXACT_INTENT in families
        assert QueryFamily.BUSINESS_TERMINOLOGY in families
        assert QueryFamily.PROVIDER_TAXONOMY in families
        assert QueryFamily.LOCAL_SUBDIVISION in families
        assert QueryFamily.COMMERCIAL_INTENT in families

        subdivision_queries = [q for q in plan.provider_queries if q.query_family == QueryFamily.LOCAL_SUBDIVISION]
        assert len(subdivision_queries) >= 5
        assert any("Barbaros" in q.query_text for q in subdivision_queries)


class TestCoverageEngineAndDiminishingReturns:
    """Test discovery yield rate and diminishing returns calculation."""

    def test_coverage_engine_records_rounds_and_yield(self):
        intent = IntentResolver.resolve_intent("Mobilya Mağazaları")
        plan = SearchPlanner.create_plan(intent, "İstanbul", ["Ümraniye"], max_results=30)
        coverage = CoverageEngine(plan)

        # Round 1: High yield
        m1 = coverage.record_round(
            round_number=1,
            query_family=QueryFamily.EXACT_INTENT,
            queries_executed=4,
            pages_visited=4,
            raw_candidates_found=50,
            new_candidates_added=40,
            duplicate_candidates=10,
            rejections_count=0,
            subdivisions_in_round=["Modoko"]
        )
        assert m1.discovery_yield_rate == 0.8
        assert coverage.should_terminate_early(1, target_limit=0) is False

        # Round 2: Moderate yield
        m2 = coverage.record_round(
            round_number=2,
            query_family=QueryFamily.BUSINESS_TERMINOLOGY,
            queries_executed=3,
            pages_visited=3,
            raw_candidates_found=30,
            new_candidates_added=10,
            duplicate_candidates=20,
            rejections_count=0,
            subdivisions_in_round=["Dudullu"]
        )
        assert m2.discovery_yield_rate == 0.333

        # Round 3 & 4: Zero new candidates -> Must trigger diminishing returns early termination
        coverage.record_round(3, QueryFamily.PROVIDER_TAXONOMY, 2, 2, 20, 0, 20, 0, [])
        coverage.record_round(4, QueryFamily.LOCAL_SUBDIVISION, 2, 2, 10, 0, 10, 0, ["Atakent"])

        assert coverage.should_terminate_early(4, target_limit=0) is True
        report = coverage.build_report()
        assert report.total_rounds == 4
        assert report.diminishing_returns_reached is True


class TestEntityGraphMergerAndProvenance:
    """Test cross-provider entity fusion and multi-source corroboration."""

    def test_multi_provider_fusion_boosts_confidence(self):
        merger = EntityGraphMerger()

        # Candidate from Directory
        cand_dir = RawBusinessCandidate(
            candidate_id="cand_dir_1",
            provider="directory",
            provider_query="diş-klinikleri in Ataşehir",
            query_family=QueryFamily.PROVIDER_TAXONOMY,
            query_id="q_1",
            raw_name="7dent Ağız ve Diş Sağlığı Polikliniği",
            clean_name="7dent Ağız ve Diş Sağlığı Polikliniği",
            raw_category="Diş Klinikleri",
            raw_address="Barbaros Mah. Ataşehir/İstanbul",
            raw_phone="02165000000"
        )
        phone_data = {"e164": "+902165000000", "is_mobile": False, "is_whatsapp_eligible": False}

        entity, is_new = merger.merge_candidate(cand_dir, phone_data, "Ataşehir", "İstanbul")
        assert is_new is True
        assert len(entity.provenance_list) == 1
        assert entity.discovery_confidence == 0.5

        # Same clinic found from OSM in local subdivision round
        cand_osm = RawBusinessCandidate(
            candidate_id="cand_osm_1",
            provider="osm",
            provider_query="diş kliniği Barbaros Ataşehir",
            query_family=QueryFamily.LOCAL_SUBDIVISION,
            query_id="q_2",
            raw_name="7Dent Dental Clinic",
            clean_name="7dent",
            raw_category="dentist",
            raw_address="Barbaros Mah. Mor Sümbül Sok. No:1 Ataşehir/İstanbul",
            raw_phone="02165000000",
            raw_website="https://7dent.com.tr"
        )

        merged_entity, is_new_2 = merger.merge_candidate(cand_osm, phone_data, "Ataşehir", "İstanbul")
        assert is_new_2 is False
        assert len(merged_entity.provenance_list) == 2
        # Corroboration across 2 distinct providers increases confidence
        assert merged_entity.discovery_confidence >= 0.8
        assert merged_entity.website == "https://7dent.com.tr"


class TestGoldenDatasetScenarios:
    """Golden Dataset Tests (GD-1, GD-2, GD-3, GD-4)."""

    def test_gd1_dental_atasehir(self):
        """GD-1: Dental in Ataşehir must qualify real clinics and reject unrelated categories."""
        intent = IntentResolver.resolve_intent("Diş Klinikleri & Ağız Sağlığı")
        profile = intent.category_profile

        # Real clinic (7dent)
        clinic = RawBusinessCandidate(
            candidate_id="gd1_c1",
            provider="directory",
            provider_query="diş in Ataşehir",
            raw_name="7dent Ağız ve Diş Sağlığı Polikliniği",
            clean_name="7dent",
            raw_category="Diş Klinikleri",
            raw_address="Barbaros Mah. Ataşehir/İstanbul",
            raw_phone="02165000000"
        )
        assessment = CategoryRelevanceEngine.evaluate(profile, clinic)
        assert assessment.classification == CategoryMatchClassification.MATCH
        assert assessment.score >= 0.7

    def test_gd2_furniture_umraniye_rejects_pet_shop_and_bakery(self):
        """GD-2: Furniture in Ümraniye must strictly reject Atakent Pet Shop and Merry Dolci Pasta Dükkanı."""
        intent = IntentResolver.resolve_intent("Mobilya Mağazaları & İmalatçıları")
        profile = intent.category_profile

        # Contamination candidate 1: Pet shop
        pet = RawBusinessCandidate(
            candidate_id="gd2_pet",
            provider="directory",
            provider_query="mobilya in Ümraniye",
            raw_name="Atakent Pet Shop",
            clean_name="Atakent Pet Shop",
            raw_category="Pet Shop",
            raw_address="Atakent Mah. Ümraniye/İstanbul",
            raw_phone="02164000000"
        )
        pet_assessment = CategoryRelevanceEngine.evaluate(profile, pet)
        assert pet_assessment.classification == CategoryMatchClassification.MISMATCH
        assert pet_assessment.score == 0.0

        # Contamination candidate 2: Bakery / Pastane
        bakery = RawBusinessCandidate(
            candidate_id="gd2_bakery",
            provider="directory",
            provider_query="mobilya in Ümraniye",
            raw_name="Merry Dolci Tasarım Pasta Dükkanı",
            clean_name="Merry Dolci Tasarım Pasta Dükkanı",
            raw_category="Pastane",
            raw_address="Ihlamurkuyu Mah. Ümraniye/İstanbul",
            raw_phone="02163000000"
        )
        bakery_assessment = CategoryRelevanceEngine.evaluate(profile, bakery)
        assert bakery_assessment.classification == CategoryMatchClassification.MISMATCH
        assert bakery_assessment.score == 0.0

    def test_gd4_dynamic_unseen_category(self):
        """GD-4: Unseen category without code modification creates a valid 5-family plan."""
        intent = IntentResolver.resolve_intent("Industrial CNC Machine Manufacturers & Metalworking")
        assert intent.category_profile.is_dynamic is True
        plan = SearchPlanner.create_plan(intent, "İstanbul", ["Ümraniye"], max_results=30)
        assert len(plan.provider_queries) >= 10
        families = {q.query_family for q in plan.provider_queries}
        assert QueryFamily.EXACT_INTENT in families
        assert QueryFamily.LOCAL_SUBDIVISION in families


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
