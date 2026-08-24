"""
WhatsApp Gönderici Arayüzü ve Somut Uygulamaları.

- `WhatsAppSender`: Gönderici arayüzü (Protocol)
- `SimulatedSender`: SIMULATION_MODE=True iken güvenli ve gecikmeli sanal gönderim yapar,
  asla gerçek ağ çağrısı yapmaz ve yanıtta 'is_simulated': True bilgisini açıkça belirtir.
- `GatewaySender`: wa-gateway mikroservisine HTTP isteği gönderir; hata durumunda asla
  sahte 'success: True' yalanı söylemez, gerçek hatayı döndürür.
"""
import logging
import random
from typing import Protocol, Dict, Any, Optional
import httpx

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppSender(Protocol):
    """WhatsApp mesaj gönderim kontratı."""

    async def send_message(
        self,
        session_name: str,
        phone_e164: str,
        message_text: str,
        typing_seconds: int = 4,
    ) -> Dict[str, Any]:
        """
        Mesajı iletir.
        Dönüş formatı:
        {
            "success": bool,
            "message_id": Optional[str],
            "is_simulated": bool,
            "error": Optional[str]
        }
        """
        ...


class SimulatedSender:
    """Geliştirme ve test için şeffaf simülasyon göndericisi."""

    async def send_message(
        self,
        session_name: str,
        phone_e164: str,
        message_text: str,
        typing_seconds: int = 4,
    ) -> Dict[str, Any]:
        message_id = f"sim_{DateStamp()}_{random.randint(100000, 999999)}"
        logger.info(
            f"[SimulatedSender] (DEMO) Mesaj iletildi: session={session_name}, "
            f"phone={phone_e164}, msg_len={len(message_text)}, id={message_id}"
        )
        return {
            "success": True,
            "message_id": message_id,
            "is_simulated": True,
            "error": None,
        }


def DateStamp() -> int:
    import time
    return int(time.time())


class GatewaySender:
    """Gerçek wa-gateway mikroservisine bağlanan gönderici."""

    def __init__(self, gateway_url: Optional[str] = None, auth_token: Optional[str] = None):
        self.gateway_url = (gateway_url or settings.WA_GATEWAY_URL).rstrip("/")
        self.auth_token = auth_token or settings.WA_GATEWAY_AUTH_TOKEN

    async def send_message(
        self,
        session_name: str,
        phone_e164: str,
        message_text: str,
        typing_seconds: int = 4,
    ) -> Dict[str, Any]:
        url = f"{self.gateway_url}/api/send"
        digits_phone = phone_e164.replace("+", "").replace(" ", "").replace("-", "")

        payload = {
            "session": session_name,
            "phone": digits_phone,
            "message": message_text,
            "typingDelayMs": typing_seconds * 1000,
        }

        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        try:
            async with httpx.AsyncClient(timeout=15.0, verify=True) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "success": True,
                        "message_id": data.get("messageId"),
                        "is_simulated": False,
                        "error": None,
                    }
                else:
                    error_msg = f"Gateway HTTP {resp.status_code}: {resp.text}"
                    logger.error(f"[GatewaySender] Gönderim başarısız: {error_msg}")
                    return {
                        "success": False,
                        "message_id": None,
                        "is_simulated": False,
                        "error": error_msg,
                    }
        except Exception as e:
            error_msg = f"Gateway bağlantı hatası: {str(e)}"
            logger.error(f"[GatewaySender] {error_msg}")
            return {
                "success": False,
                "message_id": None,
                "is_simulated": False,
                "error": error_msg,
            }


def get_whatsapp_sender(force_simulation: Optional[bool] = None) -> WhatsAppSender:
    """Mevcut ortam yapılandırmasına göre uygun göndericiyi üretir."""
    is_sim = settings.SIMULATION_MODE if force_simulation is None else force_simulation
    if is_sim:
        return SimulatedSender()
    return GatewaySender()
