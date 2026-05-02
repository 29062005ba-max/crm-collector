from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "CRM Collector"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://crm:crm@postgres:5432/crm_db"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://crm:crm@postgres:5432/crm_db"

    REDIS_URL: str = "redis://redis:6379/0"

    SECRET_KEY: str = "super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://frontend:3000",
        "https://localhost",
        "http://localhost",
        "https://192.168.8.222",
        "http://192.168.8.222",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
