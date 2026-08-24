import asyncio
import logging
import time
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.database import get_db, AsyncSessionLocal
from backend.app.core.config import settings
from backend.app.models.blacklist import ScraperJob, ScraperJobStatus
from backend.app.schemas.scraper import ScraperRunRequest, ScraperJobResponse
from backend.app.schemas.lead import LeadResponse
from backend.app.scrapers.google_maps_scraper import GoogleMapsScraper
from backend.app.services.lead_ingest_service import LeadIngestService
from backend.app.api.v1.websocket import ws_manager
from backend.app.data.turkey_locations import get_districts_for_city

logger = logging.getLogger(__name__)

router = APIRouter()

active_tasks: dict[int, asyncio.Task] = {}
scraper_semaphore = asyncio.Semaphore(settings.SCRAPER_MAX_CONCURRENT_TASKS)


async def run_scraper_task(
    job_id: int,
    keyword: str,
    city: str,
    districts: List[str],
    max_results: int,
):
    """Background execution of scraper with structured location snapshot and WebSocket dispatch."""
    start_time = time.time()
    scraper = GoogleMapsScraper()

    logger.info(
        f"[SEARCH_JOB] job_id={job_id} keyword={keyword!r} "
        f"city={city!r} districts={districts!r} max_results={max_results}"
    )

    async with AsyncSessionLocal() as db:
        job = await db.get(ScraperJob, job_id)
        if not job:
            logger.error(f"[SEARCH_JOB] job_id={job_id} NOT FOUND in database")
            return

        job.status = ScraperJobStatus.RUNNING
        job.started_at = datetime.utcnow()
        await db.commit()

        await ws_manager.broadcast({
            "event": "scraper_started",
            "job_id": job_id,
            "keyword": keyword,
            "city": city,
            "districts": districts,
        })

        latest_metrics = {}

        async def on_progress(event_data: dict):
            nonlocal latest_metrics
            if event_data.get("type") == "completed" and "metrics" in event_data:
                latest_metrics = event_data["metrics"]
            await ws_manager.broadcast({
                "event": "scraper_progress",
                "job_id": job_id,
                "data": event_data
            })

        try:
            async with scraper_semaphore:
                raw_leads = await scraper.scrape(
                    keyword=keyword,
                    city=city,
                    districts=districts,
                    max_results=max_results,
                    progress_callback=on_progress,
                )

            # Ingest leads cleanly via LeadIngestService
            created_leads, new_count, updated_count = await LeadIngestService.ingest_leads(
                db=db,
                raw_leads=raw_leads,
                source="GOOGLE_MAPS",
                search_keyword=keyword,
                search_location=f"{city} {', '.join(districts)}",
            )

            job.status = ScraperJobStatus.COMPLETED
            job.total_found = len(raw_leads)
            job.total_valid_phones = sum(1 for r in raw_leads if r.get("phone_e164"))
            job.total_new_leads = new_count
            job.completed_at = datetime.utcnow()
            job.duration_seconds = int(time.time() - start_time)

            await db.commit()

            lead_dicts = [
                {
                    "id": l.id,
                    "name": l.name,
                    "category": l.category,
                    "phone": l.phone,
                    "phone_e164": l.phone_e164,
                    "is_mobile": l.is_mobile,
                    "is_whatsapp_eligible": l.is_whatsapp_eligible,
                    "address": l.address,
                    "city": l.city,
                    "district": l.district,
                    "website": l.website,
                    "rating": l.rating,
                    "reviews_count": l.reviews_count,
                    "maps_url": l.custom_data.get("maps_url") if l.custom_data else None,
                    "status": l.status.value if hasattr(l.status, 'value') else str(l.status),
                    "created_at": str(l.created_at)
                }
                for l in created_leads
            ]

            await ws_manager.broadcast({
                "event": "scraper_completed",
                "job_id": job_id,
                "total_found": len(raw_leads),
                "total_new_leads": new_count,
                "leads": lead_dicts[:25],
                "metrics": latest_metrics
            })

            logger.info(
                f"[SEARCH_JOB_DONE] job_id={job_id} in {job.duration_seconds}s "
                f"found={len(raw_leads)} new={new_count} updated={updated_count}"
            )

        except asyncio.CancelledError:
            logger.warning(f"[SEARCH_JOB_CANCELLED] job_id={job_id}")
            job.status = ScraperJobStatus.CANCELLED
            job.completed_at = datetime.utcnow()
            job.duration_seconds = int(time.time() - start_time)
            await db.commit()
            await ws_manager.broadcast({
                "event": "scraper_cancelled",
                "job_id": job_id,
            })
            raise
        except Exception as e:
            logger.exception(f"[SEARCH_JOB_ERROR] job_id={job_id}: {e}")
            job.status = ScraperJobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            job.duration_seconds = int(time.time() - start_time)
            await db.commit()
            await ws_manager.broadcast({
                "event": "scraper_failed",
                "job_id": job_id,
                "error": str(e)
            })
        finally:
            active_tasks.pop(job_id, None)


@router.post("/run", response_model=ScraperJobResponse)
@router.post("/start", response_model=ScraperJobResponse)
async def start_scraper(
    req: ScraperRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    keyword = req.keyword.strip()
    city = req.city.strip()
    districts = req.districts or []

    if not keyword or not city:
        raise HTTPException(status_code=400, detail="Anahtar kelime ve şehir belirtilmelidir.")

    if not districts:
        districts = get_districts_for_city(city)
        if not districts:
            districts = [f"{city} Merkez"]

    job = ScraperJob(
        keyword=keyword,
        city=city,
        districts_json=districts,
        max_results=req.max_results or 50,
        status=ScraperJobStatus.PENDING,
        total_found=0,
        total_valid_phones=0,
        total_new_leads=0,
        created_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    task = asyncio.create_task(
        run_scraper_task(
            job_id=job.id,
            keyword=keyword,
            city=city,
            districts=districts,
            max_results=job.max_results,
        )
    )
    active_tasks[job.id] = task

    return job


@router.get("/jobs", response_model=List[ScraperJobResponse])
async def list_scraper_jobs(limit: int = 20, db: AsyncSession = Depends(get_db)):
    stmt = select(ScraperJob).order_by(ScraperJob.id.desc()).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/jobs/{job_id}", response_model=ScraperJobResponse)
@router.get("/status/{job_id}", response_model=ScraperJobResponse)
async def get_scraper_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(ScraperJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Tarama işi bulunamadı")
    return job


@router.post("/cancel/{job_id}")
async def cancel_scraper_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(ScraperJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Tarama işi bulunamadı")

    task = active_tasks.get(job_id)
    if task and not task.done():
        task.cancel()
        return {"message": "Tarama işi iptal edildi", "job_id": job_id}

    if job.status in [ScraperJobStatus.PENDING, ScraperJobStatus.RUNNING]:
        job.status = ScraperJobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        await db.commit()

    return {"message": "Tarama işi durduruldu", "job_id": job_id}
