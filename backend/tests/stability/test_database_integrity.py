import pytest
from sqlalchemy import select, func, text

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.lead import Lead
from backend.app.models.campaign import Campaign
from backend.app.models.campaign_group import CampaignGroup, campaign_group_leads
from backend.app.models.conversation import Conversation
from backend.app.models.message import Message


@pytest.mark.asyncio
async def test_forensic_orphan_group_memberships():
    """Proves there are zero orphan records in the campaign_group_leads junction table."""
    async with AsyncSessionLocal() as session:
        # 1. Memberships pointing to non-existent Lead
        orphan_lead_query = (
            select(campaign_group_leads)
            .outerjoin(Lead, campaign_group_leads.c.lead_id == Lead.id)
            .where(Lead.id == None)
        )
        orphan_leads = (await session.execute(orphan_lead_query)).fetchall()
        assert len(orphan_leads) == 0, f"Found {len(orphan_leads)} orphan memberships pointing to non-existent Leads"

        # 2. Memberships pointing to non-existent CampaignGroup
        orphan_group_query = (
            select(campaign_group_leads)
            .outerjoin(CampaignGroup, campaign_group_leads.c.group_id == CampaignGroup.id)
            .where(CampaignGroup.id == None)
        )
        orphan_groups = (await session.execute(orphan_group_query)).fetchall()
        assert len(orphan_groups) == 0, f"Found {len(orphan_groups)} orphan memberships pointing to non-existent Groups"


@pytest.mark.asyncio
async def test_forensic_duplicate_memberships_scan():
    """Proves there are zero duplicate (group_id, lead_id) pairs in the database."""
    async with AsyncSessionLocal() as session:
        dup_query = (
            select(
                campaign_group_leads.c.group_id,
                campaign_group_leads.c.lead_id,
                func.count().label("cnt")
            )
            .group_by(campaign_group_leads.c.group_id, campaign_group_leads.c.lead_id)
            .having(func.count() > 1)
        )
        duplicates = (await session.execute(dup_query)).fetchall()
        assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate group membership pairs"


@pytest.mark.asyncio
async def test_forensic_orphan_messages_scan():
    """Proves all messages belong to an active, valid conversation."""
    async with AsyncSessionLocal() as session:
        orphan_msg_query = (
            select(Message)
            .outerjoin(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.id == None)
        )
        orphan_msgs = (await session.execute(orphan_msg_query)).scalars().all()
        assert len(orphan_msgs) == 0, f"Found {len(orphan_msgs)} orphan messages without conversations"
