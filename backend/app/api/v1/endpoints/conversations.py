from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.api.v1.websocket import ws_manager
from backend.app.models.conversation import Conversation, ConversationStatus
from backend.app.models.message import Message
from backend.app.models.lead import Lead
from backend.app.schemas.conversation import (
    ConversationResponse,
    ConversationDetailResponse,
    ConversationMessagesResponse,
    MessageResponse,
)

router = APIRouter()


async def _fetch_paginated_messages(
    db: AsyncSession,
    conversation_id: int,
    limit: int = 50,
    before: Optional[int] = None,
):
    """
    Fetches messages for a conversation with cursor pagination.
    Returns (messages in chronological order, has_more, oldest_id, newest_id).
    """
    stmt = select(Message).where(Message.conversation_id == conversation_id)
    if before is not None:
        stmt = stmt.where(Message.id < before)

    stmt = stmt.order_by(Message.id.desc()).limit(limit + 1)
    res = await db.execute(stmt)
    raw_messages = res.scalars().all()

    has_more = len(raw_messages) > limit
    paginated = raw_messages[:limit]
    chronological = list(reversed(paginated))

    oldest_id = chronological[0].id if chronological else None
    newest_id = chronological[-1].id if chronological else None

    messages_dto = [MessageResponse.model_validate(m) for m in chronological]
    return messages_dto, has_more, oldest_id, newest_id


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
            unread_count=conv.unread_count or 0,
            last_read_at=conv.last_read_at,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            lead_name=conv.lead.name if conv.lead else None,
            lead_phone=conv.lead.phone_e164 if conv.lead else None,
            last_message_preview=latest_msg.body if latest_msg else None,
        )
        result.append(item)

    return result


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: int,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[int] = Query(None, description="Cursor: message ID before which to fetch older messages"),
    db: AsyncSession = Depends(get_db),
):
    """Fetches a specific conversation with cursor-paginated messages."""
    stmt = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.lead), selectinload(Conversation.messages))
    )
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_dto, has_more, oldest_id, newest_id = await _fetch_paginated_messages(
        db=db, conversation_id=conv.id, limit=limit, before=before
    )
    latest_msg = conv.messages[-1] if conv.messages else None

    return ConversationDetailResponse(
        id=conv.id,
        lead_id=conv.lead_id,
        channel=conv.channel,
        status=conv.status,
        last_message_at=conv.last_message_at,
        unread_count=conv.unread_count or 0,
        last_read_at=conv.last_read_at,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        lead_name=conv.lead.name if conv.lead else None,
        lead_phone=conv.lead.phone_e164 if conv.lead else None,
        last_message_preview=latest_msg.body if latest_msg else None,
        messages=messages_dto,
        has_more=has_more,
        oldest_message_id=oldest_id,
        newest_message_id=newest_id,
    )


@router.get("/{conversation_id}/messages", response_model=ConversationMessagesResponse)
async def get_conversation_messages(
    conversation_id: int,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[int] = Query(None, description="Cursor: message ID before which to fetch older messages"),
    db: AsyncSession = Depends(get_db),
):
    """Dedicated endpoint to fetch older paginated messages for a conversation."""
    conv = await db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_dto, has_more, oldest_id, newest_id = await _fetch_paginated_messages(
        db=db, conversation_id=conv.id, limit=limit, before=before
    )

    return ConversationMessagesResponse(
        messages=messages_dto,
        has_more=has_more,
        oldest_message_id=oldest_id,
        newest_message_id=newest_id,
    )


@router.get("/lead/{lead_id}", response_model=ConversationDetailResponse)
async def get_lead_conversation(
    lead_id: int,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[int] = Query(None, description="Cursor: message ID before which to fetch older messages"),
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
            unread_count=0,
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        stmt = (
            select(Conversation)
            .where(Conversation.id == conv.id)
            .options(selectinload(Conversation.lead), selectinload(Conversation.messages))
        )
        conv = (await db.execute(stmt)).scalar_one()

    messages_dto, has_more, oldest_id, newest_id = await _fetch_paginated_messages(
        db=db, conversation_id=conv.id, limit=limit, before=before
    )
    latest_msg = conv.messages[-1] if conv.messages else None

    return ConversationDetailResponse(
        id=conv.id,
        lead_id=conv.lead_id,
        channel=conv.channel,
        status=conv.status,
        last_message_at=conv.last_message_at,
        unread_count=conv.unread_count or 0,
        last_read_at=conv.last_read_at,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        lead_name=conv.lead.name if conv.lead else None,
        lead_phone=conv.lead.phone_e164 if conv.lead else None,
        last_message_preview=latest_msg.body if latest_msg else None,
        messages=messages_dto,
        has_more=has_more,
        oldest_message_id=oldest_id,
        newest_message_id=newest_id,
    )


@router.post("/{conversation_id}/read", response_model=ConversationResponse)
async def mark_conversation_as_read(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Marks a conversation as read, resetting unread_count to 0."""
    stmt = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.lead), selectinload(Conversation.messages))
    )
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv.unread_count = 0
    conv.last_read_at = datetime.utcnow()
    await db.commit()
    await db.refresh(conv)

    # Broadcast conversation_read event to WebSocket
    await ws_manager.broadcast({
        "event": "conversation_read",
        "conversation_id": conv.id,
        "lead_id": conv.lead_id,
        "unread_count": 0,
        "last_read_at": conv.last_read_at.isoformat() if conv.last_read_at else None,
    })

    latest_msg = conv.messages[-1] if conv.messages else None
    return ConversationResponse(
        id=conv.id,
        lead_id=conv.lead_id,
        channel=conv.channel,
        status=conv.status,
        last_message_at=conv.last_message_at,
        unread_count=0,
        last_read_at=conv.last_read_at,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        lead_name=conv.lead.name if conv.lead else None,
        lead_phone=conv.lead.phone_e164 if conv.lead else None,
        last_message_preview=latest_msg.body if latest_msg else None,
    )


@router.post("/lead/{lead_id}/read", response_model=ConversationResponse)
async def mark_lead_conversation_as_read(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Marks the active conversation of a lead as read."""
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
        raise HTTPException(status_code=404, detail="Conversation for lead not found")

    conv.unread_count = 0
    conv.last_read_at = datetime.utcnow()
    await db.commit()
    await db.refresh(conv)

    await ws_manager.broadcast({
        "event": "conversation_read",
        "conversation_id": conv.id,
        "lead_id": conv.lead_id,
        "unread_count": 0,
        "last_read_at": conv.last_read_at.isoformat() if conv.last_read_at else None,
    })

    latest_msg = conv.messages[-1] if conv.messages else None
    return ConversationResponse(
        id=conv.id,
        lead_id=conv.lead_id,
        channel=conv.channel,
        status=conv.status,
        last_message_at=conv.last_message_at,
        unread_count=0,
        last_read_at=conv.last_read_at,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        lead_name=conv.lead.name if conv.lead else None,
        lead_phone=conv.lead.phone_e164 if conv.lead else None,
        last_message_preview=latest_msg.body if latest_msg else None,
    )
