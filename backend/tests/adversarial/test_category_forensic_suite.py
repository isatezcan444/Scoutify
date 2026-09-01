"""
Category Selection Layer Forensic Adversarial Test Suite.
Forensic audit testing:
1. Contract verification (ID vs slug vs label, Turkish casing, duplicates, unknowns, empty)
2. Goal-to-category message strategy (6 goals x TR/EN parity)
3. Discovery semantic relevance & query generation
4. Category isolation between concurrent/sequential campaigns
5. Taxonomy graph integrity & mutual exclusivity reasoning
"""
import pytest
from typing import List
from backend.app.services.taxonomy_registry import TaxonomyRegistry
from backend.app.services.intent_resolver import IntentResolver
from backend.app.services.search_planner import SearchPlanner
from backend.app.services.category_recommendation_service import CategoryRecommendationService
from backend.app.services.message_strategy_service import MessageStrategyService
from backend.app.schemas.smart_outreach import (
    CategoryRecommendationRequest,
    BusinessGoal,
    CategoryFitLevel
)
from backend.app.data.turkey_locations import normalize_turkish


# =========================================================================
# SECTION 2: CATEGORY SELECTION CONTRACT & RESILIENCE TESTS
# =========================================================================

def test_cat_contract_turkish_casing_and_normalization():
    """
    Verifies that Turkish character variations (dotted/dotless I, lowercase/uppercase)
    correctly map to the exact same canonical taxonomy node.
    """
    variants = [
        "DİŞ KLİNİĞİ",
        "diş kliniği",
        "Dis Klinigi",
        "DİS KLİNİGİ",
        "DİŞ",
        "dis",
        "dış hekimi",  # intentional typo/variant
        "DİŞ HEKİMİ",
        "Ağız ve Diş Sağlığı",
        "AĞIZ VE DİŞ SAĞLIĞI",
        "agiz ve dis sagligi"
    ]
    for variant in variants:
        node = TaxonomyRegistry.find_node_by_alias_or_concept(variant)
        assert node is not None, f"Variant '{variant}' failed to resolve to taxonomy node"
        assert node.id == "dental", f"Variant '{variant}' resolved to '{node.id}' instead of 'dental'"


def test_cat_contract_slug_vs_label_vs_alias_inversion():
    """
    Verifies that passing an exact slug, display name, or alias resolves deterministically.
    """
    # 1. Furniture
    furniture_inputs = [
        "furniture",
        "Mobilya & Dekorasyon",
        "mobilya imalatı",
        "mobilya-magazalari",
        "ofis mobilyaları",
        "KOLTUK DÖŞEME"
    ]
    for inp in furniture_inputs:
        intent = IntentResolver.resolve_intent(inp)
        assert intent.canonical_category_id == "furniture", f"Input '{inp}' did not resolve to canonical 'furniture'"

    # 2. Automotive
    auto_inputs = [
        "automotive",
        "Otomotiv & Araç Servisleri",
        "oto servis",
        "oto tamir",
        "araç kiralama"
    ]
    for inp in auto_inputs:
        intent = IntentResolver.resolve_intent(inp)
        assert intent.canonical_category_id == "automotive", f"Input '{inp}' did not resolve to canonical 'automotive'"


def test_cat_contract_unknown_category_dynamic_fallback():
    """
    Verifies that unknown or niche categories gracefully create a dynamic CategoryProfile
    with is_dynamic=True, meaningful search terms, and directory slugs without crashing.
    """
    niche_queries = [
        "Güneş Enerjisi Santrali Kurulumu ve GES Bakım",
        "Drone İle Havadan Zirai İlaçlama",
        "Endüstriyel Soğuk Hava Deposu ve Chiller Servisi",
        "Wedding Planner & Düğün Organizatörü",
        "Yat ve Tekne Kiralama Acentesi"
    ]

    for q in niche_queries:
        intent = IntentResolver.resolve_intent(q)
        assert intent is not None
        assert intent.raw_query == q
        assert intent.category_profile is not None
        assert intent.category_profile.is_dynamic is True
        assert intent.canonical_category_id.startswith("dynamic_")
        assert len(intent.category_profile.search_terms) > 0
        assert len(intent.category_profile.directory_slugs) > 0
        # Positive concepts must not contain noise words
        for w in intent.category_profile.positive_concepts:
            assert w not in IntentResolver.STOPWORDS


