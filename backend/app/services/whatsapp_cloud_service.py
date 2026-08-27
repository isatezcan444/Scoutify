"""
WhatsApp Cloud API Application Service.

Encapsulates application-level orchestration for Meta WhatsApp Cloud API webhooks:
- Ingests incoming messages and correlates them with existing Leads.
- Handles Opt-Out keyword detection and Blacklist creation.
- Updates MessageLog statuses (SENT -> DELIVERED -> READ -> FAILED).
- Enforces event idempotency to prevent duplicate mutations.
- Broadcasts real-time updates over WebSockets.
"""
import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.lead import Lead, LeadStatus
from backend.app.models.blacklist import Blacklist
from backend.app.models.message_log import MessageLog, MessageStatus
from backend.app.schemas.whatsapp_cloud import ParsedIncomingMessage, ParsedStatusUpdate
from backend.app.services.phone_service import PhoneService
from backend.app.api.v1.websocket import ws_manager

logger = logging.getLogger(__name__)

# Single source of truth for opt-out keywords
OPT_OUT_PATTERN = re.compile(
    r"\b(istemiyorum|iptal|sil|stop|unsubscribe|rahats[ıi]z\s+etmeyin|mesaj\s+atmay[ıi]n)\b",
    re.IGNORECASE
)

# Status precedence rank to prevent out-of-order webhook delivery status regressions
STATUS_PRECEDENCE = {
    MessageStatus.PENDING: 1,
    MessageStatus.QUEUED: 2,
    MessageStatus.SENDING: 3,
    MessageStatus.SENT: 4,
    MessageStatus.DELIVERED: 5,
    MessageStatus.READ: 6,
    MessageStatus.REPLIED: 7,
    MessageStatus.FAILED: 99,
    MessageStatus.CANCELLED: 99,
}


class WhatsAppCloudService:
    """Application service for Meta WhatsApp Cloud events."""

    @staticmethod
    async def process_incoming_message(
        db: AsyncSession,
        msg: ParsedIncomingMessage,
    ) -> Dict[str, Any]:
        """
        Processes an incoming WhatsApp message received via Meta Webhook.
        Idempotent: Duplicate message IDs will not create duplicate blacklist entries or corrupted notes.
        """
        phone_data = PhoneService.normalize_to_e164(msg.sender_phone)
        e164 = phone_data["e164"] if phone_data else (
            f"+{msg.sender_phone}" if not msg.sender_phone.startswith("+") else msg.sender_phone
        )

        logger.info(
            f"[WhatsAppCloudService] Processing incoming message: "
            f"id={msg.message_id}, sender={e164}, len={len(msg.text)}"
        )

        # 1. Correlate with Lead
        lead_stmt = select(Lead).where(
            (Lead.phone_e164 == e164) | (Lead.phone == e164)
        )
        lead_res = await db.execute(lead_stmt)
        lead = lead_res.scalar_one_or_none()

        ts_str = msg.timestamp.strftime("%Y-%m-%d %H:%M")
        new_note_entry = f"WhatsApp Yanıtı ({ts_str}): {msg.text}"

        if lead:
            # Avoid duplicate note appending if identical webhook received
            if not lead.notes or new_note_entry not in lead.notes:
                lead.notes = f"{lead.notes}\n{new_note_entry}" if lead.notes else new_note_entry

            if lead.status not in (LeadStatus.INTERESTED, LeadStatus.UNSUBSCRIBED):
                lead.status = LeadStatus.REPLIED

        # 2. Correlate with most recent MessageLog for this phone
        log_stmt = (
            select(MessageLog)
            .where(MessageLog.target_phone == e164)
            .order_by(MessageLog.id.desc())
            .limit(1)
        )
        log_res = await db.execute(log_stmt)
        msg_log = log_res.scalar_one_or_none()

        if msg_log:
            msg_log.reply_received = True
            msg_log.reply_text = msg.text
            msg_log.replied_at = msg.timestamp
            if msg_log.status != MessageStatus.READ:
                msg_log.status = MessageStatus.REPLIED

        # 3. Check Opt-Out Keyword
        is_opt_out = bool(OPT_OUT_PATTERN.search(msg.text))
        if is_opt_out:
            # Check if already blacklisted
            bl_stmt = select(Blacklist).where(Blacklist.phone_e164 == e164)
            bl_res = await db.execute(bl_stmt)
            existing_bl = bl_res.scalar_one_or_none()

            if not existing_bl:
                bl = Blacklist(
                    phone_e164=e164,
                    reason="OPT_OUT_KEYWORD",
                    notes=f"Cloud Webhook: '{msg.text[:100]}'",
                )
                db.add(bl)
                logger.info(f"[WhatsAppCloudService] Opt-out detected. Blacklisted phone: {e164}")

            if lead:
                lead.status = LeadStatus.UNSUBSCRIBED

        await db.commit()

        # 4. Broadcast Realtime WebSocket Event
        await ws_manager.broadcast({
            "event": "inbound_reply",
            "provider": "meta_cloud",
            "message_id": msg.message_id,
            "phone": e164,
            "sender_name": msg.sender_name or (lead.name if lead else "Bilinmeyen"),
            "message": msg.text,
            "is_opt_out": is_opt_out,
            "timestamp": msg.timestamp.isoformat(),
        })

        return {
            "status": "processed",
            "phone": e164,
            "lead_id": lead.id if lead else None,
            "is_opt_out": is_opt_out,
        }

    @staticmethod
    async def process_status_update(
        db: AsyncSession,
        status: ParsedStatusUpdate,
    ) -> Dict[str, Any]:
        """
        Updates MessageLog status based on Meta Cloud API webhook status update.
        Enforces monotonic status progression (e.g. will not downgrade READ to DELIVERED).
        """
        logger.info(
            f"[WhatsAppCloudService] Status update received: "
            f"message_id={status.message_id}, status={status.status.value}, recipient={status.recipient_phone}"
        )

        stmt = (
            select(MessageLog)
            .where(MessageLog.wa_message_id == status.message_id)
            .order_by(MessageLog.id.desc())
        )
        res = await db.execute(stmt)
        msg_log = res.scalars().first()

        if not msg_log:
            logger.debug(
                f"[WhatsAppCloudService] MessageLog not found for wa_message_id={status.message_id} "
                f"(might be external or untracked message)."
            )
            return {"status": "untracked_message", "message_id": status.message_id}

        current_rank = STATUS_PRECEDENCE.get(msg_log.status, 0)
        new_rank = STATUS_PRECEDENCE.get(status.status, 0)

        # Monotonic status protection: Do not regress status unless it's a terminal error
        if status.status != MessageStatus.FAILED and new_rank < current_rank:
            logger.info(
                f"[WhatsAppCloudService] Skipping status regression from {msg_log.status.value} "
                f"to {status.status.value} for message_id={status.message_id}"
            )
            return {
                "status": "skipped_regression",
                "current_status": msg_log.status.value,
                "message_id": status.message_id,
            }

        msg_log.status = status.status
        if status.status == MessageStatus.FAILED and status.error_message:
            msg_log.error_reason = f"Meta Error ({status.error_code}): {status.error_message}"

        await db.commit()

        # Broadcast status update
        await ws_manager.broadcast({
            "event": "message_status_updated",
            "provider": "meta_cloud",
            "message_id": status.message_id,
            "status": status.status.value,
            "target_phone": msg_log.target_phone,
            "lead_id": msg_log.lead_id,
            "campaign_id": msg_log.campaign_id,
            "timestamp": status.timestamp.isoformat(),
        })

        return {
            "status": "updated",
            "message_id": status.message_id,
            "new_status": status.status.value,
        }
