import pytest
from backend.app.services.whatsapp_sender import SimulatedSender, GatewaySender, get_whatsapp_sender
from backend.app.services.antiban_policy import AntibanPolicy, parse_hhmm, gaussian_jitter_seconds
from datetime import time


@pytest.mark.asyncio
async def test_simulated_sender():
    sender = SimulatedSender()
    res = await sender.send_message(
        session_name="test_session",
        phone_e164="+905321112233",
        message_text="Merhaba!",
        typing_seconds=1
    )
    assert res["success"] is True
    assert res["is_simulated"] is True
    assert res["error"] is None
    assert res["message_id"].startswith("sim_")


@pytest.mark.asyncio
async def test_gateway_sender_connection_error():
    # Attempting to call an unreachable gateway returns truthful failure, not fake success!
    sender = GatewaySender(gateway_url="http://127.0.0.1:59999")
    res = await sender.send_message(
        session_name="test_session",
        phone_e164="+905321112233",
        message_text="Merhaba!"
    )
    assert res["success"] is False
    assert res["is_simulated"] is False
    assert "Gateway bağlantı hatası" in res["error"] or "ConnectError" in res["error"]


def test_antiban_policy_fail_closed():
    class DummyCampaign:
        min_delay_seconds = 30
        max_delay_seconds = 60
        typing_delay_seconds = 3
        working_hours_enabled = True
        working_hours_start = "invalid_time"
        working_hours_end = "18:00"

    policy = AntibanPolicy.from_campaign(DummyCampaign())
    # Fail-closed: invalid working hour returns False
    assert policy.is_within_working_hours(now=time(12, 0)) is False


def test_antiban_policy_working_hours():
    class DummyCampaign:
        min_delay_seconds = 10
        max_delay_seconds = 20
        typing_delay_seconds = 2
        working_hours_enabled = True
        working_hours_start = "09:00"
        working_hours_end = "18:00"

    policy = AntibanPolicy.from_campaign(DummyCampaign())
    assert policy.is_within_working_hours(now=time(10, 30)) is True
    assert policy.is_within_working_hours(now=time(20, 0)) is False


def test_gaussian_jitter_clamped():
    for _ in range(100):
        val = gaussian_jitter_seconds(30, 90)
        assert 30 <= val <= 90
