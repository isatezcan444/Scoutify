from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update, delete

from backend.app.core.database import get_db
from backend.app.models.lead import Lead, LeadStatus
from backend.app.schemas.lead import (
    LeadResponse,
    LeadListResponse,
    LeadCreate,
    LeadUpdate
)
from backend.app.services.phone_service import PhoneService
from backend.app.services.export_service import ExportService

router = APIRouter()

@router.get("", response_model=LeadListResponse)
async def list_leads(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    city: Optional[str] = None,
    district: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[LeadStatus] = None,
    whatsapp_eligible_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    query = select(Lead)
    count_query = select(func.count(Lead.id))
    
    conditions = []
    if search:
        search_filter = or_(
            Lead.name.ilike(f"%{search}%"),
            Lead.phone.ilike(f"%{search}%"),
            Lead.phone_e164.ilike(f"%{search}%"),
            Lead.category.ilike(f"%{search}%"),
            Lead.address.ilike(f"%{search}%"),
            Lead.notes.ilike(f"%{search}%")
        )
        conditions.append(search_filter)
        
    if city:
        conditions.append(Lead.city.ilike(f"%{city}%"))
    if district:
        conditions.append(Lead.district.ilike(f"%{district}%"))
    if category:
        conditions.append(Lead.category.ilike(f"%{category}%"))
    if status:
        conditions.append(Lead.status == status)
    if whatsapp_eligible_only:
        conditions.append(Lead.is_whatsapp_eligible == True)
        
    if conditions:
        for c in conditions:
            query = query.where(c)
            count_query = count_query.where(c)
            
    # Count total
    total_res = await db.execute(count_query)
    total = total_res.scalar_one()
    
    # Paginate and order by newest
    offset = (page - 1) * size
    query = query.order_by(Lead.id.desc()).offset(offset).limit(size)
    
    res = await db.execute(query)
    items = res.scalars().all()
    
    pages = (total + size - 1) // size if total > 0 else 1
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages
    }

@router.get("/categories", response_model=List[str])
async def get_distinct_categories(db: AsyncSession = Depends(get_db)):
    stmt = select(Lead.category).where(Lead.category.is_not(None)).distinct().order_by(Lead.category)
    res = await db.execute(stmt)
    return [c for c in res.scalars().all() if c]

@router.get("/cities", response_model=List[str])
async def get_distinct_cities(db: AsyncSession = Depends(get_db)):
    stmt = select(Lead.city).where(Lead.city.is_not(None)).distinct().order_by(Lead.city)
    res = await db.execute(stmt)
    return [c for c in res.scalars().all() if c]

@router.post("", response_model=LeadResponse, status_code=201)
async def create_lead(lead_in: LeadCreate, db: AsyncSession = Depends(get_db)):
    # Validate and normalize phone
    phone_data = PhoneService.normalize_to_e164(lead_in.phone)
    if not phone_data:
        raise HTTPException(status_code=400, detail="Geçersiz telefon numarası formatı.")
        
    # Check if duplicate exists
    stmt = select(Lead).where(Lead.phone_e164 == phone_data["e164"])
    existing = await db.execute(stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Bu telefon numarası ({phone_data['e164']}) sistemde zaten kayıtlı.")
        
    lead_dict = lead_in.model_dump()
    lead = Lead(
        **lead_dict,
        phone_e164=phone_data["e164"],
        is_mobile=phone_data["is_mobile"],
        is_whatsapp_eligible=phone_data["is_whatsapp_eligible"],
        status=LeadStatus.NEW
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead

@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")
    return lead

@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(lead_id: int, lead_in: LeadUpdate, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")
        
    update_data = lead_in.model_dump(exclude_unset=True)
    if "phone" in update_data and update_data["phone"]:
        phone_data = PhoneService.normalize_to_e164(update_data["phone"])
        if phone_data:
            lead.phone_e164 = phone_data["e164"]
            lead.is_mobile = phone_data["is_mobile"]
            lead.is_whatsapp_eligible = phone_data["is_whatsapp_eligible"]
            
    for key, value in update_data.items():
        setattr(lead, key, value)
        
    await db.commit()
    await db.refresh(lead)
    return lead

@router.delete("/{lead_id}")
async def delete_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead bulunamadı")
    await db.delete(lead)
    await db.commit()
    return {"message": "Lead başarıyla silindi", "id": lead_id}

@router.post("/export/csv")
async def export_leads_csv(
    search: Optional[str] = None,
    city: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[LeadStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Lead)
    if search:
        query = query.where(or_(Lead.name.ilike(f"%{search}%"), Lead.phone_e164.ilike(f"%{search}%")))
    if city:
        query = query.where(Lead.city.ilike(f"%{city}%"))
    if category:
        query = query.where(Lead.category.ilike(f"%{category}%"))
    if status:
        query = query.where(Lead.status == status)
        
    res = await db.execute(query.order_by(Lead.id.desc()))
    leads = res.scalars().all()
    
    leads_dicts = [l.__dict__ for l in leads]
    csv_bytes = ExportService.export_csv(leads_dicts)
    
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=scoutify_leads.csv"}
    )

@router.post("/export/excel")
async def export_leads_excel(
    search: Optional[str] = None,
    city: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[LeadStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Lead)
    if search:
        query = query.where(or_(Lead.name.ilike(f"%{search}%"), Lead.phone_e164.ilike(f"%{search}%")))
    if city:
        query = query.where(Lead.city.ilike(f"%{city}%"))
    if category:
        query = query.where(Lead.category.ilike(f"%{category}%"))
    if status:
        query = query.where(Lead.status == status)
        
    res = await db.execute(query.order_by(Lead.id.desc()))
    leads = res.scalars().all()
    
    leads_dicts = [l.__dict__ for l in leads]
    excel_bytes = ExportService.export_excel(leads_dicts)
    
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=scoutify_leads.xlsx"}
    )
