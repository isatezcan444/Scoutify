import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.lead import Lead, LeadStatus
from backend.app.models.conversation import Conversation, ConversationStatus
from backend.app.models.message import Message, MessageDirection, MessageType, ConversationMessageStatus
from backend.app.models.message_log import MessageStatus
from backend.app.services.whatsapp_cloud_service import WhatsAppCloudService
from backend.app.schemas.whatsapp_cloud import ParsedIncomingMessage, ParsedStatusUpdate


from backend.app.core.database import Base, engine, AsyncSessionLocal
from backend.app.core.migrations import ensure_conversations_columns


async def clean_db(db):
    await ensure_conversations_columns(engine)
    await db.execute(Message.__table__.delete())
    await db.execute(Conversation.__table__.delete())
    await db.commit()


@pytest.mark.asyncio
async def test_inbound_message_creates_conversation_and_message():
    """Verifies that an incoming WhatsApp message creates Conversation and Message entities."""
    test_phone = "+905411112233"
    async with AsyncSessionLocal() as db_session:
        await clean_db(db_session)
        await db_session.execute(Lead.__table__.delete().where(Lead.phone_e164 == test_phone))
        await db_session.commit()

        lead = Lead(
            name="Conversation Test Lead",
            phone=test_phone,
            phone_e164=test_phone,
            status=LeadStatus.NEW,
        )
        db_session.add(lead)
        await db_session.commit()
        await db_session.refresh(lead)

        msg = ParsedIncomingMessage(
            message_id="wamid.CONV_TEST_001",
            sender_phone=test_phone,
            sender_name="Conversation Test Lead",
            text="Hello Scoutify, this is my first message.",
            timestamp=datetime.now(timezone.utc),
        )

        result = await WhatsAppCloudService.process_incoming_message(db_session, msg)
        assert result["status"] == "processed"
        assert result["lead_id"] == lead.id
        assert result["conversation_id"] is not None

        # Check Conversation
        conv = await db_session.get(Conversation, result["conversation_id"])
        assert conv is not None
        assert conv.lead_id == lead.id
        assert conv.channel == "WHATSAPP"
        assert conv.status == ConversationStatus.ACTIVE

        # Check Message
        stmt = select(Message).where(Message.conversation_id == conv.id)
        messages = (await db_session.execute(stmt)).scalars().all()
        assert len(messages) == 1
        assert messages[0].wa_message_id == "wamid.CONV_TEST_001"
        assert messages[0].direction == MessageDirection.INBOUND
        assert messages[0].status == ConversationMessageStatus.RECEIVED
        assert messages[0].body == "Hello Scoutify, this is my first message."

        # Check Lead status
        await db_session.refresh(lead)
        assert lead.status == LeadStatus.REPLIED
        assert "Hello Scoutify" in lead.notes


@pytest.mark.asyncio
async def test_multiple_messages_reuse_same_conversation():
    """Verifies that sequential messages from the same Lead attach to the single active Conversation thread."""
    test_phone = "+905412223344"
    async with AsyncSessionLocal() as db_session:
        await clean_db(db_session)
        await db_session.execute(Lead.__table__.delete().where(Lead.phone_e164 == test_phone))
        await db_session.commit()

        lead = Lead(
            name="Multi Message Lead",
            phone=test_phone,
            phone_e164=test_phone,
            status=LeadStatus.NEW,
        )
        db_session.add(lead)
        await db_session.commit()

        msg1 = ParsedIncomingMessage(
            message_id="wamid.MULTI_001",
            sender_phone=test_phone,
            sender_name="Multi Message Lead",
            text="Message 1",
            timestamp=datetime.now(timezone.utc),
        )
        msg2 = ParsedIncomingMessage(
            message_id="wamid.MULTI_002",
            sender_phone=test_phone,
            sender_name="Multi Message Lead",
            text="Message 2",
            timestamp=datetime.now(timezone.utc),
        )

        res1 = await WhatsAppCloudService.process_incoming_message(db_session, msg1)
        res2 = await WhatsAppCloudService.process_incoming_message(db_session, msg2)

        assert res1["status"] == "processed"
        assert res2["status"] == "processed"
        assert res1["conversation_id"] == res2["conversation_id"]

        # Verify 1 Conversation with 2 Messages
        conv_id = res1["conversation_id"]
        conv_stmt = select(Conversation).where(Conversation.lead_id == lead.id)
        convs = (await db_session.execute(conv_stmt)).scalars().all()
        assert len(convs) == 1

        msg_stmt = select(Message).where(Message.conversation_id == conv_id).order_by(Message.id.asc())
        messages = (await db_session.execute(msg_stmt)).scalars().all()
        assert len(messages) == 2
        assert messages[0].body == "Message 1"
        assert messages[1].body == "Message 2"


