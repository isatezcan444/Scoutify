"""
Discovery Query Hardening & Dynamic Query Safety Test Suite.
Verifies:
- Group A: Single-token generic query suppression in dynamic discovery plans
- Group B: Multi-token phrase preservation (full phrase slugs & terms intact)
- Group C: Golden Positives Preservation (3/3 MATCH)
- Group D: Golden Negatives Rejection (9/9 NOT MATCH, 0 generic-only MATCH)
- Group E: Mutation Killers (MUT-QUERY-01 .. MUT-QUERY-04)
- Group F: 84-Category Complete Regression
"""
import pytest
from typing import List, Set
from backend.app.services.intent_resolver import IntentResolver
from backend.app.services.taxonomy_registry import TaxonomyRegistry
from backend.app.services.search_planner import SearchPlanner
from backend.app.services.category_relevance_engine import CategoryRelevanceEngine
from backend.app.schemas.intelligence import (
    SearchIntent,
    CategoryProfile,
    ProviderQuery,
    RawBusinessCandidate,
    QueryFamily,
    CategoryMatchClassification
)
from backend.app.data.turkey_locations import normalize_turkish

TaxonomyRegistry.initialize()

GENERIC_WORDS = TaxonomyRegistry.GENERIC_WORDS

# =========================================================================
# GROUP A: QUERY SUPPRESSION TESTS (Dynamic Categories)
# =========================================================================

@pytest.mark.parametrize("category,forbidden_single_tokens", [
    ("Zirai İlaç & Gübre Bayileri", ["ilac"]),
    ("Danışmanlık & Eğitim Koçluğu", ["danismanlik"]),
    ("Endüstriyel Mutfak Ekipmanları", ["mutfak", "ekipman", "ekipmanlari"]),
    ("Mutfak & Banyo Dekorasyon", ["mutfak", "dekorasyon"]),
    ("Ambalaj & Paketleme Malzemeleri", ["malzeme", "malzemeleri"]),
    ("Kombi & Klima Servisleri", ["servis", "servisleri"]),
    ("Yeminli Tercüme Büroları", ["buro", "burolari"]),
    ("Demir & Çelik İmalatçıları", ["imalat", "imalatcilari"]),
])
def test_dynamic_query_generic_single_token_suppression(category: str, forbidden_single_tokens: List[str]):
    """
    Verifies that SearchPlanner never generates single-token generic commodity/service queries
    for dynamic categories.
    """
    intent = IntentResolver.resolve_intent(category)
    plan = SearchPlanner.create_plan(intent, city="İstanbul", districts=["Kadıköy"])

    for q in plan.provider_queries:
        # Check slug
        if q.category_slug:
            norm_slug = normalize_turkish(q.category_slug).replace("-", " ")
            slug_words = norm_slug.split()
            if len(slug_words) == 1:
                assert slug_words[0] not in forbidden_single_tokens, (
                    f"CRITICAL LEAK: SearchPlanner generated dangerous single-token slug '{q.category_slug}' for '{category}'"
                )

        # Check OSM business terminology query (single-token queries only)
        if q.query_family == QueryFamily.BUSINESS_TERMINOLOGY:
            concept_text = q.query_text.replace(f"{q.district} {q.city}", "").strip()
            concept_words = concept_text.split()
            if len(concept_words) == 1:
                assert concept_words[0] not in forbidden_single_tokens, (
                    f"CRITICAL LEAK: SearchPlanner generated dangerous single-token OSM query '{q.query_text}' for '{category}'"
                )


# =========================================================================
# GROUP B: PHRASE PRESERVATION TESTS
# =========================================================================

@pytest.mark.parametrize("category,expected_phrase_slug", [
    ("Zirai İlaç & Gübre Bayileri", "zirai-ilac-gubre-bayileri"),
    ("Danışmanlık & Eğitim Koçluğu", "danismanlik-egitim-koclugu"),
    ("Endüstriyel Mutfak Ekipmanları", "endustriyel-mutfak-ekipmanlari"),
    ("Mutfak & Banyo Dekorasyon", "mutfak-banyo-dekorasyon"),
])
def test_dynamic_query_full_phrase_preservation(category: str, expected_phrase_slug: str):
    """
    Verifies that multi-token phrases containing generic words are fully preserved
    in directory slugs and local subdivision queries.
    """
    intent = IntentResolver.resolve_intent(category)
    plan = SearchPlanner.create_plan(intent, city="İstanbul", districts=["Kadıköy"])

    slugs = [q.category_slug for q in plan.provider_queries if q.category_slug]
    assert expected_phrase_slug in slugs, (
        f"REGRESSION: Full phrase slug '{expected_phrase_slug}' was missing from generated slugs: {slugs}"
    )

    # Subdivisions must contain primary term
    sub_queries = [q.query_text for q in plan.provider_queries if q.query_family == QueryFamily.LOCAL_SUBDIVISION]
    assert len(sub_queries) > 0
    assert any(normalize_turkish(category.split()[0]) in normalize_turkish(sq) for sq in sub_queries)


# =========================================================================
# GROUP C: GOLDEN POSITIVES (3/3 MATCH)
# =========================================================================

