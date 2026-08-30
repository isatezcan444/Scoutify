"""
Dedicated service for WhatsApp Outbound Message Dispatching.
Handles conversation validation, recipient phone resolution, Meta Graph API dispatch / simulation,
database persistence, and realtime WebSocket event broadcasting.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.models.conversation import Conversation, ConversationStatus
from backend.app.models.message import (
    Message,
    MessageDirection,
    MessageType,
    ConversationMessageStatus,
)
from backend.app.models.lead import Lead
from backend.app.services.phone_service import PhoneService
from backend.app.services.whatsapp_cloud_client import WhatsAppCloudApiClient
from backend.app.api.v1.websocket import ws_manager

logger = logging.getLogger(__name__)


# In-memory TTL cache for idempotency keys -> (timestamp, message_id)
_idempotency_cache: Dict[str, Any] = {}


class WhatsAppOutboundService:
    """Service handling outbound message sending for Conversations."""

    @classmethod
    async def send_conversation_message(
        cls,
        db: AsyncSession,
        conversation_id: int,
        text: str,
        idempotency_key: Optional[str] = None,
        force_simulation: Optional[bool] = None,
    ) -> Message:
        """
        Validates conversation, sends message via Meta Cloud API or simulation,
        persists OUTBOUND Message entity, and broadcasts WebSocket event.
        """
        # 1. Validate Text Content
        clean_text = (text or "").strip()
        if not clean_text:
            raise HTTPException(status_code=422, detail="Mesaj metni boş olamaz.")
        if len(clean_text) > 4096:
            raise HTTPException(status_code=422, detail="Mesaj metni 4096 karakterden uzun olamaz.")

        # 2. Fetch Conversation & Lead
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.lead))
        )
        res = await db.execute(stmt)
        conv = res.scalar_one_or_none()

        if not conv:
            raise HTTPException(status_code=404, detail="Diyalog bulunamadı.")

        if conv.status == ConversationStatus.CLOSED:
            raise HTTPException(
                status_code=400,
                detail="Kapalı bir diyaloğa mesaj gönderilemez. Lütfen önce diyaloğu yeniden açın.",
            )

        lead = conv.lead
        if not lead:
            raise HTTPException(status_code=404, detail="Diyalog ile ilişkili müşteri bulunamadı.")

        # 3. Resolve & Normalize Recipient Phone Number
        raw_phone = lead.phone_e164 or lead.phone
        if not raw_phone:
            raise HTTPException(
                status_code=400,
                detail="Müşteriye ait geçerli bir telefon numarası bulunamadı.",
            )

        phone_data = PhoneService.normalize_to_e164(raw_phone)
        e164_phone = phone_data["e164"] if phone_data else (
            f"+{raw_phone}" if not raw_phone.startswith("+") else raw_phone
        )

        # 3b. Check 24-Hour Customer Window Enforcement
        window_info = await cls.check_24h_window(conversation_id, db)
        if not window_info["is_window_open"]:
            raise HTTPException(
                status_code=400,
                detail="24 saatlik müşteri iletişim süresi dolmuştur. Lütfen konuşmaya devam etmek için bir şablon mesajı kullanın.",
            )

        # 4. Check Idempotency (if key provided)
        if idempotency_key:
            import time
            now_ts = time.time()
            # Clean expired cache entries (> 1 hour)
            expired_keys = [k for k, v in _idempotency_cache.items() if now_ts - v[0] > 3600]
            for k in expired_keys:
                _idempotency_cache.pop(k, None)

            if idempotency_key in _idempotency_cache:
                _, cached_msg_id = _idempotency_cache[idempotency_key]
                cached_msg = await db.get(Message, cached_msg_id)
                if cached_msg:
                    logger.info(f"[WhatsAppOutboundService] Idempotency cache hit for key {idempotency_key}")
                    return cached_msg

            existing_stmt = select(Message).where(
                Message.conversation_id == conversation_id,
                Message.wa_message_id == idempotency_key,
            )
            existing_msg = (await db.execute(existing_stmt)).scalar_one_or_none()
            if existing_msg:
                logger.info(f"[WhatsAppOutboundService] Idempotency match for key {idempotency_key}")
                return existing_msg

        # 5. Dispatch via WhatsApp Cloud Client or Simulation
        is_sim = settings.SIMULATION_MODE if force_simulation is None else force_simulation
        wa_message_id: Optional[str] = None

        if is_sim or not settings.WHATSAPP_CLOUD_ENABLED:
            import time, random
            wa_message_id = f"wamid.SIM_{int(time.time())}_{random.randint(100000, 999999)}"
            logger.info(
                f"[WhatsAppOutboundService] (SIMULATION) Message dispatched: "
                f"conv_id={conv.id}, recipient={e164_phone}, wamid={wa_message_id}"
            )
        else:
            client = WhatsAppCloudApiClient()
            dispatch_res = await client.send_text_message(
                to_phone=e164_phone,
                message_text=clean_text,
            )

            if not dispatch_res.get("success"):
                error_msg = dispatch_res.get("error") or "Meta Cloud API mesajı iletemedi."
                logger.error(f"[WhatsAppOutboundService] Dispatch failed: {error_msg}")
                raise HTTPException(
                    status_code=502,
                    detail=f"WhatsApp mesajı gönderilemedi: {error_msg}",
                )

            wa_message_id = dispatch_res.get("message_id")

        now_utc = datetime.now(timezone.utc)

        # 6. Persist OUTBOUND Message Entity
        outbound_msg = Message(
            conversation_id=conv.id,
            direction=MessageDirection.OUTBOUND,
            message_type=MessageType.TEXT,
            body=clean_text,
            wa_message_id=wa_message_id,
            sender_phone="BUSINESS",
            recipient_phone=e164_phone,
            status=ConversationMessageStatus.SENT,
            external_timestamp=now_utc,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db.add(outbound_msg)

        # 7. Update Conversation state
        conv.last_message_at = now_utc
        conv.updated_at = now_utc
        if conv.status == ConversationStatus.ARCHIVED:
            conv.status = ConversationStatus.ACTIVE

        await db.commit()
        await db.refresh(outbound_msg)

        if idempotency_key:
            import time
            _idempotency_cache[idempotency_key] = (time.time(), outbound_msg.id)

        # 8. Broadcast Realtime Event
        await ws_manager.broadcast({
            "event": "outbound_message_sent",
            "message_id": outbound_msg.id,
            "wa_message_id": outbound_msg.wa_message_id,
            "conversation_id": conv.id,
            "lead_id": lead.id,
            "lead_name": lead.name,
            "recipient_phone": e164_phone,
            "direction": "OUTBOUND",
            "message_type": "TEXT",
            "status": "SENT",
            "message": clean_text,
            "body": clean_text,
            "created_at": outbound_msg.created_at.isoformat(),
        })

        return outbound_msg

    @staticmethod
    async def check_24h_window(conversation_id: int, db: AsyncSession) -> Dict[str, Any]:
        """
        Calculates whether the 24-hour customer service communication window is open.
        A window is open if the last INBOUND message from the customer was received < 24 hours ago,
        or if no inbound messages have been exchanged yet.
        """
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.direction == MessageDirection.INBOUND,
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_inbound = (await db.execute(stmt)).scalar_one_or_none()

        if not last_inbound:
            # If no inbound messages yet, window is open for normal outreach/templates
            return {
                "is_window_open": True,
                "last_inbound_at": None,
                "seconds_remaining": 86400,
            }

        last_inbound_time = last_inbound.external_timestamp or last_inbound.created_at
        if last_inbound_time.tzinfo is None:
            last_inbound_time = last_inbound_time.replace(tzinfo=timezone.utc)

        now_utc = datetime.now(timezone.utc)
        elapsed_seconds = (now_utc - last_inbound_time).total_seconds()
        is_open = elapsed_seconds < 86400

        return {
            "is_window_open": is_open,
            "last_inbound_at": last_inbound_time,
            "seconds_remaining": max(0, int(86400 - elapsed_seconds)),
        }

    @classmethod
    async def retry_failed_message(
        cls,
        db: AsyncSession,
        conversation_id: int,
        message_id: int,
        force_simulation: Optional[bool] = None,
    ) -> Message:
        """
        Retries sending a FAILED message with complete audit preservation and idempotency.
        """
        msg = await db.get(Message, message_id)
        if not msg or msg.conversation_id != conversation_id:
            raise HTTPException(status_code=404, detail="Mesaj bulunamadı.")

        if msg.direction != MessageDirection.OUTBOUND:
            raise HTTPException(status_code=400, detail="Yalnızca giden mesajlar tekrar denenebilir.")

        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.lead))
        )
        conv = (await db.execute(stmt)).scalar_one_or_none()
        if not conv or not conv.lead:
            raise HTTPException(status_code=404, detail="Diyalog veya müşteri bulunamadı.")

        raw_phone = conv.lead.phone_e164 or conv.lead.phone
        phone_data = PhoneService.normalize_to_e164(raw_phone)
        e164_phone = phone_data["e164"] if phone_data else raw_phone

        is_sim = settings.SIMULATION_MODE if force_simulation is None else force_simulation
        wa_message_id: Optional[str] = None

        if is_sim or not settings.WHATSAPP_CLOUD_ENABLED:
            import time, random
            wa_message_id = f"wamid.SIM_RETRY_{int(time.time())}_{random.randint(100000, 999999)}"
        else:
            client = WhatsAppCloudApiClient()
            if msg.message_type == MessageType.TEXT and msg.body:
                dispatch_res = await client.send_text_message(to_phone=e164_phone, message_text=msg.body)
            elif msg.message_type in (MessageType.IMAGE, MessageType.DOCUMENT) and msg.media_url:
                dispatch_res = await client.send_media_message(
                    to_phone=e164_phone,
                    media_type=msg.message_type.value.lower(),
                    media_url=msg.media_url,
                    caption=msg.media_caption or msg.body,
                    filename=msg.media_filename,
                )
            else:
                dispatch_res = await client.send_text_message(to_phone=e164_phone, message_text=msg.body or "")

            if not dispatch_res.get("success"):
                error_msg = dispatch_res.get("error") or "Yeniden gönderim başarısız oldu."
                msg.status = ConversationMessageStatus.FAILED
                msg.error_message = error_msg
                await db.commit()
                raise HTTPException(status_code=502, detail=f"WhatsApp mesajı gönderilemedi: {error_msg}")

            wa_message_id = dispatch_res.get("message_id")

        now_utc = datetime.now(timezone.utc)
        msg.wa_message_id = wa_message_id
        msg.status = ConversationMessageStatus.SENT
        msg.error_code = None
        msg.error_message = None
        msg.updated_at = now_utc
        conv.last_message_at = now_utc

        await db.commit()
        await db.refresh(msg)

        # Broadcast status update
        await ws_manager.broadcast({
            "event": "message_status_updated",
            "message_id": msg.id,
            "wa_message_id": msg.wa_message_id,
            "conversation_id": conv.id,
            "status": "SENT",
            "timestamp": now_utc.isoformat(),
        })

        return msg

    @classmethod
    async def send_outbound_media(
        cls,
        db: AsyncSession,
        conversation_id: int,
        media_type: str,  # "IMAGE" or "DOCUMENT"
        media_url: str,
        caption: Optional[str] = None,
        filename: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        force_simulation: Optional[bool] = None,
    ) -> Message:
        """
        Sends an outbound media message (Image / Document) with validation and persistence.
        """
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.lead))
        )
        conv = (await db.execute(stmt)).scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Diyalog bulunamadı.")
        if conv.status == ConversationStatus.CLOSED:
            raise HTTPException(status_code=400, detail="Kapalı bir diyaloğa medya gönderilemez.")

        lead = conv.lead
        raw_phone = lead.phone_e164 or lead.phone
        phone_data = PhoneService.normalize_to_e164(raw_phone)
        e164_phone = phone_data["e164"] if phone_data else raw_phone

        clean_type = media_type.upper()
        if clean_type not in ("IMAGE", "DOCUMENT"):
            clean_type = "IMAGE"

        # Check idempotency
        if idempotency_key:
            from backend.app.services.whatsapp_outbound_service import _idempotency_cache
            if idempotency_key in _idempotency_cache:
                _, cached_msg_id = _idempotency_cache[idempotency_key]
                cached_msg = await db.get(Message, cached_msg_id)
                if cached_msg:
                    return cached_msg

        is_sim = settings.SIMULATION_MODE if force_simulation is None else force_simulation
        wa_message_id: Optional[str] = None

        if is_sim or not settings.WHATSAPP_CLOUD_ENABLED:
            import time, random
            wa_message_id = f"wamid.SIM_MEDIA_{int(time.time())}_{random.randint(100000, 999999)}"
        else:
            client = WhatsAppCloudApiClient()
            dispatch_res = await client.send_media_message(
                to_phone=e164_phone,
                media_type=clean_type.lower(),
                media_url=media_url,
                caption=caption,
                filename=filename,
            )
            if not dispatch_res.get("success"):
                error_msg = dispatch_res.get("error") or "Medya gönderilemedi."
                raise HTTPException(status_code=502, detail=f"Medya gönderilemedi: {error_msg}")
            wa_message_id = dispatch_res.get("message_id")

        now_utc = datetime.now(timezone.utc)
        m_type_enum = MessageType.IMAGE if clean_type == "IMAGE" else MessageType.DOCUMENT

        outbound_msg = Message(
            conversation_id=conv.id,
            direction=MessageDirection.OUTBOUND,
            message_type=m_type_enum,
            body=caption or (filename or "Medya"),
            media_id=media_url,
            media_caption=caption,
            media_filename=filename,
            media_mime_type="image/jpeg" if clean_type == "IMAGE" else "application/pdf",
            wa_message_id=wa_message_id,
            sender_phone="BUSINESS",
            recipient_phone=e164_phone,
            status=ConversationMessageStatus.SENT,
            external_timestamp=now_utc,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db.add(outbound_msg)

        conv.last_message_at = now_utc
        conv.updated_at = now_utc
        if conv.status == ConversationStatus.ARCHIVED:
            conv.status = ConversationStatus.ACTIVE

        await db.commit()
        await db.refresh(outbound_msg)

        if idempotency_key:
            import time
            from backend.app.services.whatsapp_outbound_service import _idempotency_cache
            _idempotency_cache[idempotency_key] = (time.time(), outbound_msg.id)

        await ws_manager.broadcast({
            "event": "outbound_message_sent",
            "message_id": outbound_msg.id,
            "wa_message_id": outbound_msg.wa_message_id,
            "conversation_id": conv.id,
            "lead_id": lead.id,
            "lead_name": lead.name,
            "recipient_phone": e164_phone,
            "direction": "OUTBOUND",
            "message_type": clean_type,
            "status": "SENT",
            "media_url": media_url,
            "caption": caption,
            "created_at": outbound_msg.created_at.isoformat(),
        })

        return outbound_msg

