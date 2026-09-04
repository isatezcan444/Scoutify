import uuid
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal


def unique_phone(prefix: str = "+90532") -> str:
    """Generate a unique random E.164 Turkish phone number.

    Uses the 532 mobile block (libphonenumber-valid for any subscriber part)
    so tests exercise the strict validation path with genuinely valid numbers
    instead of relying on the removed best-effort fallback.
    """
    import phonenumbers

    for _ in range(100):
        candidate = f"{prefix}{uuid.uuid4().int % 10000000:07d}"
        try:
            if phonenumbers.is_valid_number(phonenumbers.parse(candidate, "TR")):
                return candidate
        except Exception:
            continue
    raise AssertionError("Could not generate a valid test phone number")


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
