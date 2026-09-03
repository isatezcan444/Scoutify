"""Tests for explicit on-demand CRM save of discovery results.

Invariant: discovery (POST /scraper/start) never writes Lead rows by itself;
persistence happens only through POST /scraper/jobs/{id}/save with an
explicit user selection. Re-saving is idempotent (matches merge).
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func

from backend.app.main import app
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.lead import Lead
from backend.app.models.blacklist import ScraperJob, ScraperJobStatus


def _rnd_phone():
    return f"+90555{uuid.uuid4().int % 100000000:08d}"


def _raw(name, phone, pid):
    return {
        "name": name,
        "category": "Diş Kliniği",
        "phone": phone,
        "phone_e164": phone,
        "is_mobile": True,
        "is_whatsapp_eligible": True,
        "website": None,
        "address": "Ataşehir, İstanbul",
        "city": "İstanbul",
        "district": "Ataşehir",
        "latitude": 40.99,
        "longitude": 29.12,
        "rating": 4.5,
        "reviews_count": 10,
        "google_maps_url": f"https://maps.google.com/place/{pid}",
        "place_id": pid,
        "source": "GOOGLE_MAPS",
        "is_verified": True,
    }


async def _make_job(status=ScraperJobStatus.COMPLETED):
    async with AsyncSessionLocal() as db:
        job = ScraperJob(
            keyword="Diş Kliniği",
            location="İstanbul Ataşehir",
            city="İstanbul",
            districts_json=["Ataşehir"],
            source="GOOGLE_MAPS",
            status=status,
            total_found=2,
            total_valid_phones=2,
            total_new_leads=0,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job.id


@pytest.mark.asyncio
async def test_save_persists_selection_with_ids():
    job_id = await _make_job()
    tag = uuid.uuid4().hex[:6]
    p1, p2 = _rnd_phone(), _rnd_phone()
    pid1, pid2 = f"gmaps_save_{uuid.uuid4().hex[:8]}", f"gmaps_save_{uuid.uuid4().hex[:8]}"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/scraper/jobs/{job_id}/save",
            json={"leads": [_raw(f"Save Test A {tag}", p1, pid1), _raw(f"Save Test B {tag}", p2, pid2)]},
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["job_id"] == job_id
        assert data["new_count"] == 2
        assert data["updated_count"] == 0
        assert len(data["saved"]) == 2
        assert all(s["id"] for s in data["saved"])
        assert {s["place_id"] for s in data["saved"]} == {pid1, pid2}


@pytest.mark.asyncio
async def test_save_is_idempotent_on_resave():
    job_id = await _make_job()
    tag = uuid.uuid4().hex[:6]
    p1 = _rnd_phone()
    pid1 = f"gmaps_resave_{uuid.uuid4().hex[:8]}"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        first = await ac.post(
            f"/api/v1/scraper/jobs/{job_id}/save", json={"leads": [_raw(f"Resave Klinik {tag}", p1, pid1)]}
        )
        assert first.json()["new_count"] == 1
        second = await ac.post(
            f"/api/v1/scraper/jobs/{job_id}/save", json={"leads": [_raw(f"Resave Klinik {tag}", p1, pid1)]}
        )
        payload = second.json()
        assert payload["new_count"] == 0
        assert payload["updated_count"] == 1

    async with AsyncSessionLocal() as db:
        count = (
            await db.execute(select(func.count(Lead.id)).where(Lead.place_id == pid1))
        ).scalar_one()
        assert count == 1


@pytest.mark.asyncio
async def test_save_rejects_non_completed_job_and_empty_payload():
    pending_id = await _make_job(status=ScraperJobStatus.RUNNING)
    done_id = await _make_job()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        running = await ac.post(
            f"/api/v1/scraper/jobs/{pending_id}/save",
            json={"leads": [_raw("X", _rnd_phone(), "gmaps_x")]},
        )
        assert running.status_code == 400

        empty = await ac.post(f"/api/v1/scraper/jobs/{done_id}/save", json={"leads": []})
        assert empty.status_code == 422

        missing = await ac.post(
            "/api/v1/scraper/jobs/999999999/save",
            json={"leads": [_raw("X", _rnd_phone(), "gmaps_y")]},
        )
        assert missing.status_code == 404
