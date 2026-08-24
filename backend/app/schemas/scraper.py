from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from backend.app.models.blacklist import ScraperJobStatus


class ScraperRunRequest(BaseModel):
    """Structured search request with explicit city/districts — no opaque string parsing."""
    keyword: str
    city: str
    districts: List[str] = []
    max_results: int = 25
    source: str = "GOOGLE_MAPS"


class ScraperJobResponse(BaseModel):
    id: int
    keyword: str
    location: str  # display string for backward compat
    city: Optional[str] = None
    districts_json: Optional[List[str]] = None
    source: str
    status: ScraperJobStatus
    total_found: int
    total_valid_phones: int
    total_new_leads: int
    duration_seconds: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BlacklistCreate(BaseModel):
    phone_e164: str
    reason: Optional[str] = "USER_REQUEST"
    notes: Optional[str] = None


class BlacklistResponse(BaseModel):
    id: int
    phone_e164: str
    reason: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
