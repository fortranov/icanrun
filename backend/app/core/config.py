"""
Application configuration via pydantic-settings.
All settings are loaded from environment variables or .env file.
"""
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "ICanRun Triathlon App"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production-must-be-at-least-32-characters-long"

    # Database
    database_url: str = "sqlite+aiosqlite:///./icanrun.db"

    # JWT
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    # Google OAuth
    google_oauth_enabled: bool = False
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/auth/google/callback"

    # YooKassa
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_return_url: str = "http://localhost:3000/settings?payment=success"

    # Garmin encryption
    garmin_encryption_key: str = "change-me-garmin-key-32-bytes!!"

    # Strava OAuth
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = "http://localhost:3000/strava/callback"
    strava_webhook_verify_token: str = "icanrun-strava-webhook-token"
    # Optional HTTP/SOCKS5 proxy for Strava API calls (needed on geo-blocked servers)
    # Example: "socks5://user:pass@host:port" or "http://host:port"
    strava_proxy_url: str = ""

    # Admin user (created on startup if not exists)
    admin_email: str = "abramov.yu.v@gmail.com"
    admin_password: str = "3tuka2puka"

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # API
    api_v1_prefix: str = "/api/v1"


settings = Settings()
