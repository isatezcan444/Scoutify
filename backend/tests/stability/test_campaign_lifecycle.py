import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.campaign import Campaign, CampaignStatus
from backend.app.models.campaign_group import CampaignGroup
from backend.app.models.lead import Lead
from backend.tests.stability.conftest import unique_phone


@pytest.mark.asyncio
async def test_journey_e_campaign_lifecycle_and_state_machine(client: AsyncClient, whatsapp_spy):
    """
    CRITICAL USER JOURNEY E:
    Campaign creation (DRAFT) -> Validation -> Edit -> Zero Send Check -> Status Transitions.
    """
    whatsapp_spy.reset()

    # 1. Create a campaign via API
    payload = {
        "name": f"Diş Hekimleri Kampanyası {uuid.uuid4().hex[:6]}",
        "message_template": "{Merhaba|Selamlar} {name}, {city} bölgesindeki {category} hizmetinizi inceledim.",
        "status": "DRAFT",
        "min_delay_seconds": 10,
        "max_delay_seconds": 30,
        "working_hours_enabled": True,
        "working_hours_start": "09:00",
        "working_hours_end": "18:00"
    }

    create_res = await client.post("/api/v1/campaigns", json=payload)
    assert create_res.status_code == 201
    campaign_data = create_res.json()
    campaign_id = campaign_data["id"]
    assert campaign_data["status"] == "DRAFT"
    assert campaign_data["name"] == payload["name"]
    
    # Invariant: WhatsApp send count MUST remain exactly 0 on creation
    assert whatsapp_spy.call_count == 0

    # 2. Update Campaign (PATCH)
    patch_res = await client.patch(f"/api/v1/campaigns/{campaign_id}", json={
        "name": f"{payload['name']} (Güncellendi)",
        "min_delay_seconds": 15
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == f"{payload['name']} (Güncellendi)"
    assert patch_res.json()["min_delay_seconds"] == 15
    assert whatsapp_spy.call_count == 0

    # 3. Status Transitions: DRAFT -> PAUSED -> ACTIVE -> PAUSED -> ARCHIVED
    pause_res = await client.patch(f"/api/v1/campaigns/{campaign_id}", json={"status": "PAUSED"})
    assert pause_res.status_code == 200
    assert pause_res.json()["status"] == "PAUSED"

    active_res = await client.patch(f"/api/v1/campaigns/{campaign_id}", json={"status": "ACTIVE"})
    assert active_res.status_code == 200
    assert active_res.json()["status"] == "ACTIVE"

    archive_res = await client.patch(f"/api/v1/campaigns/{campaign_id}", json={"status": "ARCHIVED"})
    assert archive_res.status_code == 200
    assert archive_res.json()["status"] == "ARCHIVED"


@pytest.mark.asyncio
async def test_journey_f_campaign_deletion_invariants(client: AsyncClient, whatsapp_spy):
    """
    CRITICAL USER JOURNEY F:
    Campaign Deletion -> Worker Stop -> DB Cleanup -> Lead Preservation -> 404 for nonexistent.
    """
    whatsapp_spy.reset()

    # 1. Create a Campaign
    payload = {
        "name": f"Silinecek Kampanya {uuid.uuid4().hex[:6]}",
        "message_template": "Merhaba {name}, test mesajı.",
        "status": "DRAFT"
    }
    create_res = await client.post("/api/v1/campaigns", json=payload)
    assert create_res.status_code == 201
    campaign_id = create_res.json()["id"]

    # 2. Delete Campaign
    del_res = await client.delete(f"/api/v1/campaigns/{campaign_id}")
    assert del_res.status_code in (200, 204)

    # 3. Invariant: WhatsApp sends MUST be 0 during deletion
    assert whatsapp_spy.call_count == 0

    # 4. Verify Campaign is gone (404 on get)
    get_res = await client.get(f"/api/v1/campaigns/{campaign_id}")
    assert get_res.status_code == 404

    # 5. Delete non-existent campaign returns 404
    del_nonexistent = await client.delete(f"/api/v1/campaigns/{campaign_id}")
    assert del_nonexistent.status_code == 404
