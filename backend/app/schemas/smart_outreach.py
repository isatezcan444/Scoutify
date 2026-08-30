"""
Schemas for Smart Outreach, Category Confirmation, and Intelligent Matching.
"""
import enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CategorySource(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    USER_ADDED = "USER_ADDED"


class CategoryFitLevel(str, enum.Enum):
    HIGH = "HIGH"          # Yüksek Uyum
    MEDIUM = "MEDIUM"      # Orta Uyum
    LOW = "LOW"            # Düşük Uyum
    ALTERNATIVE = "ALTERNATIVE"


class BusinessGoal(str, enum.Enum):
    DISCOVERY = "DISCOVERY"    # 🔎 İhtiyaç Keşfet
    INTRO = "INTRO"            # 🤝 Hizmeti Tanıt
    OFFER = "OFFER"            # 💰 Teklif Sun
    FOLLOW_UP = "FOLLOW_UP"    # 🔄 Takip Yap
    MEETING = "MEETING"        # 📅 Görüşme Ayarla


class DiscoveredCategory(BaseModel):
    category_id: str
    display_name: str
    rationale: str
    fit_level: CategoryFitLevel
    search_keywords: List[str] = Field(default_factory=list)
    source: CategorySource = CategorySource.DISCOVERED
    is_recommended: bool = True
    estimated_volume: Optional[str] = "Orta - Yüksek"


class CategoryRecommendationRequest(BaseModel):
    offer_title: str
    offer_description: Optional[str] = None
    business_goal: Optional[BusinessGoal] = BusinessGoal.DISCOVERY
    target_sector_hint: Optional[str] = None
    city: Optional[str] = None



class CategoryRecommendationResponse(BaseModel):
    offer_title: str
    business_goal: BusinessGoal
    discovered_categories: List[DiscoveredCategory]
    suggested_custom_categories: List[str] = Field(default_factory=list)


class TargetedDiscoveryRequest(BaseModel):
    offer_title: str
    offer_description: Optional[str] = None
    business_goal: BusinessGoal = BusinessGoal.DISCOVERY
    city: str
    districts: List[str] = Field(default_factory=list)
    approved_target_categories: List[str]  # e.g. ["hotels", "corporate_companies", "travel_agencies"]
    user_added_categories: List[str] = Field(default_factory=list)
    max_results_per_category: int = 15


class FitAssessment(BaseModel):
    fit_score: int = Field(ge=0, le=100)
    fit_level: CategoryFitLevel
    target_category: str
    category_approved_by_user: bool = True
    positive_signals: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    recommended_intent: BusinessGoal = BusinessGoal.DISCOVERY
    recommended_message_snippet: Optional[str] = None


class SmartMatchedLead(BaseModel):
    lead_id: int
    name: str
    phone: str
    phone_e164: Optional[str] = None
    is_whatsapp_eligible: bool = True
    city: Optional[str] = None
    district: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    target_category: str
    category_source: CategorySource = CategorySource.DISCOVERED
    fit_assessment: FitAssessment


class MatchLeadsRequest(BaseModel):
    offer_title: str
    offer_description: Optional[str] = None
    business_goal: BusinessGoal = BusinessGoal.DISCOVERY
    approved_target_categories: Optional[List[str]] = None
    lead_ids: Optional[List[int]] = None
    city: Optional[str] = None
    category_filter: Optional[str] = None
    min_fit_score: int = 30



class MatchLeadsResponse(BaseModel):
    total_evaluated: int
    high_fit_count: int
    medium_fit_count: int
    low_fit_count: int
    leads: List[SmartMatchedLead]


class MessageRecommendationRequest(BaseModel):
    lead_id: int
    offer_title: str
    offer_description: Optional[str] = None
    business_goal: BusinessGoal = BusinessGoal.DISCOVERY
    target_category: Optional[str] = None


class MessageRecommendationResponse(BaseModel):
    lead_id: int
    lead_name: str
    target_category: str
    business_goal: BusinessGoal
    strategy_summary: str
    recommended_message: str
    alternative_message: Optional[str] = None
