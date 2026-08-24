"""
Discovery Strategy Abstraction for Business Discovery Engine V3.
Defines targeted execution strategies across independent provider capabilities.
"""
import enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.app.schemas.intelligence import ProviderQuery, QueryFamily


class StrategyType(str, enum.Enum):
    OVERPASS_STRUCTURED_CATEGORY = "OVERPASS_STRUCTURED_CATEGORY"
    DIRECTORY_CATEGORY_SLUGS = "DIRECTORY_CATEGORY_SLUGS"
    DIRECTORY_EXHAUSTIVE_PAGES = "DIRECTORY_EXHAUSTIVE_PAGES"
    LOCAL_SUBDIVISION_GEO = "LOCAL_SUBDIVISION_GEO"
    WEB_BUSINESS_CONTACT_EXPANSION = "WEB_BUSINESS_CONTACT_EXPANSION"
    NOMINATIM_ENTITY_LOOKUP = "NOMINATIM_ENTITY_LOOKUP"


class DiscoveryStrategy(BaseModel):
    strategy_type: StrategyType
    priority: int = 1
    estimated_cost: int = 1
    provider_queries: List[ProviderQuery] = Field(default_factory=list)
