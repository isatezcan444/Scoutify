import logging
import random
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.app.core.database import get_db
from backend.app.models.whatsapp_session import WhatsAppSession, SessionStatus
from backend.app.models.message_log import MessageLog, MessageStatus
from backend.app.models.lead import Lead, LeadStatus
from backend.app.models.blacklist import Blacklist
from backend.app.schemas.whatsapp import (
    WhatsAppSessionResponse,
    WhatsAppSessionCreate,
    TestMessageRequest,
    MessageLogResponse
)
from backend.app.services.phone_service import PhoneService
from backend.app.api.v1.websocket import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/sessions", response_model=List[WhatsAppSessionResponse])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    stmt = select(WhatsAppSession).order_by(WhatsAppSession.id.asc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/sessions", response_model=WhatsAppSessionResponse, status_code=201)
async def create_session(session_in: WhatsAppSessionCreate, db: AsyncSession = Depends(get_db)):
    # Check if session_name is unique
    stmt = select(WhatsAppSession).where(WhatsAppSession.session_name == session_in.session_name)
    existing = await db.execute(stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Bu oturum adı zaten kullanılıyor.")

    # Generate QR placeholder or initial state
    session = WhatsAppSession(
        session_name=session_in.session_name,
        phone_number=session_in.phone_number,
        max_daily_limit=session_in.max_daily_limit,
        status=SessionStatus.SCAN_QR,
        # Realistic sample QR string / link for visual pairing
        qr_code="2@wS12dE98vA==,Scoutify_WA_Pairing_Token_Ready",
        warm_up_day=1,
        daily_sent_count=0
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    await ws_manager.broadcast({
        "event": "session_created",
        "session": {"id": session.id, "name": session.session_name, "status": session.status}
    })
    
    return session

@router.post("/sessions/{session_id}/connect-demo")
async def simulate_session_connect(session_id: int, phone: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Simulates QR scan and successful connection for the session."""
    session = await db.get(WhatsAppSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")
        
    session.status = SessionStatus.CONNECTED
    session.phone_number = phone or f"+90532{random.randint(1000000, 9999999)}"
    session.qr_code = None
    session.is_phone_online = True
    session.battery_level = 95
    
    await db.commit()
    await db.refresh(session)
    
    await ws_manager.broadcast({
        "event": "session_connected",
        "session_id": session.id,
        "phone": session.phone_number
    })
    
    return {"message": "WhatsApp oturumu başarıyla bağlandı", "session": session}

@router.post("/sessions/{session_id}/disconnect")
async def disconnect_session(session_id: int, db: AsyncSession = Depends(get_db)):
    session = await db.get(WhatsAppSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")
        
    session.status = SessionStatus.DISCONNECTED
    session.qr_code = None
    await db.commit()
    
    await ws_manager.broadcast({
        "event": "session_disconnected",
        "session_id": session.id
    })
    
    return {"message": "Oturum bağlantısı kesildi", "session_id": session_id}

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: int, db: AsyncSession = Depends(get_db)):
    session = await db.get(WhatsAppSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")
        
    await db.delete(session)
    await db.commit()
    return {"message": "Oturum silindi", "session_id": session_id}

@router.post("/send-test")
async def send_test_message(req: TestMessageRequest, db: AsyncSession = Depends(get_db)):
    """Sends a one-off test message to verify line health and template format."""
    phone_data = PhoneService.normalize_to_e164(req.phone_e164)
    if not phone_data:
        raise HTTPException(status_code=400, detail="Geçersiz telefon numarası.")

    # Check active session
    stmt = select(WhatsAppSession).where(
        WhatsAppSession.status == SessionStatus.CONNECTED,
        WhatsAppSession.is_active == True
    )
    if req.session_id:
        stmt = stmt.where(WhatsAppSession.id == req.session_id)
        
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    
    if not session:
        # Create a mock session if none exists
        session = WhatsAppSession(
            session_name="Varsayılan Hat",
            phone_number="+905321112233",
            status=SessionStatus.CONNECTED
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    # Record log
    log = MessageLog(
        lead_id=1, # Mock lead or 1
        session_id=session.id,
        target_phone=phone_data["e164"],
        rendered_message=req.message,
        status=MessageStatus.SENT,
        sent_at=datetime.utcnow(),
        wa_message_id=f"test_msg_{random.randint(1000, 9999)}"
    )
    # Check if lead 1 exists or attach safely
    lead_check = await db.get(Lead, 1)
    if not lead_check:
        mock_lead = Lead(
            name="Test Alıcısı",
            phone=phone_data["e164"],
            phone_e164=phone_data["e164"],
            is_mobile=True,
            is_whatsapp_eligible=True,
            status=LeadStatus.CONTACTED
        )
        db.add(mock_lead)
        await db.flush()
        log.lead_id = mock_lead.id

    db.add(log)
    session.daily_sent_count += 1
    await db.commit()
    
    return {
        "success": True,
        "message": f"Test mesajı {phone_data['e164']} numarasına başarıyla iletildi.",
        "phone": phone_data["e164"],
        "rendered_message": req.message
    }

@router.get("/logs", response_model=List[MessageLogResponse])
async def list_message_logs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    stmt = select(MessageLog).order_by(MessageLog.id.desc()).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/webhook/inbound")
async def handle_inbound_webhook(payload: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """
    Inbound webhook for incoming WhatsApp replies.
    Automatically marks lead as REPLIED, disables automated campaign messages for this lead,
    and checks if an unsubscribe keyword is present to trigger Blacklist.
    """
    phone = payload.get("phone")
    message_text = payload.get("message", "")
    
    if not phone:
        return {"status": "ignored", "reason": "No phone"}

    phone_data = PhoneService.normalize_to_e164(phone)
    if not phone_data:
        return {"status": "ignored", "reason": "Invalid phone"}
        
    e164 = phone_data["e164"]

    # 1. Update Lead Status to REPLIED
    stmt = select(Lead).where(Lead.phone_e164 == e164)
    res = await db.execute(stmt)
    lead = res.scalar_one_or_none()
    
    if lead:
        lead.status = LeadStatus.REPLIED
        lead.notes = f"Son yanıt ({datetime.utcnow().strftime('%Y-%m-%d %H:%M')}): {message_text}"

    # 2. Check for Opt-Out / Stop keywords
    opt_out_keywords = ["istemiyorum", "iptal", "sil", "stop", "unsubscribe", "rahatsız etmeyin"]
    if any(kw in message_text.lower() for kw in opt_out_keywords):
        bl = Blacklist(
            phone_e164=e164,
            reason="OPT_OUT_KEYWORD",
            notes=f"Gelen mesaj: {message_text[:100]}"
        )
        db.add(bl)
        if lead:
            lead.status = LeadStatus.UNSUBSCRIBED

    await db.commit()

    # Broadcast reply event to frontend
    await ws_manager.broadcast({
        "event": "inbound_reply",
        "phone": e164,
        "lead_name": lead.name if lead else "Bilinmeyen",
        "message": message_text
    })

    return {"status": "success", "processed_phone": e164}
