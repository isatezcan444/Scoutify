from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.models.blacklist import Blacklist
from backend.app.models.lead import Lead, LeadStatus
from backend.app.schemas.scraper import BlacklistCreate, BlacklistResponse
from backend.app.services.phone_service import PhoneService

router = APIRouter()

@router.get("", response_model=List[BlacklistResponse])
async def list_blacklist(db: AsyncSession = Depends(get_db)):
    stmt = select(Blacklist).order_by(Blacklist.id.desc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("", response_model=BlacklistResponse, status_code=201)
async def add_to_blacklist(bl_in: BlacklistCreate, db: AsyncSession = Depends(get_db)):
    phone_data = PhoneService.normalize_to_e164(bl_in.phone_e164)
    if not phone_data:
        raise HTTPException(status_code=400, detail="Geçersiz telefon numarası.")
        
    e164 = phone_data["e164"]
    
    # Check if already blacklisted
    stmt = select(Blacklist).where(Blacklist.phone_e164 == e164)
    existing = await db.execute(stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Bu numara zaten kara listede.")
        
    bl = Blacklist(
        phone_e164=e164,
        reason=bl_in.reason or "USER_REQUEST",
        notes=bl_in.notes
    )
    db.add(bl)
    
    # Update lead status if exists
    lead_stmt = select(Lead).where(Lead.phone_e164 == e164)
    lead_res = await db.execute(lead_stmt)
    lead = lead_res.scalar_one_or_none()
    if lead:
        lead.status = LeadStatus.UNSUBSCRIBED
        
    await db.commit()
    await db.refresh(bl)
    return bl

@router.delete("/{bl_id}")
async def remove_from_blacklist(bl_id: int, db: AsyncSession = Depends(get_db)):
    bl = await db.get(Blacklist, bl_id)
    if not bl:
        raise HTTPException(status_code=404, detail="Kara liste kaydı bulunamadı")
    await db.delete(bl)
    await db.commit()
    return {"message": "Numara kara listeden çıkarıldı", "id": bl_id}