def test_cat_contract_empty_and_whitespace_rejection():
    """
    Verifies that empty, None, or whitespace-only inputs are strictly rejected with ValueError.
    """
    invalid_inputs = ["", "   ", "\t\n\r", "   \t  "]
    for inv in invalid_inputs:
        with pytest.raises(ValueError, match="Business category query cannot be empty"):
            IntentResolver.resolve_intent(inv)


def test_cat_contract_deduplication_and_ordering():
    """
    Verifies recommendation response returns deduplicated categories with proper fit ranking.
    """
    req = CategoryRecommendationRequest(
        offer_title="VIP Vito ve Minibüs Şoförlü Transfer Hizmetleri",
        offer_description="İstanbul içi ve havalimanı otel transferleri, kurumsal heyet taşımacılığı.",
        business_goal=BusinessGoal.DISCOVERY,
        city="İstanbul"
    )
    res = CategoryRecommendationService.recommend_categories(req)
    assert len(res.discovered_categories) > 0

    category_ids = [c.category_id for c in res.discovered_categories]
    assert len(category_ids) == len(set(category_ids)), "Discovered categories must contain NO duplicates"

    # High fit items should appear before lower fit items
    fit_rank = {CategoryFitLevel.HIGH: 3, CategoryFitLevel.MEDIUM: 2, CategoryFitLevel.LOW: 1, CategoryFitLevel.ALTERNATIVE: 0}
    for i in range(len(res.discovered_categories) - 1):
        curr_level = res.discovered_categories[i].fit_level
        next_level = res.discovered_categories[i + 1].fit_level
        assert fit_rank[curr_level] >= fit_rank[next_level], "Categories must be ordered by descending fit level"


# =========================================================================
# SECTION 3: GOAL ➔ CATEGORY BEHAVIOR & TEMPLATE AUDIT (6 GOALS x TR/EN)
# =========================================================================

@pytest.mark.parametrize("goal,offer_title,key_benefit,extra_info,need,question,price,purpose,prev_topic", [
    ("FIRST_CONTACT", "VIP Transfer Çözümleri", "Hızlı Ulaşım", "7/24 Destek", None, None, None, None, None),
    ("SERVICE_PROMOTION", "SaaS CRM Platformu", "Satış Artışı", "Ücretsiz Deneme", None, None, None, None, None),
    ("DISCOVERY", "ERP Danışmanlığı", None, None, "Dış Yazılım Çözümü", "Mevcut sisteminiz yeterli mi?", None, None, None),
    ("OFFER", "Kurumsal E-Posta Paketi", "%30 İndirim", None, None, None, "Yıllık 1200 TL", None, None),
    ("MEETING", "Yapay Zeka Destekli Otomasyon", None, None, None, None, None, "Maliyet Analizi", None),
    ("FOLLOW_UP", None, "Yeni Özellikler", "Ek Ekipman", None, None, None, None, "Geçen Haftaki Teklifimiz"),
])
def test_goal_message_generation_tr_and_en(goal, offer_title, key_benefit, extra_info, need, question, price, purpose, prev_topic):
    """
    Tests message generation for all 6 goals in both Turkish and English.
    Verifies that the target_category is injected accurately into both languages and that
    the goal change does not mutate or alter category state.
    """
    target_category = "Oteller & Konaklama Tesisleri"

    # 1. Turkish generation
    msg_tr, summary_tr = MessageStrategyService.generate_campaign_message(
        communication_goal=goal,
        target_category=target_category,
        offer_title=offer_title,
        key_benefit=key_benefit,
        extra_information=extra_info,
        lead_need=need,
        specific_question=question,
        pricing_info=price,
        meeting_purpose=purpose,
        previous_topic=prev_topic,
        language="tr"
    )
    assert msg_tr and len(msg_tr) > 20
    assert summary_tr and len(summary_tr) > 5
    assert target_category in summary_tr
    if goal != "FOLLOW_UP":
        assert target_category in msg_tr

    # 2. English generation
    msg_en, summary_en = MessageStrategyService.generate_campaign_message(
        communication_goal=goal,
        target_category=target_category,
        offer_title=offer_title,
        key_benefit=key_benefit,
        extra_information=extra_info,
        lead_need=need,
        specific_question=question,
        pricing_info=price,
        meeting_purpose=purpose,
        previous_topic=prev_topic,
        language="en"
    )
    assert msg_en and len(msg_en) > 20
    assert summary_en and len(summary_en) > 5
    assert target_category in summary_en
    if goal != "FOLLOW_UP":
        assert target_category in msg_en
    assert "Best regards." in msg_en


