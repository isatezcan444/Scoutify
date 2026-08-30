"""
Tests for Category Recommendation Service & Confirmation Layer.
"""
import pytest
from backend.app.schemas.smart_outreach import (
    CategoryRecommendationRequest,
    CategoryFitLevel,
    CategorySource,
    BusinessGoal
)
from backend.app.services.category_recommendation_service import CategoryRecommendationService


def test_recommend_categories_vip_transfer():
    request = CategoryRecommendationRequest(
        offer_title="Vito VIP Transfer Hizmeti",
        offer_description="Havalimanı ve otel transferleri, şoförlü lüks araç",
        business_goal=BusinessGoal.DISCOVERY
    )
    response = CategoryRecommendationService.recommend_categories(request)

    assert len(response.discovered_categories) >= 3
    cat_ids = [c.category_id for c in response.discovered_categories]
    assert "hotels" in cat_ids
    assert "travel_agencies" in cat_ids

    hotel_cat = next(c for c in response.discovered_categories if c.category_id == "hotels")
    assert hotel_cat.fit_level == CategoryFitLevel.HIGH
    assert "transfer" in hotel_cat.rationale.lower()
    assert hotel_cat.source == CategorySource.DISCOVERED


def test_recommend_categories_dental_supply():
    request = CategoryRecommendationRequest(
        offer_title="Dental Sarf Malzemeleri ve İmplant",
        offer_description="Kliniklere toptan medikal diş malzemesi tedariki",
        business_goal=BusinessGoal.DISCOVERY
    )
    response = CategoryRecommendationService.recommend_categories(request)

    cat_ids = [c.category_id for c in response.discovered_categories]
    assert "dental_clinics" in cat_ids
    assert "dental_centers" in cat_ids
    top_cat = response.discovered_categories[0]
    assert top_cat.fit_level == CategoryFitLevel.HIGH


def test_recommend_categories_fallback_taxonomy():
    request = CategoryRecommendationRequest(
        offer_title="Avukatlık ve Arabuluculuk Danışmanlığı",
        business_goal=BusinessGoal.INTRO
    )
    response = CategoryRecommendationService.recommend_categories(request)

    assert len(response.discovered_categories) > 0
    cat_ids = [c.category_id for c in response.discovered_categories]
    assert "legal" in cat_ids or "corporate_businesses" in cat_ids


def test_recommend_categories_software_solution():
    request = CategoryRecommendationRequest(
        offer_title="Kurumsal yazılım çözümü",
        offer_description="Küçük ve orta ölçekli işletmeler için iş süreçlerini dijitalleştiren yazılım çözümleri.",
        business_goal=BusinessGoal.DISCOVERY
    )
    response = CategoryRecommendationService.recommend_categories(request)

    assert len(response.discovered_categories) >= 3
    cat_ids = [c.category_id for c in response.discovered_categories]
    assert "e_commerce_retail" in cat_ids or "beauty_centers" in cat_ids
    for cat in response.discovered_categories:
        assert cat.source == CategorySource.DISCOVERED
        assert cat.rationale != ""
        assert cat.fit_level in {CategoryFitLevel.HIGH, CategoryFitLevel.MEDIUM}


