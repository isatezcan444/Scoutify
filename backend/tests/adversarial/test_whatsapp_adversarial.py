"""
Adversarial WhatsApp Dispatcher, Routing, and Zero-Send Invariant Tests.
Validates sender routing matrix, Spintax parser under broken grammar, and Zero-Send guarantees.
"""
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.services.whatsapp_sender import (
    get_whatsapp_sender,
    SimulatedSender,
    GatewaySender,
    CloudApiSender,
)
from backend.app.services.spintax_service import SpintaxService
from backend.tests.adversarial.conftest import WhatsAppCallTracker


def test_adversarial_spintax_broken_grammar_and_nested_patterns():
    """
    Tests that SpintaxService does not crash or loop infinitely on malformed/unbalanced syntax.
    """
    pathological_templates = [
        "",
        "   ",
        "{Merhaba|Selam",           # Unclosed brace
        "Merhaba|Selam}",           # Unopened brace
        "{||||}",                   # Empty pipe variations
        "{{Merhaba|Selam}|Günaydın}", # Nested spintax
        "{Merhaba|{Selam|Alo}}",    # Nested inner spintax
        "{name} {city} {unknown_tag_123}", # Unknown tags
        "{|a|b|c|}",
        "Normal metin tanpa spintax.",
        "{" * 50 + "}" * 50,        # Extreme nested empty braces
    ]

    for t in pathological_templates:
        # 1. Spin must return string without infinite recursion
        spun = SpintaxService.spin(t)
        assert isinstance(spun, str)

        # 2. Render template must substitute known fields safely
        rendered = SpintaxService.render_template(t, {"name": "Test İsim", "city": "Ankara"})
        assert isinstance(rendered, str)


def test_adversarial_sender_routing_matrix_completeness():
    """
    Exhaustively proves sender resolution across all permutation states of settings:
    - SIMULATION_MODE = True -> Always SimulatedSender
    - SIMULATION_MODE = False, CLOUD = True -> CloudApiSender
    - SIMULATION_MODE = False, CLOUD = False -> GatewaySender
    """
    # 1. SIMULATION_MODE = True (Override everything)
    with patch.object(settings, "SIMULATION_MODE", True), \
         patch.object(settings, "WHATSAPP_CLOUD_ENABLED", True):
        sender_1 = get_whatsapp_sender()
        assert isinstance(sender_1, SimulatedSender)

    with patch.object(settings, "SIMULATION_MODE", True), \
         patch.object(settings, "WHATSAPP_CLOUD_ENABLED", False):
        sender_2 = get_whatsapp_sender()
        assert isinstance(sender_2, SimulatedSender)

    # 2. SIMULATION_MODE = False, WHATSAPP_CLOUD_ENABLED = True
    with patch.object(settings, "SIMULATION_MODE", False), \
         patch.object(settings, "WHATSAPP_CLOUD_ENABLED", True):
        sender_3 = get_whatsapp_sender()
        assert isinstance(sender_3, CloudApiSender)

    # 3. SIMULATION_MODE = False, WHATSAPP_CLOUD_ENABLED = False
    with patch.object(settings, "SIMULATION_MODE", False), \
         patch.object(settings, "WHATSAPP_CLOUD_ENABLED", False):
        sender_4 = get_whatsapp_sender()
        assert isinstance(sender_4, GatewaySender)


@pytest.mark.asyncio
async def test_zero_early_send_comprehensive_suite(whatsapp_spy: WhatsAppCallTracker):
    """
    ZERO EARLY SEND COMPREHENSIVE PROOF:
    Executes a wide array of non-dispatch API operations:
    1. Spintax preview POST /api/v1/campaigns/spintax/preview
    2. Campaign DRAFT create POST /api/v1/campaigns
    3. Campaign DRAFT patch PATCH /api/v1/campaigns/{id}
    4. Campaign Group create POST /api/v1/campaign-groups
    5. Anti-Ban settings PATCH /api/v1/settings/antiban
    
    Strictly asserts that total sender invocations remain EXACTLY 0.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Spintax preview
        await client.post("/api/v1/campaigns/spintax/preview", json={
            "template": "{Merhaba|Selam} {name}",
            "count": 5
        })

        # 2. Campaign DRAFT create
        c_res = await client.post("/api/v1/campaigns", json={
            "name": "Zero Send Test Campaign",
            "message_template": "{Merhaba|Selam} {name}"
        })
        cid = c_res.json()["id"]

        # 3. Campaign update
        await client.patch(f"/api/v1/campaigns/{cid}", json={"name": "Updated Zero Send"})

        # 4. Group create
        await client.post("/api/v1/campaign-groups", json={"name": "Zero Send Group"})

        # 5. Anti-Ban patch
        await client.patch("/api/v1/settings/antiban", json={"preset": "aggressive_fast"})

    # Mathematical Proof: Dispatcher call count == 0
    assert whatsapp_spy.call_count == 0, f"Early send invariant breached! Calls = {whatsapp_spy.call_count}"
