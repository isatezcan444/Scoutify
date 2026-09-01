import pytest
from httpx import AsyncClient
from unittest.mock import patch

from backend.app.core.config import settings
from backend.app.services.spintax_service import SpintaxService
from backend.app.services.message_strategy_service import MessageStrategyService
from backend.app.services.whatsapp_sender import (
    get_whatsapp_sender,
    SimulatedSender,
    GatewaySender,
    CloudApiSender
)


def test_journey_h_spintax_and_template_generation():
    """
    CRITICAL USER JOURNEY H:
    Template generation, Spintax variation expansion, and placeholder replacement.
    """
    # 1. Spintax parsing
    template = "{Merhaba|Selamlar|İyi günler} {name}, {city} bölgesindeki işletmenize ulaşıyoruz."
    sample_1 = SpintaxService.spin(template)
    sample_2 = SpintaxService.spin(template)
    
    # Must expand valid options and not leave unparsed pipes
    assert any(g in sample_1 for g in ["Merhaba", "Selamlar", "İyi günler"])
    assert "|" not in sample_1

    # 2. Lead field substitution
    rendered = SpintaxService.render_template(
        template=template,
        lead_data={"name": "Ataşehir Diş", "city": "İstanbul", "category": "Diş Hekimi"}
    )
    assert "Ataşehir Diş" in rendered
    assert "İstanbul" in rendered
    assert "{name}" not in rendered
    assert "{city}" not in rendered
    assert "{" not in rendered and "}" not in rendered


def test_journey_j_whatsapp_sender_routing_matrix():
    """
    CRITICAL USER JOURNEY J:
    Verifies that get_whatsapp_sender resolves exact concrete classes based on config matrix.
    """
    # Combination 1: Simulation Mode True -> SimulatedSender
    with patch.object(settings, "SIMULATION_MODE", True), \
         patch.object(settings, "WHATSAPP_CLOUD_ENABLED", True):
        sender = get_whatsapp_sender()
        assert isinstance(sender, SimulatedSender)

    with patch.object(settings, "SIMULATION_MODE", True), \
         patch.object(settings, "WHATSAPP_CLOUD_ENABLED", False):
        sender = get_whatsapp_sender()
        assert isinstance(sender, SimulatedSender)

    # Combination 2: Simulation Mode False, Cloud API Enabled -> CloudApiSender
    with patch.object(settings, "SIMULATION_MODE", False), \
         patch.object(settings, "WHATSAPP_CLOUD_ENABLED", True):
        sender = get_whatsapp_sender()
        assert isinstance(sender, CloudApiSender)

    # Combination 3: Simulation Mode False, Cloud API Disabled -> GatewaySender
    with patch.object(settings, "SIMULATION_MODE", False), \
         patch.object(settings, "WHATSAPP_CLOUD_ENABLED", False):
        sender = get_whatsapp_sender()
        assert isinstance(sender, GatewaySender)


@pytest.mark.asyncio
async def test_simulated_sender_never_masks_as_real_network_call():
    """Proves SimulatedSender explicitly marks dispatches with is_simulated: True."""
    sender = SimulatedSender()
    res = await sender.send_message(
        session_name="test_session",
        phone_e164="+905551112233",
        message_text="Test simulation"
    )
    assert res["success"] is True
    assert res["is_simulated"] is True
    assert res["error"] is None
    assert str(res["message_id"]).startswith("sim_")


@pytest.mark.asyncio
async def test_gateway_sender_fails_truthfully_on_network_error():
    """
    Architectural Invariant 1.1: No False Positives.
    GatewaySender MUST return success: False when gateway is unreachable.
    """
    sender = GatewaySender(gateway_url="http://127.0.0.1:59999_nonexistent")
    res = await sender.send_message(
        session_name="test_session",
        phone_e164="+905551112233",
        message_text="Test gateway fail"
    )
    assert res["success"] is False
    assert res["is_simulated"] is False
    assert res["message_id"] is None
    assert res["error"] is not None