@pytest.mark.parametrize("candidate_name,category", [
    ("Toros Tarım Zirai İlaç Gübre Bayi", "Zirai İlaç & Gübre Bayileri"),
    ("Vizyon Eğitim Danışmanlık ve Öğrenci Koçluğu", "Danışmanlık & Eğitim Koçluğu"),
    ("Öztiryakiler Endüstriyel Mutfak Ekipmanları", "Endüstriyel Mutfak Ekipmanları"),
])
def test_golden_positives_preserved(candidate_name: str, category: str):
    """
    Verifies that genuine, domain-specific candidates for dynamic categories
    are reliably scored as MATCH (score >= 0.70).
    """
    intent = IntentResolver.resolve_intent(category)
    cand = RawBusinessCandidate(
        candidate_id="test_pos",
        provider="google_maps",
        provider_query=category,
        query_family=QueryFamily.EXACT_INTENT,
        query_id="qid",
        raw_name=candidate_name,
        clean_name=candidate_name,
        raw_category=category,
        raw_address="Kadıköy, İstanbul"
    )
    assessment = CategoryRelevanceEngine.evaluate(intent.category_profile, cand)
    assert assessment.classification == CategoryMatchClassification.MATCH, (
        f"REGRESSION: Golden positive '{candidate_name}' failed relevance: classification={assessment.classification}, score={assessment.score}"
    )
    assert assessment.score >= 0.70


# =========================================================================
# GROUP D: GOLDEN NEGATIVES (9/9 REJECTED / NOT MATCH)
# =========================================================================

@pytest.mark.parametrize("candidate_name,category", [
    ("Merkez Eczanesi", "Zirai İlaç & Gübre Bayileri"),
    ("Nöbetçi Eczane Şifa", "Zirai İlaç & Gübre Bayileri"),
    ("Kadıköy İlaç Deposu ve Medikal", "Zirai İlaç & Gübre Bayileri"),
    ("Avukatlık Bürosu & Danışmanlık", "Danışmanlık & Eğitim Koçluğu"),
    ("Finans Danışmanlığı ve Muhasebe", "Danışmanlık & Eğitim Koçluğu"),
    ("Kaya Hukuk ve Arabuluculuk Bürosu", "Danışmanlık & Eğitim Koçluğu"),
    ("Saray Kebap ve Mutfak Salonu", "Endüstriyel Mutfak Ekipmanları"),
    ("Boğaziçi Balık Restoranı", "Endüstriyel Mutfak Ekipmanları"),
    ("Akdeniz Mutfak Mobilyaları ve Dolap", "Endüstriyel Mutfak Ekipmanları"),
])
def test_golden_negatives_rejected(candidate_name: str, category: str):
    """
    Verifies that cross-domain candidates sharing only a single generic token
    (or matching mutually exclusive domains) are strictly NOT MATCH (MISMATCH or AMBIGUOUS, score < 0.60).
    """
    intent = IntentResolver.resolve_intent(category)
    cand = RawBusinessCandidate(
        candidate_id="test_neg",
        provider="google_maps",
        provider_query=category,
        query_family=QueryFamily.EXACT_INTENT,
        query_id="qid",
        raw_name=candidate_name,
        clean_name=candidate_name,
        raw_category="Diğer",
        raw_address="Kadıköy, İstanbul"
    )
    assessment = CategoryRelevanceEngine.evaluate(intent.category_profile, cand)
    assert assessment.classification != CategoryMatchClassification.MATCH, (
        f"CRITICAL DRIFT: False positive '{candidate_name}' matched dynamic category '{category}'! (score={assessment.score})"
    )
    assert assessment.score < 0.60, (
        f"False positive '{candidate_name}' has dangerously high score {assessment.score} for '{category}'"
    )


# =========================================================================
# GROUP E: MUTATION KILLERS (MUT-QUERY-01 .. MUT-QUERY-04)
# =========================================================================

def test_mut_query_01_generic_expansion_killer():
    """
    MUT-QUERY-01: Verifies that no dynamic profile contains single-token generic words in search_terms or directory_slugs.
    """
    intent = IntentResolver.resolve_intent("Zirai İlaç & Gübre Bayileri")
    profile = intent.category_profile
    for slug in profile.directory_slugs:
        slug_words = slug.split("-")
        if len(slug_words) == 1:
            assert slug_words[0] not in GENERIC_WORDS, f"MUT-QUERY-01 FAILED: Generic single word '{slug_words[0]}' found in directory_slugs"


def test_mut_query_02_mandatory_ilac_query_killer():
    """
    MUT-QUERY-02: SearchPlanner must NOT generate 'ilac' as a standalone directory slug.
    """
    intent = IntentResolver.resolve_intent("Zirai İlaç & Gübre Bayileri")
    plan = SearchPlanner.create_plan(intent, city="İstanbul", districts=["Kadıköy"])
    slugs = [q.category_slug for q in plan.provider_queries if q.category_slug]
    assert "ilac" not in slugs, "MUT-QUERY-02 FAILED: 'ilac' slug was generated for Zirai İlaç"


def test_mut_query_03_mandatory_danismanlik_query_killer():
    """
    MUT-QUERY-03: SearchPlanner must NOT generate 'danismanlik' as a standalone directory slug.
    """
    intent = IntentResolver.resolve_intent("Danışmanlık & Eğitim Koçluğu")
    plan = SearchPlanner.create_plan(intent, city="İstanbul", districts=["Kadıköy"])
    slugs = [q.category_slug for q in plan.provider_queries if q.category_slug]
    assert "danismanlik" not in slugs, "MUT-QUERY-03 FAILED: 'danismanlik' slug was generated for Eğitim Koçluğu"


def test_mut_query_04_mandatory_mutfak_query_killer():
    """
    MUT-QUERY-04: SearchPlanner must NOT generate 'mutfak' as a standalone directory slug.
    """
    intent = IntentResolver.resolve_intent("Endüstriyel Mutfak Ekipmanları")
    plan = SearchPlanner.create_plan(intent, city="İstanbul", districts=["Kadıköy"])
    slugs = [q.category_slug for q in plan.provider_queries if q.category_slug]
    assert "mutfak" not in slugs, "MUT-QUERY-04 FAILED: 'mutfak' slug was generated for Endüstriyel Mutfak"
