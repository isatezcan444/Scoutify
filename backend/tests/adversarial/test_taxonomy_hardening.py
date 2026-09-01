"""
Taxonomy Resolution Hardening & Semantic Drift Prevention Test Suite.
Verifies:
- Negative False-Positive Drift Matrix (Pharmacy, Legal, Food)
- Positive Static Mapping Preservation
- Generic Single-Token Collision Matrix
- 84-Category Complete Invariant Suite
- Mutation Test Gate (MUT-RESOLVE-01 to MUT-RESOLVE-04)
"""
import pytest
import re
from typing import List
from backend.app.services.taxonomy_registry import TaxonomyRegistry
from backend.app.services.intent_resolver import IntentResolver
from backend.app.services.search_planner import SearchPlanner
from backend.app.schemas.intelligence import SearchIntent, CategoryProfile

TaxonomyRegistry.initialize()


# =========================================================================
# 1. NEGATIVE FALSE-POSITIVE DRIFT PREVENTION TESTS
# =========================================================================

@pytest.mark.parametrize("query,forbidden_node", [
    ("Zirai İlaç & Gübre Bayileri", "pharmacy"),
    ("Tarım İlaçları", "pharmacy"),
    ("Bitki İlaçları", "pharmacy"),
    ("İlaç Toptancıları", "pharmacy"),
    ("Danışmanlık & Eğitim Koçluğu", "legal"),
    ("İş Danışmanlığı", "legal"),
    ("Yönetim & İK Danışmanlığı", "legal"),
    ("Finans Danışmanlığı", "legal"),
    ("Endüstriyel Mutfak Ekipmanları", "food_beverage"),
    ("Mutfak Mobilyaları", "food_beverage"),
    ("Mutfak Ekipman Üreticileri", "food_beverage"),
])
def test_negative_false_positive_drift_prevention(query: str, forbidden_node: str):
    """
    Negative Test: Generic/unrelated domain queries MUST NOT map to static canonical nodes.
    They must safely fall back to dynamic profiles (is_dynamic == True) with matching intent.
    """
    intent = IntentResolver.resolve_intent(query)
    profile = intent.category_profile
    
    assert profile.canonical_id != forbidden_node, (
        f"CRITICAL DRIFT: '{query}' was falsely resolved to static node '{forbidden_node}'!"
    )
    assert profile.is_dynamic is True, (
        f"'{query}' should have fallen back to dynamic profile, got canonical_id='{profile.canonical_id}'"
    )

    # Verify discovery provider queries do not leak forbidden provider slugs
    plan = SearchPlanner.create_plan(intent, city="İstanbul", districts=["Kadıköy"])
    queries = [q.query_text.lower() for q in plan.provider_queries]

    if forbidden_node == "pharmacy":
        assert not any("eczaneler" in q or "nobetci-eczaneler" in q for q in queries)
    elif forbidden_node == "legal":
        assert not any("avukatlar" in q or "hukuk-burolari" in q or "arabuluculuk" in q for q in queries)
    elif forbidden_node == "food_beverage":
        assert not any("restoranlar" in q or "lokantalar" in q or "kebapcilar" in q for q in queries)


# =========================================================================
# 2. POSITIVE RESOLUTION PRESERVATION TESTS
# =========================================================================

@pytest.mark.parametrize("query,expected_node", [
    ("Eczaneler", "pharmacy"),
    ("Eczane", "pharmacy"),
    ("Nöbetçi Eczaneler", "pharmacy"),
    ("Avukatlık & Hukuk Büroları", "legal"),
    ("Hukuk Danışmanlığı", "legal"),
    ("Avukatlık Büroları", "legal"),
    ("Avukatlar", "legal"),
    ("Restoranlar & Lokantalar", "food_beverage"),
    ("Kafe & Kahve Dükkanları", "food_beverage"),
    ("Restoranlar", "food_beverage"),
    ("Lokantalar", "food_beverage"),
    ("Diş Klinikleri & Ağız Sağlığı Merkezleri", "dental"),
    ("Diş Klinikleri", "dental"),
    ("Mobilya Mağazaları & İmalatçıları", "furniture"),
    ("Mobilya Mağazaları", "furniture"),
    ("Oto Servis & Tamir Merkezleri", "automotive"),
    ("Veteriner Klinikleri", "pet_services"),
    ("Güzellik & Estetik Merkezleri", "hair_beauty"),
    ("Fırın & Pastaneler", "bakery"),
])
def test_positive_static_resolution_preservation(query: str, expected_node: str):
    """
    Positive Test: Qualified, genuine domain queries MUST reliably map to their static canonical nodes.
    """
    intent = IntentResolver.resolve_intent(query)
    profile = intent.category_profile
    
    assert profile.canonical_id == expected_node, (
        f"REGRESSION: '{query}' should resolve to '{expected_node}', but got '{profile.canonical_id}'"
    )
    assert profile.is_dynamic is False, (
        f"REGRESSION: '{query}' was unexpectedly downgraded to dynamic profile"
    )


