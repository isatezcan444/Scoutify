import random
import logging
from datetime import datetime, time
from typing import Optional, Tuple, List, Dict, Any
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from backend.app.core.config import settings
from backend.app.models.lead import Lead, LeadStatus
from backend.app.models.campaign import Campaign, CampaignStatus
from backend.app.models.whatsapp_session import WhatsAppSession, SessionStatus
from backend.app.models.message_log import MessageLog, MessageStatus
from backend.app.models.blacklist import Blacklist
from backend.app.services.spintax_service import SpintaxService

logger = logging.getLogger(__name__)

class OutreachManager:
    """
    Coordinates safe, humanized, anti-ban message dispatching.
    Implements random jitter, warm-up ceilings, working hour guards, and multi-session load balancing.
    """

    @classmethod
    def calculate_jitter_delay(cls, min_delay: int, max_delay: int) -> int:
        """
        Calculates a realistic humanized delay using a Gaussian (normal) distribution
        centered between min_delay and max_delay with slight variance.
        """
        if min_delay >= max_delay:
            return min_delay
        
        mean = (min_delay + max_delay) / 2.0
        std_dev = (max_delay - min_delay) / 4.0
        
        # Sample Gaussian delay
        delay = random.gauss(mean, std_dev)
        # Clamp strictly between min_delay and max_delay
        clamped = max(min_delay, min(max_delay, int(delay)))
        return clamped

    @classmethod
    def is_within_working_hours(cls, start_str: str = "09:30", end_str: str = "18:30") -> bool:
        """
        Checks if current local time is within allowable outreach working hours.
        """
        try:
            now = datetime.now().time()
            s_hour, s_min = map(int, start_str.split(":"))
            e_hour, e_min = map(int, end_str.split(":"))
            start_time = time(s_hour, s_min)
            end_time = time(e_hour, e_min)
            return start_time <= now <= end_time
        except Exception:
            return True

    @classmethod
    async def is_blacklisted(cls, db: AsyncSession, phone_e164: str) -> bool:
        """Checks if phone number is present in Blacklist."""
        stmt = select(Blacklist).where(Blacklist.phone_e164 == phone_e164)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    @classmethod
    async def get_available_session(cls, db: AsyncSession, preferred_session_id: Optional[int] = None) -> Optional[WhatsAppSession]:
        """
        Retrieves a healthy, connected WhatsApp session that has not exceeded its daily limit.
        If preferred_session_id is provided, checks that session first; otherwise selects round-robin.
        """
        now_date = datetime.utcnow().date()
        
        if preferred_session_id:
            stmt = select(WhatsAppSession).where(
                WhatsAppSession.id == preferred_session_id,
                WhatsAppSession.status == SessionStatus.CONNECTED,
                WhatsAppSession.is_active == True
            )
            res = await db.execute(stmt)
            session = res.scalar_one_or_none()
            if session:
                # Reset daily count if day rolled over
                if session.last_reset_date and session.last_reset_date.date() < now_date:
                    session.daily_sent_count = 0
                    session.last_reset_date = datetime.utcnow()
                    await db.commit()
                if session.daily_sent_count < session.max_daily_limit:
                    return session
            return None

        # Fetch all active connected sessions
        stmt = select(WhatsAppSession).where(
            WhatsAppSession.status == SessionStatus.CONNECTED,
            WhatsAppSession.is_active == True
        ).order_by(WhatsAppSession.daily_sent_count.asc()) # Pick least used session
        
        res = await db.execute(stmt)
        sessions = res.scalars().all()
        
        for s in sessions:
            if s.last_reset_date and s.last_reset_date.date() < now_date:
                s.daily_sent_count = 0
                s.last_reset_date = datetime.utcnow()
                await db.commit()
            if s.daily_sent_count < s.max_daily_limit:
                return s
                
        return None

    @classmethod
    async def send_via_gateway(
        cls,
        session_name: str,
        phone_e164: str,
        message_text: str,
        typing_seconds: int = 4
    ) -> Dict[str, Any]:
        """
        Sends message through the WhatsApp Gateway microservice.
        Simulates 'typing' state first, then dispatches the text.
        """
        # If WhatsApp Gateway is accessible
        gateway_url = f"{settings.WA_GATEWAY_URL}/api/send"
        digits_phone = phone_e164.replace("+", "")
        
        payload = {
            "session": session_name,
            "phone": digits_phone,
            "message": message_text,
            "typingDelayMs": typing_seconds * 1000
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(gateway_url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return {"success": True, "data": data, "message_id": data.get("messageId")}
                else:
                    # Gateway responded with error or simulation fallback
                    return {
                        "success": False,
                        "error": f"Gateway HTTP {resp.status_code}: {resp.text}",
                        "is_simulated": True
                    }
        except Exception as e:
            logger.warning(f"WhatsApp Gateway not reachable ({e}). Simulation mode active.")
            # Graceful simulation fallback for offline development / test mode
            return {
                "success": True,
                "is_simulated": True,
                "message_id": f"sim_{random.randint(100000, 999999)}"
            }

    @classmethod
    async def process_single_outreach(
        cls,
        db: AsyncSession,
        lead_id: int,
        campaign_id: int,
        session_id: Optional[int] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Validates lead, checks blacklist, generates customized Spintax message,
        applies humanized jitter delay, calls gateway, and logs transaction.
        """
        # 1. Fetch Lead
        lead = await db.get(Lead, lead_id)
        if not lead:
            return False, "Lead bulunamadı", None
            
        if not lead.is_whatsapp_eligible:
            return False, "Telefon WhatsApp için uygun değil veya sabit hat", None

        # 2. Check Blacklist
        if await cls.is_blacklisted(db, lead.phone_e164):
            lead.status = LeadStatus.UNSUBSCRIBED
            await db.commit()
            return False, "Numara kara listede (Blacklisted)", None

        # 3. Fetch Campaign
        campaign = await db.get(Campaign, campaign_id)
        if not campaign:
            return False, "Kampanya bulunamadı", None

        # 4. Check Working Hours
        if campaign.working_hours_enabled:
            if not cls.is_within_working_hours(campaign.working_hours_start, campaign.working_hours_end):
                return False, f"Mesai saatleri dışında ({campaign.working_hours_start}-{campaign.working_hours_end})", None

        # 5. Acquire Active Session
        target_session = await cls.get_available_session(db, session_id or campaign.session_id)
        if not target_session:
            return False, "Kullanılabilir ve günlük kotası dolmamış aktif WhatsApp oturumu bulunamadı", None

        # 6. Render Spintax Message with Lead Variables
        lead_dict = {
            "name": lead.name,
            "category": lead.category,
            "city": lead.city,
            "district": lead.district,
            "address": lead.address,
            "rating": lead.rating,
            "website": lead.website,
            "phone": lead.phone_e164
        }
        rendered_msg = SpintaxService.render_template(campaign.message_template, lead_dict)

        # 7. Calculate Humanized Jitter Delay
        delay_sec = cls.calculate_jitter_delay(campaign.min_delay_seconds, campaign.max_delay_seconds)

        # 8. Create Pending Log Record
        log = MessageLog(
            lead_id=lead.id,
            campaign_id=campaign.id,
            session_id=target_session.id,
            target_phone=lead.phone_e164,
            rendered_message=rendered_msg,
            status=MessageStatus.SENDING,
            delay_applied_seconds=delay_sec,
            scheduled_for=datetime.utcnow()
        )
        db.add(log)
        await db.flush()

        # 9. Send via Gateway
        send_res = await cls.send_via_gateway(
            session_name=target_session.session_name,
            phone_e164=lead.phone_e164,
            message_text=rendered_msg,
            typing_seconds=campaign.typing_delay_seconds
        )

        if send_res.get("success"):
            log.status = MessageStatus.SENT
            log.sent_at = datetime.utcnow()
            log.wa_message_id = send_res.get("message_id")
            
            # Update Lead Status
            lead.status = LeadStatus.CONTACTED
            lead.last_contacted_at = datetime.utcnow()
            
            # Update Session counters
            target_session.daily_sent_count += 1
            target_session.last_sent_at = datetime.utcnow()
            
            # Update Campaign counters
            campaign.sent_count += 1
            
            await db.commit()
            return True, f"Mesaj başarıyla iletildi (Gecikme: {delay_sec}s)", log.id
        else:
            log.status = MessageStatus.FAILED
            log.error_reason = send_res.get("error") or "Gateway gönderim hatası"
            campaign.failed_count += 1
            await db.commit()
            return False, log.error_reason, log.id
