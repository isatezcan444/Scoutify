from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class DashboardStatsResponse(BaseModel):
    total_leads: int
    whatsapp_eligible_leads: int
    contacted_leads: int
    replied_leads: int
    response_rate_percentage: float
    total_campaigns: int
    active_campaigns: int
    connected_sessions: int
    total_messages_sent: int
    messages_sent_today: int
    daily_volume: List[Dict[str, Any]]
    leads_by_status: Dict[str, int]
    top_categories: List[Dict[str, Any]]
    recent_activity: List[Dict[str, Any]]
