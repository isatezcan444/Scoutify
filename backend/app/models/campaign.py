import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class CampaignStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Message Template with Spintax
    # e.g.: "{Merhaba|Selamlar} {name} Yetkilisi, {city} lokasyonundaki {category} hizmetinizi gördüm..."
    message_template = Column(Text, nullable=False)
    
    # Campaign Controls & Anti-Ban Config
    status = Column(Enum(CampaignStatus), default=CampaignStatus.DRAFT, index=True)
    min_delay_seconds = Column(Integer, default=45) # Random delay lower bound
    max_delay_seconds = Column(Integer, default=120) # Random delay upper bound
    typing_delay_seconds = Column(Integer, default=5) # Typing simulation
    
    # Working Hours Gate
    working_hours_enabled = Column(Boolean, default=True)
    working_hours_start = Column(String(10), default="09:30") # HH:MM
    working_hours_end = Column(String(10), default="18:30") # HH:MM
    
    # Session Association (Optional: specific session or round-robin all active)
    session_id = Column(Integer, ForeignKey("whatsapp_sessions.id", ondelete="SET NULL"), nullable=True)
    session = relationship("WhatsAppSession", backref="campaigns")
    
    # Counters
    total_leads_target = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    replied_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
