import asyncio
import json
import logging
import time
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from backend.app.core.database import get_db, AsyncSessionLocal
from backend.app.models.lead import Lead, LeadStatus
from backend.app.models.blacklist import ScraperJob, ScraperJobStatus, Blacklist
from backend.app.schemas.scraper import ScraperRunRequest, ScraperJobResponse
from backend.app.schemas.lead import LeadResponse
from backend.app.scrapers.google_maps_scraper import GoogleMapsScraper
from backend.app.services.phone_service import PhoneService
from backend.app.api.v1.websocket import ws_manager
from backend.app.data.turkey_locations import get_districts_for_city

logger = logging.getLogger(__name__)

router = APIRouter()

active_tasks: dict[int, asyncio.Task] = {}


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
            raw_leads = await scraper.scrape(
                keyword=keyword,
                city=city,
                districts=districts,
                max_results=max_results,
                progress_callback=on_progress,
            )

            new_leads_count = 0
            valid_phones_count = 0
            created_leads_dicts = []

            for raw in raw_leads:
                biz_name = raw.get("name", "İsimsiz İşletme").strip()
                biz_district = raw.get("district", "").strip()
                biz_city = raw.get("city", "").strip()

                raw_phone = raw.get("phone", "")
                phone_data = PhoneService.normalize_to_e164(raw_phone)
                e164 = phone_data["e164"] if phone_data else (raw.get("phone_e164") or f"+90000{abs(hash(biz_name)) % 10000000:07d}")

                if phone_data:
                    valid_phones_count += 1

                # Check if phone is blacklisted
                bl_check = await db.execute(select(Blacklist).where(Blacklist.phone_e164 == e164))
                if bl_check.scalar_one_or_none():
                    continue

                existing = await db.execute(
                    select(Lead).where(
                        or_(
                            Lead.phone_e164 == e164,
                            and_(Lead.name == biz_name, Lead.district == biz_district, Lead.city == biz_city)
                        )
                    )
                )
                existing_lead = existing.scalars().first()

                if existing_lead:
                    # Refresh entity resolution and verification attributes on existing lead
                    existing_lead.entity_type = raw.get("entity_type", existing_lead.entity_type)
                    existing_lead.verification_status = raw.get("verification_status", existing_lead.verification_status)
                    existing_lead.confidence_level = raw.get("confidence_level", existing_lead.confidence_level)
                    existing_lead.confidence_score = raw.get("confidence_score", existing_lead.confidence_score)
                    existing_lead.is_verified = raw.get("is_verified", existing_lead.is_verified)
                    existing_lead.canonical_category = raw.get("canonical_category", existing_lead.canonical_category)
                    existing_lead.category_score = raw.get("category_score", existing_lead.category_score)
                    existing_lead.category_classification = raw.get("category_classification", existing_lead.category_classification)
                    existing_lead.verification_trace = raw.get("verification_trace", existing_lead.verification_trace)
                    if raw.get("address"):
                        existing_lead.address = raw.get("address")
                    if raw.get("website"):
                        existing_lead.website = raw.get("website")
                    if raw.get("phone") and raw.get("phone") != "Belirtilmemiş":
                        existing_lead.phone = raw.get("phone")
                    if raw.get("phone_e164") and not raw.get("phone_e164", "").startswith("+90000"):
                        existing_lead.phone_e164 = raw.get("phone_e164")
                        existing_lead.is_mobile = phone_data.get("is_mobile", False) if phone_data else False
                        existing_lead.is_whatsapp_eligible = phone_data.get("is_whatsapp_eligible", False) if phone_data else False
                    if raw.get("rating") is not None:
                        existing_lead.rating = raw.get("rating")
                    if raw.get("reviews_count") is not None:
                        existing_lead.reviews_count = raw.get("reviews_count")
                    if raw.get("google_maps_url") or raw.get("maps_url"):
                        existing_lead.custom_data = {"maps_url": raw.get("google_maps_url") or raw.get("maps_url")}

                    created_leads_dicts.append({
                        "id": existing_lead.id,
                        "name": existing_lead.name,
                        "category": existing_lead.category,
                        "canonical_category": existing_lead.canonical_category,
                        "category_score": existing_lead.category_score,
                        "category_classification": existing_lead.category_classification,
                        "entity_type": existing_lead.entity_type,
                        "verification_status": existing_lead.verification_status,
                        "confidence_level": existing_lead.confidence_level,
                        "confidence_score": existing_lead.confidence_score,
                        "is_verified": existing_lead.is_verified,
                        "discovered_from": existing_lead.discovered_from,
                        "verified_by": existing_lead.verified_by,
                        "verification_trace": existing_lead.verification_trace,
                        "phone": existing_lead.phone,
                        "phone_e164": existing_lead.phone_e164,
                        "is_mobile": existing_lead.is_mobile,
                        "is_whatsapp_eligible": existing_lead.is_whatsapp_eligible,
                        "address": existing_lead.address,
                        "city": existing_lead.city,
                        "district": existing_lead.district,
                        "website": existing_lead.website,
                        "rating": existing_lead.rating,
                        "reviews_count": existing_lead.reviews_count,
                        "status": existing_lead.status.value if hasattr(existing_lead.status, 'value') else str(existing_lead.status),
                        "created_at": str(existing_lead.created_at)
                    })
                else:
                    # Insert new Lead
                    lead = Lead(
                        name=biz_name,
                        category=raw.get("category") or keyword.title(),
                        canonical_category=raw.get("canonical_category"),
                        category_score=raw.get("category_score", 1.0),
                        category_classification=raw.get("category_classification", "MATCH"),
                        entity_type=raw.get("entity_type", "BUSINESS"),
                        verification_status=raw.get("verification_status", "UNVERIFIED"),
                        confidence_level=raw.get("confidence_level", "MEDIUM"),
                        confidence_score=raw.get("confidence_score", 50),
                        is_verified=raw.get("is_verified", False),
                        discovered_from=raw.get("discovered_from"),
                        verified_by=raw.get("verified_by"),
                        verification_trace=raw.get("verification_trace"),
                        phone=raw_phone or "Belirtilmemiş",
                        phone_e164=e164,
                        is_mobile=phone_data.get("is_mobile", False) if phone_data else False,
                        is_whatsapp_eligible=phone_data.get("is_whatsapp_eligible", False) if phone_data else False,
                        address=raw.get("address"),
                        city=biz_city or city,
                        district=biz_district,
                        latitude=raw.get("latitude"),
                        longitude=raw.get("longitude"),
                        website=raw.get("website"),
                        rating=raw.get("rating"),
                        reviews_count=raw.get("reviews_count", 0),
                        place_id=raw.get("place_id"),
                        custom_data={"maps_url": raw.get("google_maps_url") or raw.get("maps_url")},
                        search_keyword=keyword,
                        search_location=f"{city} {', '.join(districts)}",
                        source=raw.get("source", "GOOGLE_MAPS"),
                        status=LeadStatus.NEW
                    )
                    db.add(lead)
                    await db.flush()
                    await db.refresh(lead)

                    created_leads_dicts.append({
                        "id": lead.id,
                        "name": lead.name,
                        "category": lead.category,
                        "canonical_category": lead.canonical_category,
                        "category_score": lead.category_score,
                        "category_classification": lead.category_classification,
                        "entity_type": lead.entity_type,
                        "verification_status": lead.verification_status,
                        "confidence_level": lead.confidence_level,
                        "confidence_score": lead.confidence_score,
                        "is_verified": lead.is_verified,
                        "discovered_from": lead.discovered_from,
                        "verified_by": lead.verified_by,
                        "verification_trace": lead.verification_trace,
                        "phone": lead.phone,
                        "phone_e164": lead.phone_e164,
                        "is_mobile": lead.is_mobile,
                        "is_whatsapp_eligible": lead.is_whatsapp_eligible,
                        "address": lead.address,
                        "city": lead.city,
                        "district": lead.district,
                        "website": lead.website,
                        "rating": lead.rating,
                        "reviews_count": lead.reviews_count,
                        "maps_url": raw.get("google_maps_url") or raw.get("maps_url"),
                        "latitude": lead.latitude,
                        "longitude": lead.longitude,
                        "status": lead.status.value if hasattr(lead.status, 'value') else str(lead.status),
                        "created_at": str(lead.created_at)
                    })
                    new_leads_count += 1

            job.status = ScraperJobStatus.COMPLETED
            job.total_found = len(created_leads_dicts)
            job.total_valid_phones = valid_phones_count
            job.total_new_leads = new_leads_count
            job.completed_at = datetime.utcnow()
            job.duration_seconds = int(time.time() - start_time)

            await db.commit()

            logger.info(
                f"[SEARCH_JOB_COMPLETE] job_id={job_id} total_found={len(created_leads_dicts)} "
                f"valid_phones={valid_phones_count} new_leads={new_leads_count} "
                f"duration={job.duration_seconds}s"
            )

            await ws_manager.broadcast({
                "event": "scraper_completed",
                "job_id": job_id,
                "total_found": len(created_leads_dicts),
                "total_valid_phones": valid_phones_count,
                "total_new_leads": new_leads_count,
                "leads": created_leads_dicts,
                "metrics": latest_metrics,
                "duration_seconds": job.duration_seconds
            })

        except asyncio.CancelledError:
            logger.info(f"[SEARCH_JOB_CANCELLED] job_id={job_id} task cancelled by user.")
            job.status = ScraperJobStatus.CANCELLED
            job.error_message = "Kullanıcı tarafından iptal edildi."
            job.completed_at = datetime.utcnow()
            job.duration_seconds = int(time.time() - start_time)
            await db.commit()

            await ws_manager.broadcast({
                "event": "scraper_cancelled",
                "job_id": job_id,
                "message": "Tarama kullanıcı tarafından iptal edildi."
            })

        except Exception as e:
            logger.error(f"[SEARCH_JOB_ERROR] job_id={job_id} error={e}", exc_info=True)
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
    db: AsyncSession = Depends(get_db)
):
    if not req.keyword or not req.keyword.strip():
        raise HTTPException(status_code=400, detail="Anahtar kelime (keyword) zorunludur.")
    if not req.city or not req.city.strip():
        raise HTTPException(status_code=400, detail="Şehir (city) zorunludur.")

    city = req.city.strip()
    districts = [d.strip() for d in req.districts if d.strip()]

    # If no specific districts selected, load ALL districts for the city (Tüm İl Geneli)
    if not districts:
        districts = get_districts_for_city(city)
        if not districts:
            raise HTTPException(
                status_code=400,
                detail=f"'{city}' için ilçe bilgisi bulunamadı."
            )

    # Compute display string for backward compatibility
    display_location = f"{city} {', '.join(districts)}" if len(districts) <= 5 else f"{city} ({len(districts)} İlçe)"

    job = ScraperJob(
        keyword=req.keyword.strip(),
        location=display_location,
        city=city,
        districts_json=districts,
        source=req.source,
        status=ScraperJobStatus.PENDING
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    logger.info(
        f"[SEARCH_JOB_CREATED] job_id={job.id} keyword={job.keyword!r} "
        f"city={city!r} districts={districts!r} max_results={req.max_results}"
    )

    # Launch background async scraping task with active task tracking
    task = asyncio.create_task(
        run_scraper_task(
            job.id,
            job.keyword,
            city,
            districts,
            req.max_results,
        )
    )
    active_tasks[job.id] = task

    return job


@router.post("/cancel/{job_id}", response_model=ScraperJobResponse)
async def cancel_scraper_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(ScraperJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job_id in active_tasks:
        task = active_tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"[SEARCH_JOB_CANCELLED] Cancelled task for job_id={job_id}")

    job.status = ScraperJobStatus.CANCELLED
    job.error_message = "Kullanıcı tarafından iptal edildi."
    job.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)

    await ws_manager.broadcast({
        "event": "scraper_cancelled",
        "job_id": job_id,
        "message": "Tarama durduruldu."
    })

    return job


@router.get("/jobs", response_model=List[ScraperJobResponse])
async def list_scraper_jobs(db: AsyncSession = Depends(get_db)):
    stmt = select(ScraperJob).order_by(ScraperJob.id.desc()).limit(20)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/jobs/{job_id}", response_model=ScraperJobResponse)
@router.get("/status/{job_id}", response_model=ScraperJobResponse)
async def get_scraper_job_status(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(ScraperJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