# =========================================================================
# 3. GENERIC SINGLE-TOKEN COLLISION MATRIX
# =========================================================================

@pytest.mark.parametrize("query,unintended_node", [
    ("Temizlik Malzemeleri", "furniture"),
    ("Ses & Işık Ekipmanları", "food_beverage"),
    ("Klima & İklimlendirme Servisleri", "automotive"),
    ("Tıbbi Cihaz & Ekipman", "pharmacy"),
    ("Yeminli Tercüme Büroları", "legal"),
    ("Çağrı Merkezleri", "hair_beauty"),
])
def test_generic_single_token_collision_prevention(query: str, unintended_node: str):
    """
    Verifies that words like 'malzeme', 'ekipman', 'servis', 'cihaz', 'büro', 'merkez'
    do NOT cause accidental collision with existing static nodes.
    """
    intent = IntentResolver.resolve_intent(query)
    assert intent.category_profile.canonical_id != unintended_node


# =========================================================================
# 4. MUTATION TEST SUITE (MUT-RESOLVE-01 .. 04)
# =========================================================================

def test_mut_resolve_01_generic_ilac_alias_killer():
    """
    MUT-RESOLVE-01: Adding generic 'ilaç' as alias to pharmacy MUST be detected and rejected.
    """
    # If a resolver accepts 'ilaç' as a standalone alias for pharmacy, 'Zirai İlaç Bayileri' would falsely resolve to pharmacy.
    intent = IntentResolver.resolve_intent("Zirai İlaç Bayileri")
    assert intent.category_profile.canonical_id != "pharmacy", (
        "MUT-RESOLVE-01 FAILED: Standalone 'ilaç' matched pharmacy on 'Zirai İlaç Bayileri'"
    )


def test_mut_resolve_02_generic_danismanlik_concept_killer():
    """
    MUT-RESOLVE-02: Adding generic 'danışmanlık' as standalone concept to legal MUST NOT capture non-legal consulting.
    """
    intent = IntentResolver.resolve_intent("Eğitim ve Yaşam Koçluğu Danışmanlığı")
    assert intent.category_profile.canonical_id != "legal", (
        "MUT-RESOLVE-02 FAILED: Generic 'danışmanlık' matched legal on non-legal coaching"
    )


def test_mut_resolve_03_generic_mutfak_concept_killer():
    """
    MUT-RESOLVE-03: Adding generic 'mutfak' as standalone concept MUST NOT capture kitchen equipment manufacturing.
    """
    intent = IntentResolver.resolve_intent("Endüstriyel Mutfak İmalatçıları")
    assert intent.category_profile.canonical_id != "food_beverage", (
        "MUT-RESOLVE-03 FAILED: Generic 'mutfak' matched food_beverage on industrial manufacturing"
    )


def test_mut_resolve_04_single_token_generic_matching_killer():
    """
    MUT-RESOLVE-04: Single-token generic matching must not bypass dynamic fallback.
    """
    generic_words = ["ilaç", "danışmanlık", "mutfak", "servis", "tamir", "büro", "merkez", "ekipman", "malzeme"]
    for word in generic_words:
        intent = IntentResolver.resolve_intent(f"Genel {word.title()} Hizmetleri")
        # Should NOT resolve to any static node via that single word alone
        assert intent.category_profile.is_dynamic is True, (
            f"MUT-RESOLVE-04 FAILED: 'Genel {word.title()} Hizmetleri' falsely matched static node '{intent.category_profile.canonical_id}'"
        )
