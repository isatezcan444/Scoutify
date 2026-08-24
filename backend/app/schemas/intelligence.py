"""
Data Contracts and Schema Models for Business Discovery Engine V2.
Supports Hierarchical Query Families, Iterative Discovery Rounds,
Coverage Analysis, Multi-Provider Provenance, and Entity Graph Fusion.
"""
import enum
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field


def get_utc_now() -> datetime:
    """Helper to return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class QueryFamily(str, enum.Enum):
    EXACT_INTENT = "EXACT_INTENT"                  # e.g., "diş kliniği Ataşehir"
    BUSINESS_TERMINOLOGY = "BUSINESS_TERMINOLOGY"  # e.g., "ağız ve diş sağlığı merkezi Ataşehir", "dental clinic Ataşehir"
    PROVIDER_TAXONOMY = "PROVIDER_TAXONOMY"        # e.g., amenity=dentist, healthcare=dentist
    LOCAL_SUBDIVISION = "LOCAL_SUBDIVISION"        # e.g., "diş kliniği Barbaros Ataşehir", "diş kliniği İçerenköy Ataşehir"
    COMMERCIAL_INTENT = "COMMERCIAL_INTENT"        # e.g., "diş kliniği Ataşehir telefon", "diş hekimi muayenehanesi Ataşehir"


class RelationshipType(str, enum.Enum):
    IS_A = "IS_A"
    SUBCATEGORY_OF = "SUBCATEGORY_OF"
    RELATED_TO = "RELATED_TO"
    MUTUALLY_EXCLUSIVE = "MUTUALLY_EXCLUSIVE"
    COMPLEMENTARY_TO = "COMPLEMENTARY_TO"


class CategoryMatchClassification(str, enum.Enum):
    MATCH = "MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    RELATED = "RELATED"
    AMBIGUOUS = "AMBIGUOUS"
    MISMATCH = "MISMATCH"


class QualificationState(str, enum.Enum):
    QUALIFIED = "QUALIFIED"
    CANDIDATE = "CANDIDATE"
    UNVERIFIED = "UNVERIFIED"
    REJECTED = "REJECTED"


class CategoryRelationship(BaseModel):
    target_category_id: str
    relationship_type: RelationshipType
    weight: float = 1.0


class CategoryNode(BaseModel):
    id: str
    name: str
    display_name: str
    parent_id: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    semantic_concepts: List[str] = Field(default_factory=list)
    directory_slugs: List[str] = Field(default_factory=list)
    osm_amenities: List[str] = Field(default_factory=list)
    osm_healthcare: List[str] = Field(default_factory=list)
    osm_shops: List[str] = Field(default_factory=list)
    relationships: List[CategoryRelationship] = Field(default_factory=list)
    version: str = "1.0.0"


class CategoryProfile(BaseModel):
    canonical_id: str
    display_name: str
    semantic_description: str
    profile_version: str = "1.0.0"
    is_dynamic: bool = False
    positive_concepts: List[str] = Field(default_factory=list)
    negative_concepts: List[str] = Field(default_factory=list)
    search_terms: List[str] = Field(default_factory=list)
    directory_slugs: List[str] = Field(default_factory=list)
    osm_amenities: List[str] = Field(default_factory=list)
    osm_shops: List[str] = Field(default_factory=list)
    mutually_exclusive_categories: List[str] = Field(default_factory=list)
    related_categories: List[str] = Field(default_factory=list)


class SearchIntent(BaseModel):
    raw_query: str
    normalized_query: str
    canonical_category_id: str
    category_profile: CategoryProfile
    location_required: bool = True
    intent_type: str = "business_discovery"
    created_at: datetime = Field(default_factory=get_utc_now)


class LocationSubdivision(BaseModel):
    city: str
    district: str
    neighborhoods: List[str] = Field(default_factory=list)


class ProviderQuery(BaseModel):
    query_id: str
    query_family: QueryFamily = QueryFamily.EXACT_INTENT
    provider_name: str
    query_text: str
    category_slug: Optional[str] = None
    osm_tags: Optional[Dict[str, str]] = None
    district: str
    city: str
    subdivision: Optional[str] = None
    round_number: int = 1
    page: int = 1
    limit: int = 50


class SearchPlan(BaseModel):
    search_intent: SearchIntent
    city: str
    districts: List[str]
    max_results: int
    provider_queries: List[ProviderQuery] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=get_utc_now)


class RawBusinessCandidate(BaseModel):
    candidate_id: str
    provider: str
    provider_query: str
    query_family: QueryFamily = QueryFamily.EXACT_INTENT
    query_id: Optional[str] = None
    raw_name: str
    clean_name: str
    raw_category: Optional[str] = None
    raw_address: Optional[str] = None
    raw_phone: Optional[str] = None
    raw_website: Optional[str] = None
    source_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)
    discovered_at: datetime = Field(default_factory=get_utc_now)


class CandidateProvenance(BaseModel):
    provider: str
    query_id: str
    query_family: QueryFamily
    query_text: str
    source_url: Optional[str] = None
    raw_category: Optional[str] = None
    discovered_at: datetime = Field(default_factory=get_utc_now)


class CategoryAssessment(BaseModel):
    score: float = 0.0
    classification: CategoryMatchClassification
    matched_category_id: Optional[str] = None
    positive_evidence: List[str] = Field(default_factory=list)
    negative_evidence: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    reason: str


class QualityAssessment(BaseModel):
    category_score: float
    location_score: float
    entity_score: float
    contact_score: float
    source_score: float
    overall_quality_score: int
    qualification_state: QualificationState
    entity_type: str
    is_verified: bool
    positive_signals: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    rejection_reasons: List[str] = Field(default_factory=list)


class CandidateEntity(BaseModel):
    entity_id: str
    primary_name: str
    name_variations: List[str] = Field(default_factory=list)
    phone_e164: str
    phone_raw: str
    is_mobile: bool
    is_whatsapp_eligible: bool
    address: Optional[str] = None
    city: str
    district: str
    subdivision: Optional[str] = None
    website: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    provenance_list: List[CandidateProvenance] = Field(default_factory=list)
    discovery_confidence: float = 0.5
    category_assessment: Optional[CategoryAssessment] = None
    quality_assessment: Optional[QualityAssessment] = None
    qualification_state: QualificationState = QualificationState.CANDIDATE
    rejection_reason: Optional[str] = None


class RoundMetrics(BaseModel):
    round_number: int
    query_family: QueryFamily
    queries_executed: int = 0
    pages_visited: int = 0
    raw_candidates_found: int = 0
    new_candidates_added: int = 0
    duplicate_candidates: int = 0
    rejections_count: int = 0
    discovery_yield_rate: float = 0.0


class CoverageReport(BaseModel):
    total_rounds: int = 0
    total_queries: int = 0
    query_families_covered: List[QueryFamily] = Field(default_factory=list)
    subdivisions_covered: List[str] = Field(default_factory=list)
    subdivisions_total: int = 0
    subdivision_coverage_pct: float = 0.0
    raw_candidates_total: int = 0
    unique_entities_total: int = 0
    category_matches: int = 0
    category_mismatches: int = 0
    location_rejected: int = 0
    qualified_leads_total: int = 0
    diminishing_returns_reached: bool = False
    round_history: List[RoundMetrics] = Field(default_factory=list)


class SearchTrace(BaseModel):
    job_id: Optional[int] = None
    raw_query: str
    resolved_category: str
    city: str
    districts: List[str]
    coverage_report: CoverageReport = Field(default_factory=CoverageReport)
    query_traces: List[Dict[str, Any]] = Field(default_factory=list)
    candidates_trace: List[Dict[str, Any]] = Field(default_factory=list)
