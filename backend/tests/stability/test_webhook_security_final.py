"""
Final Webhook Security & Zero Side-Effect Audit Suite.
Verifies cryptographic HMAC-SHA256 signature verification, Meta GET verification handshake,
and proves that unauthorized or tampered webhook requests produce ZERO database side effects.
"""
import pytest
import hmac
import hashlib
import json
import uuid
from sqlalchemy import select, func
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.message import Message
from backend.app.models.lead import Lead


@pytest.fixture
def anyio_backend():
    return "asyncio"


def compute_signature(payload_bytes: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


@pytest.mark.asyncio
async def test_webhook_get_handshake_security_matrix():
    """
    Tests Meta Webhook GET verification handshake with valid, invalid, and missing tokens.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Valid handshake
        res = await client.get(
            "/api/v1/whatsapp/cloud-webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": settings.WHATSAPP_CLOUD_WEBHOOK_VERIFY_TOKEN,
                "hub.challenge": "123456789"
            }
        )
        assert res.status_code == 200
        assert res.text == "123456789"

        # 2. Invalid verify token
        res = await client.get(
            "/api/v1/whatsapp/cloud-webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token_attack",
                "hub.challenge": "123456789"
            }
        )
        assert res.status_code == 403

        # 3. Missing verify token
        res = await client.get(
            "/api/v1/whatsapp/cloud-webhook",
            params={"hub.mode": "subscribe", "hub.challenge": "123456789"}
        )
        assert res.status_code in (400, 403, 422)


@pytest.mark.asyncio
async def test_webhook_tampered_payload_zero_database_side_effects():
    """
    Proves that tampered or invalidly signed webhook payloads are rejected (401)
    and produce EXACTLY ZERO database side effects (no new Messages or Leads).
    """
    secret = "production_audit_secret_key_123"
    settings.WHATSAPP_CLOUD_APP_SECRET = secret

    # Count DB state before attack
    async with AsyncSessionLocal() as session:
        msg_count_before = (await session.execute(select(func.count(Message.id)))).scalar()
        lead_count_before = (await session.execute(select(func.count(Lead.id)))).scalar()

    valid_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "12345", "phone_number_id": "98765"},
                            "messages": [
                                {
                                    "from": "905559998877",
                                    "id": f"wamid_attack_{uuid.uuid4().hex[:12]}",
                                    "timestamp": "1700000000",
                                    "text": {"body": "Malicious payload injection attempt"},
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    payload_bytes = json.dumps(valid_payload).encode("utf-8")
    valid_sig = compute_signature(payload_bytes, secret)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Attack 1: Forged signature
        res1 = await client.post(
            "/api/v1/whatsapp/cloud-webhook",
            content=payload_bytes,
            headers={"X-Hub-Signature-256": "sha256=0000000000000000000000000000000000000000000000000000000000000000"}
        )
        assert res1.status_code == 401

        # Attack 2: Tampered body with old signature
        tampered_bytes = payload_bytes.replace(b"Malicious", b"Modified_")
        res2 = await client.post(
            "/api/v1/whatsapp/cloud-webhook",
            content=tampered_bytes,
            headers={"X-Hub-Signature-256": valid_sig}
        )
        assert res2.status_code == 401

        # Attack 3: Missing signature header
        res3 = await client.post(
            "/api/v1/whatsapp/cloud-webhook",
            content=payload_bytes
        )
        assert res3.status_code == 401

    # Verify zero database side effects
    async with AsyncSessionLocal() as session:
        msg_count_after = (await session.execute(select(func.count(Message.id)))).scalar()
        lead_count_after = (await session.execute(select(func.count(Lead.id)))).scalar()

        assert msg_count_after == msg_count_before, "Tampered webhook created an unauthorized message!"
        assert lead_count_after == lead_count_before, "Tampered webhook created an unauthorized lead!"