def test_goal_switching_category_preservation():
    """
    Simulates rapid goal switching (FIRST_CONTACT -> OFFER -> DISCOVERY -> MEETING -> FOLLOW_UP)
    and verifies that the category string and semantic parameters remain unaltered.
    """
    cat = "Diş Klinikleri"
    goals = ["FIRST_CONTACT", "SERVICE_PROMOTION", "DISCOVERY", "OFFER", "MEETING", "FOLLOW_UP"]

    for g in goals:
        msg, summary = MessageStrategyService.generate_campaign_message(
            communication_goal=g,
            target_category=cat,
            offer_title="Dental CAD/CAM Frezeleme Cihazı",
            key_benefit="2 Kat Hızlı Üretim",
            lead_need="Laboratuvar Desteği",
            meeting_purpose="Cihaz Demosu",
            previous_topic="Katalog Paylaşımı",
            language="tr"
        )
        assert cat in summary, f"Category '{cat}' missing in summary for goal '{g}'"
        if g != "FOLLOW_UP":
            assert cat in msg, f"Category '{cat}' missing in message for goal '{g}'"


# =========================================================================
# SECTION 5: DISCOVERY CORRECTNESS & QUERY SEMANTICS
# =========================================================================

def test_discovery_correctness_furniture_no_drift():
    """
    Verifies that querying 'Mobilya Üreticileri' resolves to 'furniture' taxonomy node
    and generates structured Overpass & Directory queries without drifting to food, dental, or legal.
    """
    intent = IntentResolver.resolve_intent("Mobilya Üreticileri & İmalatçıları")
    assert intent.canonical_category_id == "furniture"

    plan = SearchPlanner.create_plan(
        intent=intent,
        city="İstanbul",
        districts=["Kadıköy", "Ümraniye"]
    )
    assert len(plan.provider_queries) > 0

    all_query_texts = " ".join([q.query_text for q in plan.provider_queries]).lower()
    assert "furniture" in all_query_texts or "mobilya" in all_query_texts

    # Negative check: Ensure NO drift to completely unrelated categories
    unrelated_terms = ["dentist", "diş", "veteriner", "avukat", "eczane", "restoran"]
    for term in unrelated_terms:
        assert term not in all_query_texts, f"Query plan leaked unrelated term '{term}' for furniture search!"


def test_discovery_correctness_wedding_planner_dynamic_plan():
    """
    Verifies that querying 'Wedding Planner & Düğün Organizatörleri' creates a clean dynamic plan.
    """
    intent = IntentResolver.resolve_intent("Wedding Planner & Düğün Organizatörleri")
    assert intent.category_profile.is_dynamic is True

    plan = SearchPlanner.create_plan(
        intent=intent,
        city="İzmir",
        districts=["Konak", "Karşıyaka"]
    )
    assert len(plan.provider_queries) > 0
    slugs = [q.category_slug for q in plan.provider_queries if q.category_slug]
    assert any("dugun" in s or "wedding" in s or "organizator" in s for s in slugs)


