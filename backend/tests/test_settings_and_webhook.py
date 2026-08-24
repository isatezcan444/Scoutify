import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.config import settings


@pytest.mark.asyncio
async def test_get_and_patch_antiban_settings():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET default settings
        res = await client.get("/api/v1/settings/antiban")
        assert res.status_code == 200
        data = res.json()
        assert "min_delay_seconds" in data
        assert "daily_message_limit" in data

        # PATCH update settings
        patch_payload = {
            "preset": "ultra_safe",
            "min_delay_seconds": 60,
            "max_delay_seconds": 150,
            "typing_delay_seconds": 5,
            "daily_message_limit": 35,
            "working_hours_enabled": True,
            "working_hours_start": "09:30",
            "working_hours_end": "18:00"
        }
        patch_res = await client.patch("/api/v1/settings/antiban", json=patch_payload)
        assert patch_res.status_code == 200
        updated = patch_res.json()
        assert updated["preset"] == "ultra_safe"
        assert updated["min_delay_seconds"] == 60
        assert updated["daily_message_limit"] == 35


@pytest.mark.asyncio
async def test_webhook_secret_authorization():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request with invalid secret should return 401
        invalid_res = await client.post(
            "/api/v1/whatsapp/webhook/inbound",
            headers={"X-Webhook-Secret": "wrong-secret"},
            json={"phone": "+905321112233", "message": "Merhaba"}
        )
        assert invalid_res.status_code == 401

        # Request with valid secret
        valid_res = await client.post(
            "/api/v1/whatsapp/webhook/inbound",
            headers={"X-Webhook-Secret": settings.WA_GATEWAY_WEBHOOK_SECRET},
            json={"phone": "+905321112233", "message": "Teşekkürler bilgi aldım"}
        )
        assert valid_res.status_code == 200
        assert valid_res.json()["status"] == "success"
