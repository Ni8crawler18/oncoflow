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

    # Twilio / WhatsApp. Leave credentials blank to run in mock mode (messages
    # are logged, not sent). Inbound webhook still works for the demo.
    #
    # Two auth styles are supported:
    #   1. Account SID (AC...) + Auth Token
    #   2. API Key SID (SK...) + API Key Secret + Account SID (AC...)
    twilio_account_sid: str = ""          # AC...  (required to actually send)
    twilio_auth_token: str = ""           # account auth token (style 1)
    twilio_api_key_sid: str = ""          # SK...  (style 2)
    twilio_api_key_secret: str = ""       # api key secret (style 2)
    twilio_whatsapp_from: str = "whatsapp:+14155238886"  # Twilio sandbox number

    # Sarvam AI — conversational patient follow-up.
    sarvam_api_key: str = ""
    sarvam_model: str = "sarvam-105b-conversations"

    @property
    def twilio_configured(self) -> bool:
        if self.twilio_account_sid and self.twilio_auth_token:
            return True
        return bool(
            self.twilio_api_key_sid
            and self.twilio_api_key_secret
            and self.twilio_account_sid
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
