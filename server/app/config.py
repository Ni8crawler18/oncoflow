"""Application configuration.

Reads from environment / .env. Defaults to a local SQLite database so the
MVP runs with zero setup; point DATABASE_URL at Postgres for production.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "OncoFlow"
    environment: str = "development"

    # Postgres is the product database. Override via DATABASE_URL env var.
    # Render provides a URL like postgres://... — normalized below to the
    # SQLAlchemy + psycopg driver form.
    database_url: str = (
        "postgresql+psycopg://oncoflow:oncoflow@localhost:5432/oncoflow"
    )

    # Allowed frontend origins (comma-separated). Add your Vercel URL in prod,
    # e.g. CORS_ORIGINS="https://oncoflow.vercel.app,http://localhost:3000"
    cors_origins: str = "http://localhost:3000"

    @property
    def normalized_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # Auth. Override in production via JWT_SECRET env var.
    jwt_secret: str = "oncoflow-dev-secret-change-me"

    # Meta WhatsApp Cloud API. Leave credentials blank to run in mock mode
    # (messages are logged, not sent).
    meta_phone_number_id: str = ""
    meta_access_token: str = ""
    meta_verify_token: str = "oncoflow-verify"   # for webhook verification handshake
    meta_graph_version: str = "v21.0"

    # Telegram Bot API (patient chat channel)
    telegram_bot_token: str = ""

    # Sarvam AI — conversational patient follow-up.
    sarvam_api_key: str = ""
    sarvam_model: str = "sarvam-105b-conversations"

    # Proactive AI check-ins. A linked patient with no care-team contact in this
    # many days is "due" for an automatic check-in. CRON_SECRET guards the
    # unauthenticated cron endpoint that fires them across all doctors.
    checkin_interval_days: int = 7
    cron_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
