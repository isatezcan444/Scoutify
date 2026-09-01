from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.lead import LeadResponse

class CampaignGroupBase(BaseModel):
    name: str
    description: Optional[str] = None
    target_category: Optional[str] = None
    target_location: Optional[str] = None

class CampaignGroupCreate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_category: Optional[str] = None
    target_location: Optional[str] = None
    lead_ids: Optional[List[int]] = None

class CampaignGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_category: Optional[str] = None
    target_location: Optional[str] = None

class CampaignGroupResponse(CampaignGroupBase):
    id: int
    total_leads_count: int = 0
    whatsapp_eligible_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CampaignGroupDetailResponse(CampaignGroupResponse):
    leads: List[LeadResponse] = []

class AddLeadsToGroupRequest(BaseModel):
    lead_ids: List[int]

class AddLeadsToGroupResponse(BaseModel):
    group_id: int
    group_name: str
    added_count: int
    existing_count: int
    total_leads_count: int
    whatsapp_eligible_count: int
    message: str

class CampaignGroupBulkDeleteRequest(BaseModel):
    group_ids: List[int]
