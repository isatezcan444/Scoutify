from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.models.conversation import Conversation, ConversationStatus
from backend.app.models.message import Message
from backend.app.models.lead import Lead
from backend.app.schemas.conversation import (
    ConversationResponse,
    ConversationDetailResponse,
    MessageResponse,
)

router = APIRouter()


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    status: Optional[ConversationStatus] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Lists conversations ordered by most recent message."""
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.lead), selectinload(Conversation.messages))
        .order_by(Conversation.last_message_at.desc().nullslast(), Conversation.id.desc())
        .offset(offset)
        .limit(limit)
    )
    if status:
        stmt = stmt.where(Conversation.status == status)

    res = await db.execute(stmt)
    conversations = res.scalars().all()

    result = []
    for conv in conversations:
        latest_msg = conv.messages[-1] if conv.messages else None
        item = ConversationResponse(
            id=conv.id,
            lead_id=conv.lead_id,
            channel=conv.channel,
            status=conv.status,
            last_message_at=conv.last_message_at,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            lead_name=conv.lead.name if conv.lead else None,
            lead_phone=conv.lead.phone_e164 if conv.lead else None,
            last_message_preview=latest_msg.body if latest_msg else None,
            unread_count=0,
        )
        result.append(item)

    return result


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetches a specific conversation with all its messages."""
    stmt = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.lead), selectinload(Conversation.messages))
    )
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_dto = [MessageResponse.model_validate(m) for m in conv.messages]
    latest_msg = conv.messages[-1] if conv.messages else None

    return ConversationDetailResponse(
        id=conv.id,
        lead_id=conv.lead_id,
        channel=conv.channel,
        status=conv.status,
        last_message_at=conv.last_message_at,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        lead_name=conv.lead.name if conv.lead else None,
        lead_phone=conv.lead.phone_e164 if conv.lead else None,
        last_message_preview=latest_msg.body if latest_msg else None,
        unread_count=0,
        messages=messages_dto,
    )


@router.get("/lead/{lead_id}", response_model=ConversationDetailResponse)
async def get_lead_conversation(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetches or initializes the active conversation thread for a given lead."""
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    stmt = (
        select(Conversation)
        .where(Conversation.lead_id == lead_id, Conversation.channel == "WHATSAPP")
        .options(selectinload(Conversation.lead), selectinload(Conversation.messages))
        .order_by(Conversation.id.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()

    if not conv:
        conv = Conversation(
            lead_id=lead_id,
            channel="WHATSAPP",
            status=ConversationStatus.ACTIVE,
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        # re-query with options
        stmt = select(Conversation).where(Conversation.id == conv.id).options(selectinload(Conversation.lead), selectinload(Conversation.messages))
        conv = (await db.execute(stmt)).scalar_one()

    messages_dto = [MessageResponse.model_validate(m) for m in conv.messages]
    latest_msg = conv.messages[-1] if conv.messages else None

    return ConversationDetailResponse(
        id=conv.id,
        lead_id=conv.lead_id,
        channel=conv.channel,
        status=conv.status,
        last_message_at=conv.last_message_at,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        lead_name=conv.lead.name if conv.lead else None,
        lead_phone=conv.lead.phone_e164 if conv.lead else None,
        last_message_preview=latest_msg.body if latest_msg else None,
        unread_count=0,
        messages=messages_dto,
    )