@pytest.mark.asyncio
async def test_idempotent_duplicate_message_rejected():
    """Verifies that sending an identical message_id twice does not create duplicate Message entities."""
    test_phone = "+905413334455"
    async with AsyncSessionLocal() as db_session:
        await clean_db(db_session)
        await db_session.execute(Lead.__table__.delete().where(Lead.phone_e164 == test_phone))
        await db_session.commit()

        lead = Lead(
            name="Idempotency Lead",
            phone=test_phone,
            phone_e164=test_phone,
            status=LeadStatus.NEW,
        )
        db_session.add(lead)
        await db_session.commit()

        msg = ParsedIncomingMessage(
            message_id="wamid.IDEMPOTENT_DUPLICATE_999",
            sender_phone=test_phone,
            sender_name="Idempotency Lead",
            text="Original Message",
            timestamp=datetime.now(timezone.utc),
        )

        res1 = await WhatsAppCloudService.process_incoming_message(db_session, msg)
        assert res1["status"] == "processed"

        # Replay identical message
        res2 = await WhatsAppCloudService.process_incoming_message(db_session, msg)
        assert res2["status"] == "idempotent_duplicate"

        # Assert exactly 1 message exists in DB
        msg_stmt = select(Message).where(Message.wa_message_id == "wamid.IDEMPOTENT_DUPLICATE_999")
        messages = (await db_session.execute(msg_stmt)).scalars().all()
        assert len(messages) == 1


@pytest.mark.asyncio
async def test_status_update_on_conversation_message():
    """Verifies status progression (SENT -> DELIVERED -> READ) on Message entity."""
    test_phone = "+905414445566"
    async with AsyncSessionLocal() as db_session:
        await clean_db(db_session)
        await db_session.execute(Lead.__table__.delete().where(Lead.phone_e164 == test_phone))
        await db_session.commit()

        lead = Lead(
            name="Status Lead",
            phone=test_phone,
            phone_e164=test_phone,
            status=LeadStatus.CONTACTED,
        )
        db_session.add(lead)
        await db_session.commit()

        conv = Conversation(lead_id=lead.id, channel="WHATSAPP")
        db_session.add(conv)
        await db_session.commit()

        outbound_msg = Message(
            conversation_id=conv.id,
            direction=MessageDirection.OUTBOUND,
            message_type=MessageType.TEXT,
            body="Outbound test",
            wa_message_id="wamid.OUTBOUND_STATUS_001",
            sender_phone="BUSINESS",
            recipient_phone=test_phone,
            status=ConversationMessageStatus.SENT,
        )
        db_session.add(outbound_msg)
        await db_session.commit()

        # 1. Update to DELIVERED
        status_delivered = ParsedStatusUpdate(
            message_id="wamid.OUTBOUND_STATUS_001",
            recipient_phone=test_phone,
            status=MessageStatus.DELIVERED,
            timestamp=datetime.now(timezone.utc),
        )
        await WhatsAppCloudService.process_status_update(db_session, status_delivered)
        await db_session.refresh(outbound_msg)
        assert outbound_msg.status == ConversationMessageStatus.DELIVERED

        # 2. Update to READ
        status_read = ParsedStatusUpdate(
            message_id="wamid.OUTBOUND_STATUS_001",
            recipient_phone=test_phone,
            status=MessageStatus.READ,
            timestamp=datetime.now(timezone.utc),
        )
        await WhatsAppCloudService.process_status_update(db_session, status_read)
        await db_session.refresh(outbound_msg)
        assert outbound_msg.status == ConversationMessageStatus.READ

        # 3. Delayed DELIVERED should NOT downgrade READ
        await WhatsAppCloudService.process_status_update(db_session, status_delivered)
        await db_session.refresh(outbound_msg)
        assert outbound_msg.status == ConversationMessageStatus.READ


@pytest.mark.asyncio
async def test_conversations_rest_api():
    """Verifies REST endpoints /api/v1/conversations, /{id}, and /lead/{lead_id}."""
    test_phone = "+905415556677"
    async with AsyncSessionLocal() as db_session:
        await clean_db(db_session)
        await db_session.execute(Lead.__table__.delete().where(Lead.phone_e164 == test_phone))
        await db_session.commit()

        lead = Lead(
            name="REST API Lead",
            phone=test_phone,
            phone_e164=test_phone,
            status=LeadStatus.NEW,
        )
        db_session.add(lead)
        await db_session.commit()
        await db_session.refresh(lead)
        lead_id = lead.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get or init lead conversation
        res_lead = await client.get(f"/api/v1/conversations/lead/{lead_id}")
        assert res_lead.status_code == 200
        conv_data = res_lead.json()
        assert conv_data["lead_id"] == lead_id
        conv_id = conv_data["id"]

        # List conversations
        res_list = await client.get("/api/v1/conversations")
        assert res_list.status_code == 200
        convs = res_list.json()
        assert any(c["id"] == conv_id for c in convs)

        # Get conversation detail
        res_detail = await client.get(f"/api/v1/conversations/{conv_id}")
        assert res_detail.status_code == 200
        assert res_detail.json()["id"] == conv_id


