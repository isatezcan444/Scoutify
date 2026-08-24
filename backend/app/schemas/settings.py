from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class AntiBanSettingsSchema(BaseModel):
    preset: str = Field(default="standard_balanced", description="ultra_safe | standard_balanced | fast_warmed | custom")
    min_delay_seconds: int = Field(default=45, ge=5, le=600)
    max_delay_seconds: int = Field(default=120, ge=10, le=900)
    typing_delay_seconds: int = Field(default=4, ge=1, le=30)
    daily_message_limit: int = Field(default=50, ge=5, le=500)
    working_hours_enabled: bool = True
    working_hours_start: str = "09:00"
    working_hours_end: str = "18:30"


class AntiBanSettingsResponse(AntiBanSettingsSchema):
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
