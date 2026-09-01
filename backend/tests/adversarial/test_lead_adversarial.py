"""
Adversarial Robustness Test Suite: Lead Ingestion, Normalization, Deduplication & CRM Mutations.
Validates system resilience against hostile, corrupted, boundary, and pathological inputs.
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func

from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.lead import Lead, LeadStatus
from backend.app.models.blacklist import Blacklist
from backend.app.services.lead_ingest_service import LeadIngestService
from backend.app.services.phone_service import PhoneService


def unique_phone_num():
    return f"+9053{uuid.uuid4().int % 100000000:08d}"


@pytest.mark.asyncio
async def test_adversarial_phone_corruption_matrix():
    """
    Tests extreme and adversarial phone string corruptions:
    System must never crash, never synthesize fake +90000 numbers, and gracefully resolve validity.
    """
    corrupt_inputs = [
        "",
        "   ",
        None,
        "abcdef",
        "!!!@@@###$$$",
        "+",
        "++905321112233",
        "00000000000000000000000000000000",
        "9" * 100,
        "0532",
        "0212",
        "+90 532 ABC 45 67",
        "tel:05321234567",
        "undefined",
        "null",
        "NaN",
        "\x00\x01\x02",
        "0532 123 45 67\n0533 987 65 43",  # Multiline string injection
    ]

    for corrupted in corrupt_inputs:
        result = PhoneService.normalize_to_e164(corrupted)
        if result is not None:
            # If normalized, it MUST be a valid structure
            assert isinstance(result, dict)
            assert "e164" in result
            assert "is_valid" in result
            assert not result["e164"].startswith("+9000000"), "Must never synthesize fake dummy numbers"
        else:
            assert result is None


@pytest.mark.asyncio
async def test_adversarial_phone_format_deduplication():
    """
    Tests that differently formatted variations of the EXACT same phone number
    normalize to the identical E.164 string and deduplicate cleanly.
    """
    base_digits = f"532{uuid.uuid4().int % 10000000:07d}"
    formats = [
        f"0{base_digits}",
        f"+90{base_digits}",
        f"90{base_digits}",
        f"0 ({base_digits[:3]}) {base_digits[3:6]} {base_digits[6:8]} {base_digits[8:]}",
        f"+90-{base_digits[:3]}-{base_digits[3:6]}-{base_digits[6:]}",
        f"  0{base_digits}  ",
    ]

    normalized_set = set()
    for fmt in formats:
        norm = PhoneService.normalize_to_e164(fmt)
        assert norm is not None
        assert norm["is_valid"] is True
        normalized_set.add(norm["e164"])

    assert len(normalized_set) == 1, f"All formats must normalize to 1 E.164, got {normalized_set}"


@pytest.mark.asyncio
async def test_adversarial_unicode_and_extreme_lead_names():
    """
    Tests ingestion with Unicode, emojis, non-Latin scripts, and extreme length strings.
    """
    unicode_names = [
        "🦷 Özel Diş Kliniği & Estetik 🏥",
        "Стоматологическая Клиника Анталья",
        "عيادة لطب الأسنان إسطنبول",
        "伊斯坦布尔牙科诊所",
        "İstanbul / Kadıköy (Şube #1) - \"Mega Dental\" <Grup>",
        "A" * 2000,  # Extremely long business name
        "   Önünde ve Arkasında Boşluk Olan Klinik   ",
    ]

    raw_batch = [
        {
            "name": f"{name} {uuid.uuid4().hex[:6]}",
            "phone": unique_phone_num(),
            "place_id": f"adv_place_{uuid.uuid4().hex[:12]}",
            "category": "Diş Hekimi",
            "city": "İstanbul",
        }
        for name in unicode_names
    ]

    async with AsyncSessionLocal() as session:
        leads, new_cnt, updated_cnt = await LeadIngestService.ingest_leads(
            db=session,
            raw_leads=raw_batch,
            search_keyword="Adversarial Unicode Test"
        )
        await session.commit()
        assert new_cnt == len(unicode_names)
        assert updated_cnt == 0

        # Verify all survived and can be fetched without SQL corruption
        for raw in raw_batch:
            stmt = select(Lead).where(Lead.place_id == raw["place_id"])
            saved = (await session.execute(stmt)).scalar_one_or_none()
            assert saved is not None
            assert saved.name == raw["name"].strip()


@pytest.mark.asyncio
async def test_adversarial_same_lead_repeated_ingest_10x():
    """
    Tests 10 consecutive ingestions of the exact same 5 raw leads in varying order.
    Total leads in database must remain exactly 5 (0 duplicate records).
    """
    test_run_id = uuid.uuid4().hex[:8]
    phone_base = [unique_phone_num() for _ in range(5)]
    place_ids = [f"place_stress_{test_run_id}_{i}" for i in range(5)]

    raw_candidates = [
        {
            "name": f"Stres Test İşletmesi {test_run_id} #{i}",
            "phone": phone_base[i],
            "place_id": place_ids[i],
            "category": "Sağlık",
            "city": "İzmir",
        }
        for i in range(5)
    ]

    # Ingest 10 times in a loop
    for iteration in range(10):
        async with AsyncSessionLocal() as session:
            leads, new_cnt, upd_cnt = await LeadIngestService.ingest_leads(
                db=session,
                raw_leads=raw_candidates,
                search_keyword="Tekrarlı Test"
            )
            await session.commit()
            if iteration == 0:
                assert new_cnt == 5
                assert upd_cnt == 0
            else:
                assert new_cnt == 0
                assert upd_cnt == 5

    # Verify Database count
    async with AsyncSessionLocal() as session:
        stmt = select(func.count(Lead.id)).where(Lead.place_id.in_(place_ids))
        total_in_db = (await session.execute(stmt)).scalar()
        assert total_in_db == 5, f"Expected 5 leads, found {total_in_db}"


@pytest.mark.asyncio
async def test_adversarial_lead_mutation_boundary_conditions():
    """
    Tests mutation boundary conditions on REST API:
    - Update nonexistent lead ID -> 404
    - Delete nonexistent lead ID -> 404
    - Bulk delete with mixed existing, negative, and extreme integer IDs -> 200 with accurate count
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Update nonexistent lead
        res_update = await client.patch("/api/v1/leads/99999999", json={"notes": "Hayalet Lead"})
        assert res_update.status_code == 404

        # 2. Delete nonexistent lead
        res_del = await client.delete("/api/v1/leads/99999999")
        assert res_del.status_code == 404

        # 3. Create 1 real lead to test mixed bulk delete
        real_phone = unique_phone_num()
        create_res = await client.post("/api/v1/leads", json={
            "name": "Silinecek Gerçek Lead",
            "phone": real_phone,
            "category": "Test",
            "city": "Bursa"
        })
        assert create_res.status_code == 201
        real_id = create_res.json()["id"]

        # 4. Bulk delete with invalid, negative, extreme IDs and 1 real ID
        bulk_res = await client.post("/api/v1/leads/bulk-delete", json={
            "lead_ids": [-1, 0, 9999999, real_id, 8888888]
        })
        assert bulk_res.status_code == 200
        assert bulk_res.json()["deleted_count"] == 1
