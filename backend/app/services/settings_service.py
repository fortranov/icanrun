"""
AppSettings service.

Reads/writes application settings stored in the `app_settings` DB table.

Settings are plain key/value strings. Typed accessors and mutators convert
them to the appropriate Python type on the fly.

Default values are returned when a key is not yet present in the DB
(covers the case where the row was never seeded).
"""
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_setting import AppSetting

logger = logging.getLogger(__name__)

# Canonical setting keys ---------------------------------------------------- #
KEY_EMAIL_CONFIRMATION_ENABLED = "email_confirmation_enabled"
KEY_SMTP_HOST = "smtp_host"
KEY_SMTP_PORT = "smtp_port"
KEY_SMTP_USER = "smtp_user"
KEY_SMTP_PASSWORD = "smtp_password"
KEY_SMTP_FROM_EMAIL = "smtp_from_email"
KEY_SMTP_FROM_NAME = "smtp_from_name"
KEY_CONFIRMATION_TOKEN_HOURS = "confirmation_token_hours"

_DEFAULTS: dict[str, str] = {
    KEY_EMAIL_CONFIRMATION_ENABLED: "false",
    KEY_SMTP_HOST: "",
    KEY_SMTP_PORT: "587",
    KEY_SMTP_USER: "",
    KEY_SMTP_PASSWORD: "",
    KEY_SMTP_FROM_EMAIL: "",
    KEY_SMTP_FROM_NAME: "ICanRun",
    KEY_CONFIRMATION_TOKEN_HOURS: "24",
}


class SettingsService:
    """CRUD helpers for the app_settings table."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------ #
    # Low-level get / set                                                  #
    # ------------------------------------------------------------------ #

    async def get(self, key: str) -> str:
        """Return the string value for *key*, or its default if not set."""
        result = await self.db.execute(
            select(AppSetting).where(AppSetting.key == key)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return _DEFAULTS.get(key, "")
        return row.value

    async def set(self, key: str, value: str) -> None:
        """Upsert a setting value."""
        result = await self.db.execute(
            select(AppSetting).where(AppSetting.key == key)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = AppSetting(key=key, value=value)
            self.db.add(row)
        else:
            row.value = value
        # caller is responsible for commit / flush

    # ------------------------------------------------------------------ #
    # Typed accessors                                                      #
    # ------------------------------------------------------------------ #

    async def get_all(self) -> dict[str, str]:
        """Return all settings as a plain dict (including defaults for missing keys)."""
        result = await self.db.execute(select(AppSetting))
        rows = {row.key: row.value for row in result.scalars().all()}
        # Merge with defaults so we always return the full set of known keys
        merged = dict(_DEFAULTS)
        merged.update(rows)
        return merged

    async def email_confirmation_enabled(self) -> bool:
        v = await self.get(KEY_EMAIL_CONFIRMATION_ENABLED)
        return v.lower() == "true"

    async def smtp_host(self) -> str:
        return await self.get(KEY_SMTP_HOST)

    async def smtp_port(self) -> int:
        return int(await self.get(KEY_SMTP_PORT) or "587")

    async def smtp_user(self) -> str:
        return await self.get(KEY_SMTP_USER)

    async def smtp_password(self) -> str:
        return await self.get(KEY_SMTP_PASSWORD)

    async def smtp_from_email(self) -> str:
        return await self.get(KEY_SMTP_FROM_EMAIL)

    async def smtp_from_name(self) -> str:
        return await self.get(KEY_SMTP_FROM_NAME)

    async def confirmation_token_hours(self) -> int:
        return int(await self.get(KEY_CONFIRMATION_TOKEN_HOURS) or "24")

    # ------------------------------------------------------------------ #
    # Bulk update (used by admin endpoint)                                 #
    # ------------------------------------------------------------------ #

    async def update_many(self, updates: dict[str, str]) -> None:
        """Update multiple settings at once. Unknown keys are silently ignored."""
        known_keys = set(_DEFAULTS.keys())
        for key, value in updates.items():
            if key not in known_keys:
                logger.warning(f"SettingsService.update_many: unknown key '{key}' ignored")
                continue
            await self.set(key, value)
