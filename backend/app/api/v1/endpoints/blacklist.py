from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, or_

from backend.app.core.database import get_db
from backend.app.models.blacklist import Blacklist
from backend.app.models.lead import Lead, LeadStatus
from backend.app.schemas.scraper import BlacklistCreate, BlacklistResponse, BlacklistPaginationResponse
from backend.app.services.phone_service import PhoneService

router = APIRouter()

class BulkDeleteBlacklistRequest(BaseModel):
    ids: Optional[List[int]] = None
    delete_all_matching: Optional[bool] = False
    search: Optional[str] = None
    reason: Optional[str] = None

@router.get("", response_model=BlacklistPaginationResponse)
async def list_blacklist(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Blacklist, Lead).outerjoin(Lead, Blacklist.phone_e164 == Lead.phone_e164)
    count_stmt = select(func.count(Blacklist.id)).outerjoin(Lead, Blacklist.phone_e164 == Lead.phone_e164)

    conditions = []
    if search and search.strip():
        q = f"%{search.strip()}%"
        conditions.append(
            or_(
                Blacklist.phone_e164.ilike(q),
                Blacklist.reason.ilike(q),
                Blacklist.notes.ilike(q),
                Lead.name.ilike(q),
                Lead.category.ilike(q),
                Lead.city.ilike(q),
                Lead.district.ilike(q)
            )
        )
    if reason and reason.strip():
        conditions.append(Blacklist.reason == reason.strip())

    for c in conditions:
        stmt = stmt.where(c)
        count_stmt = count_stmt.where(c)

    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (page - 1) * size
    stmt = stmt.order_by(Blacklist.id.desc()).offset(offset).limit(size)
    res = await db.execute(stmt)
    rows = res.all()

    items = []
    for bl, lead in rows:
        items.append(
            BlacklistResponse(
                id=bl.id,
                phone_e164=bl.phone_e164,
                reason=bl.reason,
                notes=bl.notes,
                created_at=bl.created_at,
                lead_name=lead.name if lead else None,
                lead_category=lead.category if lead else None,
                lead_city=lead.city if lead else None,
                lead_district=lead.district if lead else None,
                lead_address=lead.address if lead else None,
                lead_rating=lead.rating if lead else None,
                lead_reviews_count=lead.reviews_count if lead else None,
                lead_website=lead.website if lead else None,
            )
        )

    pages = (total + size - 1) // size if total > 0 else 1

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }

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

    return BlacklistResponse(
        id=bl.id,
        phone_e164=bl.phone_e164,
        reason=bl.reason,
        notes=bl.notes,
        created_at=bl.created_at,
        lead_name=lead.name if lead else None,
        lead_category=lead.category if lead else None,
        lead_city=lead.city if lead else None,
        lead_district=lead.district if lead else None,
        lead_address=lead.address if lead else None,
        lead_rating=lead.rating if lead else None,
        lead_reviews_count=lead.reviews_count if lead else None,
        lead_website=lead.website if lead else None,
    )

@router.delete("/{bl_id}")
async def remove_from_blacklist(bl_id: int, db: AsyncSession = Depends(get_db)):
    bl = await db.get(Blacklist, bl_id)
    if not bl:
        raise HTTPException(status_code=404, detail="Kara liste kaydı bulunamadı")
    await db.delete(bl)
    await db.commit()
    return {"message": "Numara kara listeden çıkarıldı", "id": bl_id}

@router.post("/bulk-delete")
async def bulk_delete_blacklist(payload: BulkDeleteBlacklistRequest, db: AsyncSession = Depends(get_db)):
    if payload.delete_all_matching:
        if payload.search or payload.reason:
            subq = select(Blacklist.id).outerjoin(Lead, Blacklist.phone_e164 == Lead.phone_e164)
            if payload.search and payload.search.strip():
                q = f"%{payload.search.strip()}%"
                subq = subq.where(
                    or_(
                        Blacklist.phone_e164.ilike(q),
                        Blacklist.reason.ilike(q),
                        Blacklist.notes.ilike(q),
                        Lead.name.ilike(q),
                        Lead.category.ilike(q),
                        Lead.city.ilike(q),
                        Lead.district.ilike(q)
                    )
                )
            if payload.reason and payload.reason.strip():
                subq = subq.where(Blacklist.reason == payload.reason.strip())
            
            stmt = delete(Blacklist).where(Blacklist.id.in_(subq))
        else:
            stmt = delete(Blacklist)

        res = await db.execute(stmt)
        await db.commit()
        return {"deleted_count": res.rowcount if res.rowcount is not None and res.rowcount >= 0 else 0}

    elif payload.ids:
        stmt = delete(Blacklist).where(Blacklist.id.in_(payload.ids))
        res = await db.execute(stmt)
        await db.commit()
        return {"deleted_count": res.rowcount if res.rowcount is not None and res.rowcount >= 0 else 0}
    else:
        raise HTTPException(status_code=400, detail="Silinecek kara liste kaydı belirtilmedi")
