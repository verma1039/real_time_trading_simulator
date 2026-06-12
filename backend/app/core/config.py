from decimal import Decimal
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    app_name: str = "Trading Simulator API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    # ── Database (PostgreSQL via Neon / local) ───────────────────
    database_url: str = "postgresql+psycopg://localhost:5432/trading_sim_dev"

    # ── Frontend ─────────────────────────────────────────────────
    frontend_url: str = "http://localhost:5173"
    frontend_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    # ── JWT / Auth ───────────────────────────────────────────────
    jwt_secret: str = "CHANGE-ME-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    # ── Email (Gmail SMTP) ───────────────────────────────────────
    gmail_address: str = ""
    gmail_app_password: str = ""

    # ── Portfolio defaults ───────────────────────────────────────
    opening_balance: Decimal = Decimal("1000000.0000")

    @field_validator("database_url")
    @classmethod
    def normalize_postgres_scheme(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