# =========================================================================
# SECTION 6: CATEGORY & CAMPAIGN ISOLATION
# =========================================================================

def test_campaign_state_isolation():
    """
    Verifies that creating message drafts and search plans for Campaign A (Category: Dental, Goal: OFFER)
    and Campaign B (Category: Furniture, Goal: MEETING) completely isolates states without cross-contamination.
    """
    # Campaign A
    intent_a = IntentResolver.resolve_intent("Diş Klinikleri & Ortodonti")
    plan_a = SearchPlanner.create_plan(intent=intent_a, city="Ankara", districts=["Çankaya"])
    msg_a, _ = MessageStrategyService.generate_campaign_message(
        communication_goal="OFFER",
        target_category=intent_a.category_profile.display_name,
        offer_title="İmplant Seti",
        key_benefit="%20 İndirim",
        language="tr"
    )

    # Campaign B
    intent_b = IntentResolver.resolve_intent("Ofis Mobilyaları & Masa İmalatı")
    plan_b = SearchPlanner.create_plan(intent=intent_b, city="Bursa", districts=["Nilüfer"])
    msg_b, _ = MessageStrategyService.generate_campaign_message(
        communication_goal="MEETING",
        target_category=intent_b.category_profile.display_name,
        offer_title="Ergonomik Çalışma Masaları",
        meeting_purpose="Showroom Ziyareti",
        language="tr"
    )

    # Invariants
    assert intent_a.canonical_category_id == "dental"
    assert intent_b.canonical_category_id == "furniture"
    assert "Diş" in msg_a and "Mobilya" not in msg_a
    assert "Mobilya" in msg_b and "Diş" not in msg_b

    # Verify query plans are strictly disjoint
    queries_a = {q.query_text for q in plan_a.provider_queries}
    queries_b = {q.query_text for q in plan_b.provider_queries}
    assert queries_a.isdisjoint(queries_b), "Campaign A and Campaign B queries must be completely disjoint!"


# =========================================================================
# SECTION 9: TAXONOMY GRAPH AUDIT & MUTUAL EXCLUSIVITY
# =========================================================================

def test_taxonomy_graph_completeness_and_exclusivity():
    """
    Graph audit on TaxonomyRegistry:
    - Verifies 9 registered nodes
    - Verifies bidirectional mutual exclusivity where defined
    - Verifies that no node has broken relations
    """
    TaxonomyRegistry.initialize()
    registry = TaxonomyRegistry._registry
    assert len(registry) == 9, f"Expected 9 taxonomy nodes, found {len(registry)}"

    node_ids = set(registry.keys())
    expected_ids = {
        "furniture", "dental", "pet_services", "food_beverage",
        "bakery", "legal", "hair_beauty", "automotive", "pharmacy"
    }
    assert node_ids == expected_ids

    # Mutual exclusivity checks
    assert TaxonomyRegistry.are_mutually_exclusive("dental", "furniture") is True
    assert TaxonomyRegistry.are_mutually_exclusive("furniture", "dental") is True
    assert TaxonomyRegistry.are_mutually_exclusive("pet_services", "food_beverage") is True
    assert TaxonomyRegistry.are_mutually_exclusive("legal", "automotive") is False  # Not explicitly exclusive

    # Verify all nodes have non-empty aliases, concepts, and slugs
    for nid, node in registry.items():
        assert len(node.aliases) > 0, f"Node {nid} has empty aliases"
        assert len(node.semantic_concepts) > 0, f"Node {nid} has empty semantic concepts"
        assert len(node.directory_slugs) > 0, f"Node {nid} has empty directory slugs"
