import uuid
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal, get_db
from backend.app.models.lead import Lead, LeadStatus
from backend.app.models.campaign import Campaign, CampaignStatus
from backend.app.models.campaign_group import CampaignGroup
from backend.app.models.blacklist import Blacklist


def unique_phone(prefix: str = "+90555") -> str:
    """Generate a unique random E.164 Turkish phone number."""
    return f"{prefix}{uuid.uuid4().int % 100000000:08d}"


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provides an isolated AsyncClient for REST API integration testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator:
    """Provides a fresh database session."""
    async with AsyncSessionLocal() as session:
        yield session


class WhatsAppCallTracker:
    """Tracks all attempted WhatsApp dispatches to ensure Zero-Send safety invariants."""
    def __init__(self):
        self.calls = []

    def record_call(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def reset(self):
        self.calls.clear()


@pytest.fixture
def whatsapp_spy():
    """Mocks WhatsApp sender mechanisms and records all calls."""
    tracker = WhatsAppCallTracker()
    mock_send = AsyncMock(side_effect=lambda *a, **kw: tracker.record_call(*a, **kw) or {"success": True, "message_id": "test_msg_id"})
    
    with patch("backend.app.services.whatsapp_sender.SimulatedSender.send_message", mock_send), \
         patch("backend.app.services.whatsapp_sender.GatewaySender.send_message", mock_send), \
         patch("backend.app.services.whatsapp_sender.CloudApiSender.send_message", mock_send), \
         patch("backend.app.services.whatsapp_cloud_client.WhatsAppCloudApiClient.send_text_message", mock_send):
        yield tracker
