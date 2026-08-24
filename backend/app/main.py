import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.core.database import engine, Base, AsyncSessionLocal
from backend.app.api.v1.api import api_router
from backend.app.api.v1.websocket import ws_manager
from backend.app.models.lead import Lead, LeadStatus
from backend.app.models.whatsapp_session import WhatsAppSession, SessionStatus
from backend.app.models.campaign import Campaign, CampaignStatus
from sqlalchemy import select, func

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("scoutify")

async def init_seed_data():
    """Initializes sample initial data if database is empty."""
    async with AsyncSessionLocal() as db:
        # Check if sessions exist
        sess_count = await db.execute(select(func.count(WhatsAppSession.id)))
        if sess_count.scalar_one() == 0:
            default_session = WhatsAppSession(
                session_name="Ana Hat (Satış)",
                phone_number="+905321002030",
                status=SessionStatus.CONNECTED,
                warm_up_day=3,
                daily_sent_count=12,
                max_daily_limit=60,
                is_phone_online=True,
                battery_level=88
            )
            db.add(default_session)
            await db.flush()

            # Seed Sample Campaign
            sample_campaign = Campaign(
                name="Diş Klinikleri B2B Tanıtım",
                description="İstanbul geneli diş kliniklerine yönelik randevu yazılımı tanıtım kampanyası",
                message_template="{Merhaba|Selamlar|İyi günler} {name} Yetkilisi,\n\n{city} {district} bölgesindeki {category} profilinizi inceledik. Google'daki {rating} yıldızlı puanınız çok başarılı! 🌟\n\nKlinikler için geliştirdiğimiz otomatik WhatsApp randevu ve hatırlatma sistemimizle hasta kaçırma oranını %40 azaltıyoruz. Size 2 dakikalık kısa bir demo sunabilir miyiz?\n\n{İyi çalışmalar dileriz|Saygılarımızla}.",
                status=CampaignStatus.ACTIVE,
                min_delay_seconds=45,
                max_delay_seconds=110,
                typing_delay_seconds=5,
                session_id=default_session.id,
                total_leads_target=25,
                sent_count=12,
                delivered_count=12,
                replied_count=3,
                failed_count=0
            )
            db.add(sample_campaign)

            # Seed Initial Leads
            leads_data = [
                {
                    "name": "Özel DentaLine Ağız ve Diş Sağlığı",
                    "category": "Diş Kliniği",
                    "phone": "0532 987 65 43",
                    "phone_e164": "+905329876543",
                    "is_mobile": True,
                    "is_whatsapp_eligible": True,
                    "city": "İstanbul",
                    "district": "Ümraniye",
                    "address": "Atatürk Mah. Alemdağ Cad. No:142 Ümraniye / İstanbul",
                    "rating": 4.9,
                    "reviews_count": 184,
                    "website": "https://www.dentaline.com.tr",
                    "status": LeadStatus.REPLIED,
                    "search_keyword": "diş klinikleri",
                    "search_location": "İstanbul Ümraniye"
                },
                {
                    "name": "Estetik Diş Dünyası Polikliniği",
                    "category": "Diş Kliniği",
                    "phone": "0544 123 45 67",
                    "phone_e164": "+905441234567",
                    "is_mobile": True,
                    "is_whatsapp_eligible": True,
                    "city": "İstanbul",
                    "district": "Kadıköy",
                    "address": "Moda Cad. No:55 Kadıköy / İstanbul",
                    "rating": 4.8,
                    "reviews_count": 92,
                    "website": "https://www.estetikdisdunyasi.com",
                    "status": LeadStatus.CONTACTED,
                    "search_keyword": "diş klinikleri",
                    "search_location": "İstanbul Kadıköy"
                },
                {
                    "name": "Megadent Dental Hospital",
                    "category": "Diş Hastanesi",
                    "phone": "0533 555 88 99",
                    "phone_e164": "+905335558899",
                    "is_mobile": True,
                    "is_whatsapp_eligible": True,
                    "city": "İstanbul",
                    "district": "Ataşehir",
                    "address": "Barbaros Mah. Mor Sümbül Sok. Ataşehir / İstanbul",
                    "rating": 4.7,
                    "reviews_count": 310,
                    "website": "https://www.megadent.com.tr",
                    "status": LeadStatus.NEW,
                    "search_keyword": "diş hastanesi",
                    "search_location": "İstanbul Ataşehir"
                },
                {
                    "name": "SmileArt Ortodonti & İmplant",
                    "category": "Diş Kliniği",
                    "phone": "0535 777 44 22",
                    "phone_e164": "+905357774422",
                    "is_mobile": True,
                    "is_whatsapp_eligible": True,
                    "city": "İstanbul",
                    "district": "Beşiktaş",
                    "address": "Nispetiye Cad. Levent / Beşiktaş",
                    "rating": 5.0,
                    "reviews_count": 64,
                    "website": "https://www.smileartclinic.com",
                    "status": LeadStatus.NEW,
                    "search_keyword": "ortodonti kliniği",
                    "search_location": "İstanbul Beşiktaş"
                }
            ]

            for l_data in leads_data:
                lead = Lead(**l_data)
                db.add(lead)

            await db.commit()
            logger.info("Seed demo data initialized successfully.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB Tables
    logger.info("Connecting to Database & Creating Tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    await init_seed_data()
    yield
    # Cleanup
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Scoutify - B2B Lead Generation & Automated WhatsApp Outreach Platform API",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for dev flexibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for ping/pong
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket exception: {e}")
        ws_manager.disconnect(websocket)

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "Scoutify Backend API",
        "version": settings.VERSION
    }
