import collections
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update

from backend.app.api.v1.api import api_router
from backend.app.api.v1.websocket import ws_manager
from backend.app.core.config import settings
from backend.app.core.database import Base, engine
from backend.app.core.migrations import (
    ensure_leads_phone_nullable,
    ensure_conversations_columns,
    ensure_messages_media_columns,
)
from backend.app.core.seed import seed_demo_data_if_empty
from backend.app.models.blacklist import ScraperJob, ScraperJobStatus
from backend.app.models.campaign import Campaign, CampaignStatus

# In-memory log handler for live diagnostics
class MemoryLogHandler(logging.Handler):
    def __init__(self, capacity: int = 300):
        super().__init__()
        self.buffer = collections.deque(maxlen=capacity)

    def emit(self, record):
        try:
            msg = self.format(record)
            self.buffer.append(msg)
        except Exception:
            pass

memory_log_handler = MemoryLogHandler()
memory_log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logging.getLogger().addHandler(memory_log_handler)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("scoutify")


async def recover_stuck_jobs() -> None:
    """Sunucu yeniden başlatıldığında arka planda kalmış işleri güvenli duruma alır.

    - Aktif (ACTIVE) kampanyalar -> PAUSED (kullanıcı devam kararı verir)
    - RUNNING/PENDING tarama işleri -> FAILED ( açık mesajla)
    """
    from backend.app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        paused = await db.execute(
            update(Campaign)
            .where(Campaign.status == CampaignStatus.ACTIVE)
            .values(status=CampaignStatus.PAUSED)
        )
        failed = await db.execute(
            update(ScraperJob)
            .where(ScraperJob.status.in_([ScraperJobStatus.RUNNING, ScraperJobStatus.PENDING]))
            .values(
                status=ScraperJobStatus.FAILED,
                error_message="Sunucu yeniden başlatıldı; iş kaldırıldı. Yeniden başlatın.",
            )
        )
        await db.commit()
        if paused.rowcount:
            logger.warning("[RECOVERY] %d ACTIVE kampanya PAUSED durumuna alındı.", paused.rowcount)
        if failed.rowcount:
            logger.warning("[RECOVERY] %d takılı tarama işi FAILED durumuna alındı.", failed.rowcount)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Connecting to Database & Creating Tables...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Bilinen şema geçişleri (idempotent)
        await ensure_leads_phone_nullable(engine)
        await ensure_conversations_columns(engine)
        await ensure_messages_media_columns(engine)

        # Restart sonrası yarıda kalan arka plan işlerini toparla
        await recover_stuck_jobs()

        if settings.SEED_DEMO_DATA:
            await seed_demo_data_if_empty()
    except Exception as e:
        logger.error(f"[STARTUP_ERROR] Database/seed initialization exception: {e}", exc_info=True)

    yield
    # Cleanup
    try:
        await engine.dispose()
    except Exception as e:
        logger.warning(f"Engine dispose exception: {e}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Scoutify - B2B Lead Generation & Automated WhatsApp Outreach Platform API",
    lifespan=lifespan,
)

# CORS Configuration: Allow all origins so Vercel preview branches and custom domains never get blocked
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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


@app.get("/system-log", tags=["Health"])
async def get_system_log():
    return {"logs": list(memory_log_handler.buffer)}


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "ok",
        "service": "Scoutify Backend API",
        "docs": "/docs",
        "health": "/health",
        "version": settings.VERSION,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "Scoutify Backend API",
        "version": settings.VERSION,
        "simulation_mode": settings.SIMULATION_MODE,
    }
