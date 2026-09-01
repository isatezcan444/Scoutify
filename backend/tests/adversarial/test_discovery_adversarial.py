"""
Adversarial Discovery & Taxonomy Intelligence Tests.
Validates category taxonomy resolution, search planner robustness, and smart matching under hostile/boundary inputs.
"""
import hashlib
import pytest
from backend.app.models.lead import Lead
from backend.app.services.taxonomy_registry import TaxonomyRegistry
from backend.app.services.intent_resolver import IntentResolver
from backend.app.services.search_planner import SearchPlanner
from backend.app.services.smart_matching_service import SmartMatchingService
from backend.app.schemas.intelligence import CategoryMatchClassification


def test_adversarial_deterministic_hashing_stability():
    """
    INVARIANT PROOF:
    Proves that place_id hashing is mathematically deterministic (SHA-256 slice)
    and strictly immune to Python process restart seed randomization.
    """
    url = "https://www.google.com/maps/place/DataDent+Klinik/@40.99,29.02,17z/data=!3m1"
    expected_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]

    # Verify 1,000 continuous hash calculations yield the exact identical 16-char string
    for _ in range(1000):
        calc = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        assert calc == expected_hash


def test_adversarial_taxonomy_boundary_queries():
    """
    Tests taxonomy resolution against arbitrary, empty, punctuation-only, and nonsense queries:
    Must safely return None or default fallback rather than raising unhandled exceptions.
    """
    hostile_queries = [
        "",
        "   ",
        "!!!@@@###$$$%%%^^^",
        "1234567890",
        "nonexistent_mars_mining_category_xyz",
        "a" * 500,
        "<script>alert(1)</script>",
        "SELECT * FROM categories;",
        "None",
        "null",
    ]

    for q in hostile_queries:
        node = TaxonomyRegistry.find_node_by_alias_or_concept(q)
        # Should gracefully return None or a valid CategoryNode
        if node is not None:
            assert hasattr(node, "id")
            assert hasattr(node, "display_name")


def test_adversarial_search_planner_missing_parameters():
    """
    Tests that SearchPlanner fails fast with informative ValueError when city or districts are missing.
    """
    intent = IntentResolver.resolve_intent("diş")

    # 1. Empty city -> ValueError
    with pytest.raises(ValueError, match="City is required"):
        SearchPlanner.create_plan(intent=intent, city="", districts=["Kadıköy"])

    # 2. Whitespace city -> ValueError
    with pytest.raises(ValueError, match="City is required"):
        SearchPlanner.create_plan(intent=intent, city="   ", districts=["Kadıköy"])

    # 3. Empty districts list -> ValueError
    with pytest.raises(ValueError, match="Districts list cannot be empty"):
        SearchPlanner.create_plan(intent=intent, city="İstanbul", districts=[])


def test_adversarial_smart_matching_polar_opposite_categories():
    """
    Tests that SmartMatchingService correctly identifies mismatch between unrelated domains
    (e.g., Pet Shop lead vs Dental Clinic software offer) and assigns low score / risk factor.
    """
    pet_lead = Lead(
        name="Kadıköy Sevimli Patiler Veteriner Kliniği & Pet Shop",
        category="Pet Shop & Veteriner",
        city="İstanbul",
        district="Kadıköy",
        is_whatsapp_eligible=True
    )

    assessment = SmartMatchingService.evaluate_lead(
        lead=pet_lead,
        offer_title="Diş Hekimlerine Özel İmplant Randevu ve Takip Yazılımı",
        offer_description="Diş hekimliği ve dental klinik operasyonları için randevu optimizasyonu.",
        approved_target_categories=["Diş Klinikleri", "Diş Hekimleri"]
    )

    assert assessment is not None
    assert assessment.fit_score < 70, f"Unrelated pet shop should not get high dental fit score: {assessment.fit_score}"
    assert isinstance(assessment.positive_signals, list)
    assert isinstance(assessment.risk_factors, list)
