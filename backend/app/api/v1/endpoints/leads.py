from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, delete

from backend.app.core.database import get_db
from backend.app.models.lead import Lead, LeadStatus
from backend.app.models.blacklist import Blacklist
from backend.app.schemas.lead import (
    LeadResponse,
    LeadListResponse,
    LeadCreate,
    LeadUpdate,
    BulkDeleteRequest,
    BulkBlacklistRequest,
    ExportLeadsRequest
)
from backend.app.services.phone_service import PhoneService
from backend.app.services.export_service import ExportService

router = APIRouter()


def build_lead_filter_conditions(
    search: Optional[str] = None,
    city: Optional[str] = None,
    district: Optional[str] = None,
    districts: Optional[List[str]] = None,
    category: Optional[str] = None,
    categories: Optional[List[str]] = None,
    status: Optional[LeadStatus] = None,
    whatsapp_eligible_only: bool = False,
) -> list:
    """Builds a unified list of SQLAlchemy filter expressions for Lead queries."""
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

    # Multi-district filtering
    all_districts = []
    if districts:
        for d in districts:
            if "," in d:
                all_districts.extend([x.strip() for x in d.split(",") if x.strip()])
            elif d.strip():
                all_districts.append(d.strip())
    if district and district.strip():
        all_districts.append(district.strip())

    if all_districts:
        conditions.append(or_(*[Lead.district.ilike(f"%{d}%") for d in set(all_districts)]))

    # Multi-category filtering
    all_categories = []
    if categories:
        for c in categories:
            if "," in c:
                all_categories.extend([x.strip() for x in c.split(",") if x.strip()])
            elif c.strip():
                all_categories.append(c.strip())
    if category and category.strip():
        all_categories.append(category.strip())

    if all_categories:
        conditions.append(or_(*[Lead.category.ilike(f"%{c}%") for c in set(all_categories)]))

    if status:
        conditions.append(Lead.status == status)
    if whatsapp_eligible_only:
        conditions.append(Lead.is_whatsapp_eligible == True)

    return conditions


