"""
Meta WhatsApp Cloud API Webhook Endpoints.

Provides:
- GET verification endpoint for Meta webhook handshake challenge.
- POST event receiver endpoint with optional X-Hub-Signature-256 HMAC validation,
  DTO parsing, and application service dispatch.
"""
import hmac
import hashlib
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.schemas.whatsapp_cloud import parse_meta_webhook_payload
from backend.app.services.whatsapp_cloud_service import WhatsAppCloudService

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_meta_signature(raw_body: bytes, signature_header: Optional[str], app_secret: str) -> bool:
    """
    Validates the X-Hub-Signature-256 header sent by Meta using HMAC-SHA256.
    """
    if not app_secret:
        # Fail-closed: without a configured secret no signature can be
        # trusted. Configure WHATSAPP_CLOUD_APP_SECRET to enable the webhook.
        logger.warning("[MetaWebhook] Rejecting webhook: WHATSAPP_CLOUD_APP_SECRET is not configured.")
        return False

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_hash = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    expected_signature = f"sha256={expected_hash}"
    return hmac.compare_digest(signature_header, expected_signature)


@router.get("", summary="Meta Webhook Verification Handshake")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
):
    """
    Meta Webhook Verification Endpoint (GET).
    
    Meta will call this endpoint when configuring the webhook URL in the App Dashboard.
    If the verify token and mode match, returns the challenge string with HTTP 200.
    """
    configured_token = settings.WHATSAPP_CLOUD_WEBHOOK_VERIFY_TOKEN

    if configured_token and hub_mode == "subscribe" and hub_verify_token == configured_token and hub_challenge:
        logger.info("[WhatsAppCloudWebhook] Webhook successfully verified with Meta.")
        # Meta expects the raw integer/string challenge in plain text
        return Response(content=str(hub_challenge), media_type="text/plain", status_code=200)

    logger.warning(
        f"[WhatsAppCloudWebhook] Webhook verification failed. "
        f"mode={hub_mode}, verify_token_match={hub_verify_token == configured_token}"
    )
    raise HTTPException(
        status_code=403,
        detail="Webhook verification failed: Invalid verify token or mode.",
    )


@router.post("", summary="Meta Webhook Event Ingestion")
async def handle_webhook_event(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    db: AsyncSession = Depends(get_db),
):
    """
    Meta Webhook Event Ingestion Endpoint (POST).
    
    Receives incoming WhatsApp messages and outbound message status updates from Meta Graph API.
    Validates X-Hub-Signature-256 when WHATSAPP_CLOUD_APP_SECRET is configured.
    """
    raw_body = await request.body()

    # 1. Cryptographic signature check (X-Hub-Signature-256)
    if settings.WHATSAPP_CLOUD_APP_SECRET:
        if not verify_meta_signature(raw_body, x_hub_signature_256, settings.WHATSAPP_CLOUD_APP_SECRET):
            logger.warning("[WhatsAppCloudWebhook] Rejected webhook with invalid X-Hub-Signature-256.")
            raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    # 2. Parse JSON payload safely
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"[WhatsAppCloudWebhook] Malformed JSON payload: {e}")
        # Always return 200 OK to Meta to avoid webhook unsubscription, with error note
        return {"status": "error", "message": "Malformed JSON"}

    # 3. Separate Meta DTO from internal Domain models
    incoming_messages, status_updates = parse_meta_webhook_payload(payload)

    # 4. Process incoming messages
    for msg in incoming_messages:
        try:
            await WhatsAppCloudService.process_incoming_message(db=db, msg=msg)
        except Exception as e:
            logger.error(f"[WhatsAppCloudWebhook] Error processing incoming message {msg.message_id}: {e}")

    # 5. Process status updates
    for status in status_updates:
        try:
            await WhatsAppCloudService.process_status_update(db=db, status=status)
        except Exception as e:
            logger.error(f"[WhatsAppCloudWebhook] Error processing status update {status.message_id}: {e}")

    # Meta requires a prompt 200 OK response
    return {
        "status": "success",
        "processed_messages": len(incoming_messages),
        "processed_statuses": len(status_updates),
    }
