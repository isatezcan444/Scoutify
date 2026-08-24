import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.models.campaign import Campaign, CampaignStatus
from backend.app.schemas.campaign import (
    CampaignResponse,
    CampaignCreate,
    CampaignUpdate,
    CampaignLaunchRequest,
    SpintaxPreviewRequest,
    SpintaxPreviewResponse
)
from backend.app.services.spintax_service import SpintaxService
from backend.app.services.campaign_runner import CampaignRunner

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    stmt = select(Campaign).order_by(Campaign.id.desc())
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("", response_model=CampaignResponse, status_code=201)
async def create_campaign(campaign_in: CampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign_dict = campaign_in.model_dump()
    campaign = Campaign(**campaign_dict, status=CampaignStatus.DRAFT)
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampanya bulunamadı")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(campaign_id: int, campaign_in: CampaignUpdate, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampanya bulunamadı")

    update_data = campaign_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(campaign, key, value)

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampanya bulunamadı")
    
    if CampaignRunner.is_campaign_running(campaign_id):
        await CampaignRunner.cancel_campaign(campaign_id)

    await db.delete(campaign)
    await db.commit()
    return None


@router.post("/spintax/preview", response_model=SpintaxPreviewResponse)
async def preview_spintax(req: SpintaxPreviewRequest):
    """
    Evaluates template, calculates permutation combinations, and generates live sample variations.
    """
    perms = SpintaxService.calculate_permutations(req.template)
    samples = SpintaxService.generate_preview_samples(req.template, count=req.count, sample_lead=req.sample_lead)
    return {
        "template": req.template,
        "permutations_count": perms,
        "samples": samples
    }


@router.post("/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: int,
    req: CampaignLaunchRequest,
    db: AsyncSession = Depends(get_db)
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampanya bulunamadı")

    if campaign.status == CampaignStatus.ACTIVE or CampaignRunner.is_campaign_running(campaign_id):
        raise HTTPException(status_code=409, detail="Bu kampanya şu anda zaten çalışıyor.")

    started = await CampaignRunner.start_campaign(
        campaign_id=campaign.id,
        lead_ids=req.lead_ids,
        limit=req.limit or 50
    )

    if not started:
        raise HTTPException(status_code=409, detail="Kampanya başlatılamadı, işlem zaten aktif.")

    return {
        "message": f"'{campaign.name}' kampanyası başlatıldı ve arka planda işleniyor.",
        "campaign_id": campaign.id
    }


@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: int, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Kampanya bulunamadı")

    campaign.status = CampaignStatus.PAUSED
    await db.commit()
    await CampaignRunner.cancel_campaign(campaign_id)

    return {"message": f"'{campaign.name}' kampanyası duraklatıldı.", "campaign_id": campaign.id}
