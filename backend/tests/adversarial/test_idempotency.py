"""
Adversarial Idempotency Test Suite.
Verifies that repeating identical operations N times produces the exact identical final state
and does not trigger unintended side effects, state drifts, or counter inflations.
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func

from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.lead import Lead, LeadStatus
from backend.app.models.campaign import Campaign
from backend.app.models.campaign_group import CampaignGroup
from backend.tests.stability.conftest import unique_phone


@pytest.mark.asyncio
async def test_adversarial_lead_mutation_idempotency():
    """
    Tests that repeating PATCH /api/v1/leads/{id} 5 times with identical payload:
    - Returns 200 OK on all calls
    - Database entity retains exactly the patched values
    """
    phone = unique_phone()
    async with AsyncSessionLocal() as session:
        lead = Lead(name="Idempotent Lead", phone=phone, phone_e164=phone, is_whatsapp_eligible=True, status=LeadStatus.NEW)
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        lid = lead.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        patch_payload = {
            "status": "INTERESTED",
            "notes": "İdempotent Test Notu"
        }

        for _ in range(5):
            res = await client.patch(f"/api/v1/leads/{lid}", json=patch_payload)
            assert res.status_code == 200
            assert res.json()["status"] == "INTERESTED"
            assert res.json()["notes"] == "İdempotent Test Notu"

    async with AsyncSessionLocal() as session:
        saved = await session.get(Lead, lid)
        assert saved.status == LeadStatus.INTERESTED
        assert saved.notes == "İdempotent Test Notu"


@pytest.mark.asyncio
async def test_adversarial_antiban_patch_idempotency():
    """
    Tests that repeating PATCH /api/v1/settings/antiban 5 times with identical parameters:
    - Returns 200 OK on all calls
    - Database SystemSetting table retains exactly 1 record for 'antiban_config'
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "preset": "safe_gradual",
            "min_delay_seconds": 60,
            "max_delay_seconds": 120,
            "typing_delay_seconds": 10,
            "daily_message_limit": 25,
            "working_hours_enabled": True,
            "working_hours_start": "09:30",
            "working_hours_end": "17:30"
        }

        for _ in range(5):
            res = await client.patch("/api/v1/settings/antiban", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["preset"] == "safe_gradual"
            assert data["daily_message_limit"] == 25

    # Verify Database has exactly 1 setting row
    async with AsyncSessionLocal() as session:
        from backend.app.models.system_settings import SystemSetting
        stmt = select(func.count(SystemSetting.id)).where(SystemSetting.key == "antiban_config")
        cnt = (await session.execute(stmt)).scalar()
        assert cnt == 1
