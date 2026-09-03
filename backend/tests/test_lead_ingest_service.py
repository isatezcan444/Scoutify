import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.models.lead import Lead, LeadStatus
from backend.app.models.blacklist import Blacklist
from backend.app.services.lead_ingest_service import LeadIngestService


async def get_in_memory_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return sessionmaker(engine, class_=AsyncSession, expire_on_commit=False), engine


@pytest.mark.asyncio
async def test_lead_ingest_creates_and_deduplicates():
    session_maker, engine = await get_in_memory_db()
    async with session_maker() as db:
        raw_data = [
            {
                "name": "Kadıköy Diş Kliniği",
                "category": "Diş Kliniği",
                "phone": "05321112233",
                "city": "İstanbul",
                "district": "Kadıköy",
                "place_id": "gmaps_kdk_01"
            },
            {
                "name": "Telefonsuz Butik",
                "category": "Giyim",
                "phone": None,
                "city": "İzmir",
                "district": "Konak",
                "place_id": "gmaps_konak_02"
            }
        ]

        leads, new_c, upd_c = await LeadIngestService.ingest_leads(db, raw_data)
        assert new_c == 2
        assert upd_c == 0
        assert len(leads) == 2

        # Verify first lead normalized phone
        assert leads[0].phone_e164 == "+905321112233"
        assert leads[0].is_whatsapp_eligible is True

        # Verify second lead with missing phone is NULL, NOT fake +90000 number!
        assert leads[1].phone_e164 is None
        assert leads[1].is_whatsapp_eligible is False

        # Second ingestion with same place_id should update, not create duplicate
        leads_2, new_c2, upd_c2 = await LeadIngestService.ingest_leads(db, raw_data)
        assert new_c2 == 0
        assert upd_c2 == 2

    await engine.dispose()


@pytest.mark.asyncio
async def test_lead_ingest_handles_blacklist():
    session_maker, engine = await get_in_memory_db()
    async with session_maker() as db:
        bl = Blacklist(phone_e164="+905329998877", reason="Opt-out test")
        db.add(bl)
        await db.commit()

        raw = [{
            "name": "Kara Liste Adayı",
            "phone": "+905329998877",
            "city": "Ankara",
            "district": "Çankaya"
        }]

        leads, new_c, upd_c = await LeadIngestService.ingest_leads(db, raw)
        assert new_c == 1
        assert leads[0].status == LeadStatus.UNSUBSCRIBED

    await engine.dispose()


@pytest.mark.asyncio
async def test_merge_heals_name_prefixed_address():
    """Rows stored before the pd[18] prefix strip carry 'Name, street...'.
    A re-scrape touching the same business must normalize the stored
    address (pure prefix removal, no new content injected)."""
    session_maker, engine = await get_in_memory_db()
    async with session_maker() as db:
        db.add(Lead(
            name="Mozaik Dent",
            city="İstanbul",
            district="Ataşehir",
            phone="Belirtilmemiş",
            phone_e164=None,
            place_id="gmaps_mozaik_01",
            address="Mozaik Dent, Atatürk, Meriç Cd. NO: 21/35",
        ))
        await db.commit()

        raw = [{
            "name": "Mozaik Dent",
            "city": "İstanbul",
            "district": "Ataşehir",
            "place_id": "gmaps_mozaik_01",
            "phone": None,
            "phone_e164": None,
            "address": "Atatürk, Meriç Cd. NO: 21/35",
        }]
        leads, new_c, upd_c = await LeadIngestService.ingest_leads(db, raw)
        assert new_c == 0 and upd_c == 1
        assert leads[0].address == "Atatürk, Meriç Cd. NO: 21/35"
    await engine.dispose()


@pytest.mark.asyncio
async def test_ingest_progress_callback_reports_checkpoints():
    session_maker, engine = await get_in_memory_db()
    async with session_maker() as db:
        raw = [
            {"name": f"Klinik {i}", "city": "İstanbul", "district": "Ataşehir",
             "place_id": f"gmaps_prog_{i}", "phone": None, "phone_e164": None}
            for i in range(25)
        ]
        checkpoints = []
        async def on_progress(done, total):
            checkpoints.append((done, total))
        leads, new_c, upd_c = await LeadIngestService.ingest_leads(
            db, raw, progress_callback=on_progress
        )
        assert new_c == 25
        assert checkpoints[0] == (0, 25)
        assert (10, 25) in checkpoints
        assert (20, 25) in checkpoints
        assert checkpoints[-1] == (25, 25)
    await engine.dispose()


@pytest.mark.asyncio
async def test_ingest_batch_blacklist_prefetch_marks_unsubscribed():
    from backend.app.models.lead import LeadStatus
    session_maker, engine = await get_in_memory_db()
    async with session_maker() as db:
        db.add(Blacklist(phone_e164="+905321112233", reason="USER_REQUEST"))
        await db.commit()
        raw = [
            {"name": "Engelli Klinik", "city": "İstanbul", "district": "Kadıköy",
             "place_id": "gmaps_bl_01", "phone": "05321112233"},
            {"name": "Temiz Klinik", "city": "İstanbul", "district": "Kadıköy",
             "place_id": "gmaps_bl_02", "phone": "05329998877"},
        ]
        leads, new_c, upd_c = await LeadIngestService.ingest_leads(db, raw)
        assert new_c == 2
        by_name = {l.name: l for l in leads}
        assert by_name["Engelli Klinik"].status == LeadStatus.UNSUBSCRIBED
        assert by_name["Temiz Klinik"].status == LeadStatus.NEW
    await engine.dispose()
