from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Uygulama genelinde tek yapılandırma kaynağı.

    Tüm varsayılanlar geliştirme (development) içindir; üretimde .env ile
    ezilmelidir (bkz. .env.example). Varsayılan değerlerin üretim için
    güvenli olduğu varsayılmaz.
    """

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "Scoutify"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./scoutify.db",
        description="Async SQLite or PostgreSQL connection string",
    )

    # Çalışma modu
    # True  -> WhatsApp gönderim zinciri SimulatedSender ile çalışır (hiçbir
    #          gerçek mesaj gitmez; loglar ve API yanıtları "simulated" işaretlenir).
    # False -> GatewaySender gerçek wa-gateway servisine HTTP çağrısı yapar.
    #          wa-gateway şu an Baileys içermeyen bir simülatördür; False yapmadan
    # önce gerçek gönderici entegrasyonunun tamamlandığından emin olun.
    SIMULATION_MODE: bool = True

    # Demo verisi: boş veritabanına örnek oturum/kampanya/lead ekler.
    # Üretimde kapatın.
    SEED_DEMO_DATA: bool = True

    # Security / CORS
    SECRET_KEY: str = Field(
        default="dev-only-insecure-secret-key",
        description="Üretimde mutlaka .env ile güçlü bir değerle ezilmelidir.",
    )
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # WhatsApp Gateway Settings
    WA_GATEWAY_URL: str = "http://localhost:3001"
    # Gateway'in /api/v1/whatsapp/webhook/inbound çağrılarında göndermesi
    # zorunlu olan gizli anahtar (header: X-Webhook-Secret).
    WA_GATEWAY_WEBHOOK_SECRET: str = Field(
        default="dev-webhook-secret",
        description="Üretimde .env ile değiştirilmelidir; webhook bu değerle doğrulanır.",
    )
    # wa-gateway /api/send çağrıları için opsiyonel Bearer token.
    # Boş bırakılırsa gateway auth istemez (yalnızca güvenli ağda çalıştırın).
    WA_GATEWAY_AUTH_TOKEN: str = ""

    # Default Outreach Anti-Ban Thresholds
    # Tek doğruluk kaynağı burasıdır; Campaign model varsayılanları ve
    # AntibanPolicy bu değerlerden beslenir.
    DEFAULT_MIN_DELAY_SECONDS: int = 45
    DEFAULT_MAX_DELAY_SECONDS: int = 120
    DEFAULT_TYPING_DELAY_SECONDS: int = 5
    DEFAULT_DAILY_LIMIT_PER_SESSION: int = 50
    DEFAULT_WORKING_HOURS_START: str = "09:30"
    DEFAULT_WORKING_HOURS_END: str = "18:30"

    # Scraper Settings
    SCRAPER_USER_AGENT: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    SCRAPER_MAX_CONCURRENT_TASKS: int = 3
    SCRAPER_REQUEST_TIMEOUT: int = 30
    # Page navigation timeout for Google Maps sessions (ms)
    SCRAPER_PAGE_TIMEOUT_MS: int = 30000
    # "Sınırsız" modda ilçe başına hedef işletme sayısı
    SCRAPER_UNLIMITED_DISTRICT_TARGET: int = 200
    # "Sınırsız" modda ilçe başına maksimum scroll iterasyonu
    SCRAPER_MAX_SCROLL_ITERATIONS: int = 40
    # Scroll sonrası yeni kartların yüklenmesi için beklenen üst sınır (ms)
    SCROLLER_SETTLE_TIMEOUT_MS: int = 6000
    # Zaman bazlı stagnasyon eşiği: bu süre boyunca hiç yeni kart görülmezse
    # sonuç listesinin bittiği kabul edilir (saniye)
    SCRAPER_STAGNATION_TIMEOUT_SECONDS: float = 12.0
    # Website telefon zenginleştirme HTTP timeout'u (saniye)
    SCRAPER_ENRICH_TIMEOUT_SECONDS: float = 4.0
    # Sektör etiketinden türetilecek maksimum arama varyantı sayısı
    SCRAPER_MAX_QUERY_VARIANTS: int = 3
    # Coğrafi çit: adresi hedef ilçe dışını kanıtlayan işletmeleri ele
    SCRAPER_GEO_FILTER_ENABLED: bool = True
    # İlçe kanıtı taşımayan (CITY_ONLY/UNKNOWN) adresleri de ele (en katı mod)
    SCRAPER_REJECT_UNPROVEN_LOCATION: bool = False


settings = Settings()
