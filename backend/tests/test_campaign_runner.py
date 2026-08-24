import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models.campaign import Campaign, CampaignStatus
from backend.app.services.campaign_runner import CampaignRunner


async def get_in_memory_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False), engine


@pytest.mark.asyncio
async def test_campaign_runner_idempotency_and_state():
    session_maker, engine = await get_in_memory_db()
    async with session_maker() as db:
        camp = Campaign(
            name="Test Outreach",
            message_template="Merhaba {name}",
            min_delay_seconds=10,
            max_delay_seconds=20,
            status=CampaignStatus.DRAFT
        )
        db.add(camp)
        await db.commit()
        await db.refresh(camp)

        # Non-running status check
        assert CampaignRunner.is_campaign_running(camp.id) is False

    await engine.dispose()
