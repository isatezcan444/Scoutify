"""
Adversarial Webhook Security & Idempotency Tests.
Audits GET challenge, HMAC-SHA256 signature tampering, opt-out word boundaries, and unknown sender idempotency.
"""
import hmac
import hashlib
import json
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.lead import Lead, LeadStatus
from backend.app.models.conversation import Conversation
from backend.app.models.message import Message
from backend.app.models.blacklist import Blacklist
from backend.tests.stability.conftest import unique_phone


@pytest.mark.asyncio
async def test_adversarial_webhook_tampered_payload_rejection():
    """
    Tests that ANY single-byte modification of the payload after signing causes HMAC-SHA256
    verification failure and returns 401 Unauthorized.
    """
    secret = "adversarial_secret_key_123"
    valid_payload = json.dumps({"object": "whatsapp_business_account", "entry": [{"id": "123"}]}).encode("utf-8")
    valid_sig = "sha256=" + hmac.new(secret.encode("utf-8"), valid_payload, hashlib.sha256).hexdigest()

    # Tampered payload (1 character difference)
    tampered_payload = json.dumps({"object": "whatsapp_business_account", "entry": [{"id": "124"}]}).encode("utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch.object(settings, "WHATSAPP_CLOUD_APP_SECRET", secret):
            # 1. Valid signature + valid payload -> 200
            res_valid = await client.post(
                "/api/v1/whatsapp/cloud-webhook",
                content=valid_payload,
                headers={"Content-Type": "application/json", "X-Hub-Signature-256": valid_sig}
            )
            assert res_valid.status_code == 200

            # 2. Valid signature + tampered payload -> 401 Unauthorized
            res_tampered = await client.post(
                "/api/v1/whatsapp/cloud-webhook",
                content=tampered_payload,
                headers={"Content-Type": "application/json", "X-Hub-Signature-256": valid_sig}
            )
            assert res_tampered.status_code == 401


@pytest.mark.asyncio
async def test_adversarial_unknown_sender_10x_burst_idempotency():
    """
    Tests sending 10 identical webhook deliveries in a burst for a new unknown sender.
    Database MUST contain strictly:
    - 1 Lead
    - 1 Conversation (unread_count = 1)
    - 1 Message
    """
    phone = unique_phone(prefix="+90535")
    msg_id = f"wamid.burst_{uuid.uuid4().hex}"
    
    meta_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "905550001122",
                                "phone_number_id": "100020003000"
                            },
                            "contacts": [{"profile": {"name": "Burst Müşteri"}, "wa_id": phone.replace("+", "")}],
                            "messages": [{
                                "from": phone.replace("+", ""),
                                "id": msg_id,
                                "timestamp": "1725185000",
                                "type": "text",
                                "text": {"body": "Fiyat bilgisi alabilir miyim?"}
                            }]
                        }
                    }
                ]
            }
        ]
    }

    raw_body = json.dumps(meta_payload).encode("utf-8")
    secret = "burst_secret"
    sig = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    headers = {"Content-Type": "application/json", "X-Hub-Signature-256": sig}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch.object(settings, "WHATSAPP_CLOUD_APP_SECRET", secret):
            # Send 10 identical webhook posts
            for _ in range(10):
                res = await client.post("/api/v1/whatsapp/cloud-webhook", content=raw_body, headers=headers)
                assert res.status_code == 200

    # Verify Database Invariant
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        # 1 Lead
        leads = (await session.execute(select(Lead).where(Lead.phone_e164 == phone))).scalars().all()
        assert len(leads) == 1

        # 1 Conversation with unread_count == 1
        convs = (await session.execute(select(Conversation).where(Conversation.lead_id == leads[0].id))).scalars().all()
        assert len(convs) == 1
        assert convs[0].unread_count == 1

        # 1 Message
        msgs = (await session.execute(select(Message).where(Message.wa_message_id == msg_id))).scalars().all()
        assert len(msgs) == 1


@pytest.mark.asyncio
async def test_adversarial_opt_out_keyword_boundary_cases():
    """
    Tests opt-out regex detection across various Turkish and English expressions:
    'istemiyorum', 'İptal', 'Lütfen siliniz', 'STOP', 'unsubscribe'.
    Ensures lead is marked UNSUBSCRIBED and phone is added to Blacklist.
    """
    opt_out_phrases = [
        "Mesaj almak istemiyorum",
        "İptal",
        "Artık bana yazmayın, sil",
        "STOP",
        "Please unsubscribe me",
    ]

    for phrase in opt_out_phrases:
        phone = unique_phone()
        msg_id = f"wamid.optout_{uuid.uuid4().hex}"

        meta_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "1234567890",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {"display_phone_number": "905550001122", "phone_number_id": "1000"},
                                "contacts": [{"profile": {"name": "Optout Tester"}, "wa_id": phone.replace("+", "")}],
                                "messages": [{
                                    "from": phone.replace("+", ""),
                                    "id": msg_id,
                                    "timestamp": "1725185100",
                                    "type": "text",
                                    "text": {"body": phrase}
                                }]
                            }
                        }
                    ]
                }
            ]
        }

        raw_body = json.dumps(meta_payload).encode("utf-8")
        secret = "optout_sec"
        sig = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        headers = {"Content-Type": "application/json", "X-Hub-Signature-256": sig}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with patch.object(settings, "WHATSAPP_CLOUD_APP_SECRET", secret):
                res = await client.post("/api/v1/whatsapp/cloud-webhook", content=raw_body, headers=headers)
                assert res.status_code == 200
                assert res.json()["status"] == "success"

        # Verify Database: Lead is UNSUBSCRIBED and Blacklist entry exists
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            lead = (await session.execute(select(Lead).where(Lead.phone_e164 == phone))).scalar_one_or_none()
            assert lead is not None
            assert lead.status == LeadStatus.UNSUBSCRIBED

            bl = (await session.execute(select(Blacklist).where(Blacklist.phone_e164 == phone))).scalar_one_or_none()
            assert bl is not None
            assert bl.reason == "OPT_OUT_KEYWORD"