@router.get("", response_model=LeadListResponse)
async def list_leads(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    city: Optional[str] = None,
    district: Optional[str] = None,
    districts: Optional[List[str]] = Query(None),
    category: Optional[str] = None,
    categories: Optional[List[str]] = Query(None),
    status: Optional[LeadStatus] = None,
    whatsapp_eligible_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    query = select(Lead)
    count_query = select(func.count(Lead.id))

    conditions = build_lead_filter_conditions(
        search=search,
        city=city,
        district=district,
        districts=districts,
        category=category,
        categories=categories,
        status=status,
        whatsapp_eligible_only=whatsapp_eligible_only
    )

    for c in conditions:
        query = query.where(c)
        count_query = count_query.where(c)

    total_res = await db.execute(count_query)
    total = total_res.scalar_one()

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
    phone_data = PhoneService.normalize_to_e164(lead_in.phone)
    if not phone_data or not phone_data["is_valid"]:
        raise HTTPException(status_code=400, detail="Geçersiz telefon numarası.")

    e164 = phone_data["e164"]

    bl_stmt = select(Blacklist).where(Blacklist.phone_e164 == e164)
    bl_res = await db.execute(bl_stmt)
    if bl_res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bu numara kara listede bulunmaktadır.")

    existing_stmt = select(Lead).where(Lead.phone_e164 == e164)
    existing_res = await db.execute(existing_stmt)
    if existing_res.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Bu numara ile kayıtlı bir müşteri adayı zaten mevcut.")

    lead = Lead(
        name=lead_in.name,
        category=lead_in.category,
        phone=lead_in.phone,
        phone_e164=e164,
        is_mobile=phone_data.get("is_mobile", False),
        is_whatsapp_eligible=phone_data.get("is_whatsapp_eligible", False),
        city=lead_in.city,
        district=lead_in.district,
        address=lead_in.address,
        website=lead_in.website,
        email=lead_in.email,
        rating=lead_in.rating,
        reviews_count=lead_in.reviews_count,
        search_keyword=lead_in.search_keyword,
        search_location=lead_in.search_location,
        notes=lead_in.notes,
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
        raise HTTPException(status_code=404, detail="Müşteri adayı bulunamadı")
    return lead


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(lead_id: int, lead_in: LeadUpdate, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Müşteri adayı bulunamadı")

    update_data = lead_in.model_dump(exclude_unset=True)
    if "phone" in update_data and update_data["phone"]:
        phone_data = PhoneService.normalize_to_e164(update_data["phone"])
        if phone_data and phone_data["is_valid"]:
            lead.phone_e164 = phone_data["e164"]
            lead.is_mobile = phone_data.get("is_mobile", False)
            lead.is_whatsapp_eligible = phone_data.get("is_whatsapp_eligible", False)

    for field, value in update_data.items():
        setattr(lead, field, value)

    await db.commit()
    await db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    lead = await db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Müşteri adayı bulunamadı")
    await db.delete(lead)
    await db.commit()
    return None


@router.post("/bulk-delete")
async def bulk_delete_leads(payload: BulkDeleteRequest, db: AsyncSession = Depends(get_db)):
    if payload.delete_all_matching:
        conditions = build_lead_filter_conditions(
            search=payload.search,
            city=payload.city,
            districts=payload.districts,
            categories=payload.categories,
            status=payload.status,
            whatsapp_eligible_only=payload.whatsapp_eligible_only or False
        )
        stmt = delete(Lead)
        for c in conditions:
            stmt = stmt.where(c)
        res = await db.execute(stmt)
        await db.commit()
        return {"deleted_count": res.rowcount if res.rowcount is not None and res.rowcount >= 0 else 0}

    elif payload.lead_ids:
        stmt = delete(Lead).where(Lead.id.in_(payload.lead_ids))
        res = await db.execute(stmt)
        await db.commit()
        return {"deleted_count": res.rowcount if res.rowcount is not None and res.rowcount >= 0 else 0}
    else:
        raise HTTPException(status_code=400, detail="Silinecek lead belirtilmedi")


@router.post("/bulk-blacklist")
async def bulk_blacklist_leads(payload: BulkBlacklistRequest, db: AsyncSession = Depends(get_db)):
    if payload.blacklist_all_matching:
        conditions = build_lead_filter_conditions(
            search=payload.search,
            city=payload.city,
            districts=payload.districts,
            categories=payload.categories,
            status=payload.status,
            whatsapp_eligible_only=payload.whatsapp_eligible_only or False
        )
        stmt = select(Lead)
        for c in conditions:
            stmt = stmt.where(c)
        res = await db.execute(stmt)
        leads = res.scalars().all()
    elif payload.lead_ids:
        stmt = select(Lead).where(Lead.id.in_(payload.lead_ids))
        res = await db.execute(stmt)
        leads = res.scalars().all()
    else:
        raise HTTPException(status_code=400, detail="Kara listeye eklenecek lead belirtilmedi")

    count = 0
    for lead in leads:
        lead.status = LeadStatus.UNSUBSCRIBED
        if lead.phone_e164:
            bl_stmt = select(Blacklist).where(Blacklist.phone_e164 == lead.phone_e164)
            bl_res = await db.execute(bl_stmt)
            if not bl_res.scalar_one_or_none():
                bl = Blacklist(phone_e164=lead.phone_e164, reason=payload.reason or "Toplu kara listeye eklendi")
                db.add(bl)
                count += 1

    await db.commit()
    return {"blacklisted_count": count, "leads_updated": len(leads)}


@router.post("/export/csv")
async def export_leads_csv(
    payload: Optional[ExportLeadsRequest] = Body(None),
    search: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[LeadStatus] = Query(None),
    whatsapp_eligible_only: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    # Support both JSON body and Query param requests
    req_search = payload.search if payload else search
    req_city = payload.city if payload else city
    req_districts = payload.districts if payload else None
    req_categories = payload.categories if payload else ([category] if category else None)
    req_status = payload.status if payload else status
    req_wa_only = payload.whatsapp_eligible_only if payload else whatsapp_eligible_only

    conditions = build_lead_filter_conditions(
        search=req_search,
        city=req_city,
        districts=req_districts,
        categories=req_categories,
        status=req_status,
        whatsapp_eligible_only=req_wa_only
    )

    query = select(Lead)
    for c in conditions:
        query = query.where(c)

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
    payload: Optional[ExportLeadsRequest] = Body(None),
    search: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[LeadStatus] = Query(None),
    whatsapp_eligible_only: bool = Query(False),
    db: AsyncSession = Depends(get_db)
):
    req_search = payload.search if payload else search
    req_city = payload.city if payload else city
    req_districts = payload.districts if payload else None
    req_categories = payload.categories if payload else ([category] if category else None)
    req_status = payload.status if payload else status
    req_wa_only = payload.whatsapp_eligible_only if payload else whatsapp_eligible_only

    conditions = build_lead_filter_conditions(
        search=req_search,
        city=req_city,
        districts=req_districts,
        categories=req_categories,
        status=req_status,
        whatsapp_eligible_only=req_wa_only
    )

    query = select(Lead)
    for c in conditions:
        query = query.where(c)

    res = await db.execute(query.order_by(Lead.id.desc()))
    leads = res.scalars().all()

    leads_dicts = [l.__dict__ for l in leads]
    excel_bytes = ExportService.export_excel(leads_dicts)

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=scoutify_leads.xlsx"}
    )