@pytest.mark.asyncio
async def test_conversation_message_pagination():
    """Verifies cursor pagination on messages within a conversation."""
    test_phone = "+905416667788"
    async with AsyncSessionLocal() as db_session:
        await clean_db(db_session)
        await db_session.execute(Lead.__table__.delete().where(Lead.phone_e164 == test_phone))
        await db_session.commit()

        lead = Lead(
            name="Pagination Test Lead",
            phone=test_phone,
            phone_e164=test_phone,
            status=LeadStatus.NEW,
        )
        db_session.add(lead)
        await db_session.commit()
        await db_session.refresh(lead)

        conv = Conversation(
            lead_id=lead.id,
            channel="WHATSAPP",
            status=ConversationStatus.ACTIVE,
        )
        db_session.add(conv)
        await db_session.commit()
        await db_session.refresh(conv)

        # Create 15 messages (1 to 15)
        for i in range(1, 16):
            m = Message(
                conversation_id=conv.id,
                direction=MessageDirection.INBOUND if i % 2 == 1 else MessageDirection.OUTBOUND,
                message_type=MessageType.TEXT,
                body=f"Message {i:02d}",
                wa_message_id=f"wamid.PAG_{i:02d}",
                sender_phone=test_phone if i % 2 == 1 else "BUSINESS",
                recipient_phone="BUSINESS" if i % 2 == 1 else test_phone,
                status=ConversationMessageStatus.RECEIVED if i % 2 == 1 else ConversationMessageStatus.SENT,
            )
            db_session.add(m)
        await db_session.commit()
        conv_id = conv.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Page 1: Latest 5 messages (limit=5)
        res1 = await client.get(f"/api/v1/conversations/{conv_id}?limit=5")
        assert res1.status_code == 200
        data1 = res1.json()
        assert len(data1["messages"]) == 5
        assert data1["has_more"] is True
        # Chronological: Message 11, 12, 13, 14, 15
        assert data1["messages"][0]["body"] == "Message 11"
        assert data1["messages"][-1]["body"] == "Message 15"
        oldest_id_p1 = data1["messages"][0]["id"]

        # Page 2: Older messages before oldest_id_p1
        res2 = await client.get(f"/api/v1/conversations/{conv_id}?limit=5&before={oldest_id_p1}")
        assert res2.status_code == 200
        data2 = res2.json()
        assert len(data2["messages"]) == 5
        assert data2["has_more"] is True
        # Chronological: Message 06, 07, 08, 09, 10
        assert data2["messages"][0]["body"] == "Message 06"
        assert data2["messages"][-1]["body"] == "Message 10"
        oldest_id_p2 = data2["messages"][0]["id"]

        # Page 3: Oldest remaining messages
        res3 = await client.get(f"/api/v1/conversations/{conv_id}?limit=5&before={oldest_id_p2}")
        assert res3.status_code == 200
        data3 = res3.json()
        assert len(data3["messages"]) == 5
        assert data3["has_more"] is False
        assert data3["messages"][0]["body"] == "Message 01"
        assert data3["messages"][-1]["body"] == "Message 05"


@pytest.mark.asyncio
async def test_conversation_unread_count_and_mark_as_read():
    """Verifies that inbound messages increment unread_count and POST /read resets it to 0."""
    test_phone = "+905417778899"
    async with AsyncSessionLocal() as db_session:
        await clean_db(db_session)
        await db_session.execute(Lead.__table__.delete().where(Lead.phone_e164 == test_phone))
        await db_session.commit()

        lead = Lead(
            name="Unread Test Lead",
            phone=test_phone,
            phone_e164=test_phone,
            status=LeadStatus.NEW,
        )
        db_session.add(lead)
        await db_session.commit()
        await db_session.refresh(lead)

        # Inbound Message 1
        msg1 = ParsedIncomingMessage(
            message_id="wamid.UNREAD_001",
            sender_phone=test_phone,
            sender_name="Unread Test Lead",
            text="First unread message",
            timestamp=datetime.now(timezone.utc),
        )
        res1 = await WhatsAppCloudService.process_incoming_message(db_session, msg1)
        conv_id = res1["conversation_id"]

        # Inbound Message 2
        msg2 = ParsedIncomingMessage(
            message_id="wamid.UNREAD_002",
            sender_phone=test_phone,
            sender_name="Unread Test Lead",
            text="Second unread message",
            timestamp=datetime.now(timezone.utc),
        )
        await WhatsAppCloudService.process_incoming_message(db_session, msg2)

        # Verify in DB unread_count == 2
        conv = await db_session.get(Conversation, conv_id)
        assert conv.unread_count == 2

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Mark as read via POST /api/v1/conversations/{conv_id}/read
        res_read = await client.post(f"/api/v1/conversations/{conv_id}/read")
        assert res_read.status_code == 200
        assert res_read.json()["unread_count"] == 0

        # Verify DB unread_count == 0
        async with AsyncSessionLocal() as db_session:
            conv_db = await db_session.get(Conversation, conv_id)
            assert conv_db.unread_count == 0
            assert conv_db.last_read_at is not None
