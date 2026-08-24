import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Scoutify"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./scoutify.db",
        description="Async SQLite or PostgreSQL connection string"
    )
    
    # Security / CORS
    SECRET_KEY: str = "scoutify-super-secret-production-key-change-in-prod"
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000"
    ]
    
    # WhatsApp Gateway Settings
    WA_GATEWAY_URL: str = "http://localhost:3001"
    WA_GATEWAY_WEBHOOK_SECRET: str = "wa-webhook-secret-scoutify"
    
    # Default Outreach Anti-Ban Thresholds
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

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
