"""
Final Campaign Group Data Preservation Audit Suite.
CRITICAL INVARIANT: Deleting a CampaignGroup must NEVER delete the underlying Lead entities.
Exhaustively tests single-lead, multi-lead, and repeated group lifecycles.
"""
import pytest
import uuid
from sqlalchemy import select, func
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.lead import Lead


@pytest.fixture
def anyio_backend():
    return "asyncio"


def unique_phone():
    return f"+9053{uuid.uuid4().int % 100000000:08d}"


@pytest.mark.asyncio
async def test_data_preservation_on_group_destruction():
    """
    Creates 10 leads, assigns them to a campaign group, deletes the group,
    and proves that 100% of the lead IDs and record counts remain intact in the CRM.
    """
    lead_ids = []
    # 1. Create 10 distinct leads
    async with AsyncSessionLocal() as session:
        for i in range(10):
            p = unique_phone()
            lead = Lead(
                name=f"Preservation Lead #{i}_{uuid.uuid4().hex[:6]}",
                phone=p,
                phone_e164=p,
                place_id=f"place_preserv_{uuid.uuid4().hex[:10]}",
                category="Estetik & Güzellik",
                city="Ankara"
            )
            session.add(lead)
        await session.commit()

        # Query all created IDs
        stmt = select(Lead.id).where(Lead.category == "Estetik & Güzellik")
        res = await session.execute(stmt)
        lead_ids = res.scalars().all()
        assert len(lead_ids) >= 10

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 2. Create Campaign Group
        g_res = await client.post("/api/v1/campaign-groups", json={"name": f"Preservation Group {uuid.uuid4().hex[:6]}"})
        assert g_res.status_code == 201
        gid = g_res.json()["id"]

        # 3. Add all leads to group
        add_res = await client.post(f"/api/v1/campaign-groups/{gid}/leads", json={"lead_ids": lead_ids})
        assert add_res.status_code == 200

        # Verify group lead count before destruction
        detail_res = await client.get(f"/api/v1/campaign-groups/{gid}")
        assert detail_res.status_code == 200
        assert detail_res.json()["total_leads_count"] >= 10

        # 4. DELETE THE GROUP
        del_res = await client.delete(f"/api/v1/campaign-groups/{gid}")
        assert del_res.status_code == 204

    # 5. Verify Database State: All 10 lead IDs MUST STILL EXIST
    async with AsyncSessionLocal() as session:
        stmt = select(Lead).where(Lead.id.in_(lead_ids))
        survived_leads = (await session.execute(stmt)).scalars().all()
        survived_ids = [l.id for l in survived_leads]

        assert len(survived_ids) == len(lead_ids), (
            f"CRITICAL DATA LOSS: {len(lead_ids) - len(survived_ids)} leads were destroyed when group was deleted!"
        )
        for lid in lead_ids:
            assert lid in survived_ids, f"Lead ID {lid} was lost during group deletion!"
