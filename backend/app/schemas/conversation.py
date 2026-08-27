from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from backend.app.models.conversation import ConversationStatus
from backend.app.models.message import MessageDirection, MessageType, ConversationMessageStatus


class MessageBase(BaseModel):
    direction: MessageDirection
    message_type: MessageType = MessageType.TEXT
    body: Optional[str] = None
    sender_phone: str
    recipient_phone: str
    status: ConversationMessageStatus = ConversationMessageStatus.RECEIVED
    wa_message_id: Optional[str] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    external_timestamp: Optional[datetime] = None


class MessageCreate(MessageBase):
    conversation_id: int


class MessageResponse(MessageBase):
    id: int
    conversation_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationBase(BaseModel):
    lead_id: int
    channel: str = "WHATSAPP"
    status: ConversationStatus = ConversationStatus.ACTIVE


class ConversationResponse(ConversationBase):
    id: int
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Enriched Lead attributes
    lead_name: Optional[str] = None
    lead_phone: Optional[str] = None
    last_message_preview: Optional[str] = None
    unread_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)
