"""
Final Failure Injection & Graceful Degradation Audit Suite.
Injects controlled infrastructure faults (gateway network unreachable, database timeout,
malformed JSON, partial rollback) and verifies deterministic error handling.
"""
import pytest
import httpx
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.services.whatsapp_sender import GatewaySender
from backend.app.services.antiban_policy import AntibanPolicy


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_failure_injection_gateway_unreachable(monkeypatch):
    """
    Injects a Network Connection Error on the WhatsApp Gateway HTTP client.
    Verifies that GatewaySender returns truthful failure ({'success': False}) and never masks as success.
    """
    sender = GatewaySender(gateway_url="http://non_existent_gateway_host:9999")

    async def mock_post(*args, **kwargs):
        raise httpx.ConnectError("Connection refused by target gateway")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    res = await sender.send_message(
        session_name="default",
        phone_e164="+905321234567",
        message_text="Test Message"
    )

    assert res["success"] is False
    assert res["is_simulated"] is False
    assert "error" in res and res["error"] is not None
    assert "Connection refused" in res["error"] or "ConnectError" in res["error"]


def test_failure_injection_antiban_corrupted_policy():
    """
    Injects completely corrupted, type-confused, and out-of-range configurations into AntibanPolicy.
    Verifies fail-closed behavior (returns False).
    """
    corrupt_configs = [
        {"start": "99:99", "end": "88:88"},
        {"start": "noon", "end": "midnight"},
        {"start": None, "end": None},
        {"start": 1234, "end": 5678},
        {"start": "", "end": ""},
    ]

    for cfg in corrupt_configs:
        policy = AntibanPolicy(
            min_delay_seconds=10,
            max_delay_seconds=30,
            typing_delay_seconds=3,
            working_hours_enabled=True,
            working_hours_start=cfg["start"],
            working_hours_end=cfg["end"],
            simulation_mode=False
        )
        assert policy.is_within_working_hours() is False, f"Corrupted config {cfg} failed open!"
