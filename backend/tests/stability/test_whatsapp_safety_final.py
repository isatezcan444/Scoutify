"""
Final WhatsApp Safety & Zero-Early-Send Audit Suite.
Verifies that all non-authorized operations (discovery, preview, group mutation, draft edits)
produce EXACTLY ZERO WhatsApp send calls.
Verifies full 4-state sender routing priority matrix.
"""
import pytest
import uuid
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.services.whatsapp_sender import (
    get_whatsapp_sender,
    SimulatedSender,
    GatewaySender,
    CloudApiSender,
)
from backend.app.services.whatsapp_cloud_client import WhatsAppCloudApiClient


@pytest.fixture
def anyio_backend():
    return "asyncio"


class WhatsAppDispatcherSpy:
    def __init__(self):
        self.call_count = 0
        self.dispatched_messages = []

    async def mock_send(self, *args, **kwargs):
        self.call_count += 1
        self.dispatched_messages.append({"args": args, "kwargs": kwargs})
        return {"success": True, "message_id": f"spy_{uuid.uuid4().hex[:8]}", "is_simulated": True}


@pytest.mark.asyncio
async def test_zero_early_whatsapp_send_matrix(monkeypatch):
    """
    Exhaustively tests all non-launch APIs and asserts zero WhatsApp sender invocations.
    """
    spy = WhatsAppDispatcherSpy()
    monkeypatch.setattr(SimulatedSender, "send_message", spy.mock_send)
    monkeypatch.setattr(GatewaySender, "send_message", spy.mock_send)
    monkeypatch.setattr(CloudApiSender, "send_message", spy.mock_send)
    monkeypatch.setattr(WhatsAppCloudApiClient, "send_text_message", spy.mock_send)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Lead creation
        test_phone = f"+9053{uuid.uuid4().int % 100000000:08d}"
        l_res = await client.post(
            "/api/v1/leads",
            json={"name": f"Safety Test Lead {uuid.uuid4().hex[:6]}", "phone": test_phone}
        )
        assert l_res.status_code == 201
        lid = l_res.json()["id"]
        assert spy.call_count == 0, "Lead creation triggered WhatsApp dispatch!"

        # 2. Campaign Group creation & Lead addition
        g_res = await client.post(
            "/api/v1/campaign-groups",
            json={"name": f"Safety Group {uuid.uuid4().hex[:6]}"}
        )
        assert g_res.status_code == 201
        gid = g_res.json()["id"]
        await client.post(f"/api/v1/campaign-groups/{gid}/leads", json={"lead_ids": [lid]})
        assert spy.call_count == 0, "Group member addition triggered WhatsApp dispatch!"

        # 3. Campaign Draft creation & Spintax Preview
        c_res = await client.post(
            "/api/v1/campaigns",
            json={
                "name": "Safety Draft Campaign",
                "message_template": "{Merhaba|Selam} {business_name}, özel teklifimiz var.",
                "campaign_group_id": gid
            }
        )
        assert c_res.status_code == 201
        cid = c_res.json()["id"]
        assert spy.call_count == 0, "Campaign creation triggered WhatsApp dispatch!"

        # 4. Spintax Preview
        prev_res = await client.post(
            "/api/v1/campaigns/spintax/preview",
            json={"template": "{Merhaba|Selam} {business_name}", "sample_data": {"business_name": "Test"}}
        )
        assert prev_res.status_code == 200
        assert spy.call_count == 0, "Spintax preview triggered WhatsApp dispatch!"

        # 5. Template Generation
        gen_res = await client.post(
            "/api/v1/campaigns/generate-message",
            json={"communication_goal": "SERVICE_PROMOTION", "offer_title": "Dental Randevu", "target_category": "Diş Hekimi"}
        )
        assert gen_res.status_code == 200
        assert spy.call_count == 0, "Template generation triggered WhatsApp dispatch!"

        # 6. Campaign Group deletion
        del_res = await client.delete(f"/api/v1/campaign-groups/{gid}")
        assert del_res.status_code == 204
        assert spy.call_count == 0, "Group deletion triggered WhatsApp dispatch!"

    assert spy.call_count == 0, f"Critical safety invariant violated: {spy.call_count} dispatches occurred!"


def test_whatsapp_sender_routing_priority_matrix():
    """
    Verifies all 4 combinations of SIMULATION_MODE and WHATSAPP_CLOUD_ENABLED.
    """
    orig_sim = settings.SIMULATION_MODE
    orig_cloud = settings.WHATSAPP_CLOUD_ENABLED
    try:
        # 1. True + True -> SimulatedSender
        settings.SIMULATION_MODE = True
        settings.WHATSAPP_CLOUD_ENABLED = True
        sender = get_whatsapp_sender()
        assert isinstance(sender, SimulatedSender)

        # 2. True + False -> SimulatedSender
        settings.SIMULATION_MODE = True
        settings.WHATSAPP_CLOUD_ENABLED = False
        sender = get_whatsapp_sender()
        assert isinstance(sender, SimulatedSender)

        # 3. False + True -> CloudApiSender
        settings.SIMULATION_MODE = False
        settings.WHATSAPP_CLOUD_ENABLED = True
        sender = get_whatsapp_sender()
        assert isinstance(sender, CloudApiSender)

        # 4. False + False -> GatewaySender
        settings.SIMULATION_MODE = False
        settings.WHATSAPP_CLOUD_ENABLED = False
        sender = get_whatsapp_sender()
        assert isinstance(sender, GatewaySender)

    finally:
        settings.SIMULATION_MODE = orig_sim
        settings.WHATSAPP_CLOUD_ENABLED = orig_cloud
