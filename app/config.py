"""
Falcon Kibertexnology School - Konfiguratsiya sozlamalari.
Pydantic-settings orqali .env fayldan o'qib olinadi.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Loyiha sozlamalari klassi."""

    BOT_TOKEN: str = ""
    ADMIN_IDS: str = ""
    DATABASE_URL: str = "sqlite+aiosqlite:///./falcon_school.db"
    LESSON_GROUP_ID: int | str = 0
    LOG_LEVEL: str = "INFO"
    WEBAPP_URL: str = ""
    PORT: int = 8080
    FINE_AMOUNT: int = 10000

    @property
    def admin_ids_list(self) -> list[int]:
        """ADMIN_IDS satrini butun sonlar (Telegram ID) ro'yxatiga aylantirish."""
        if not self.ADMIN_IDS:
            return []
        result: list[int] = []
        for item in self.ADMIN_IDS.split(","):
            cleaned = item.strip()
            if cleaned and (
                cleaned.isdigit() or (cleaned.startswith("-") and cleaned[1:].isdigit())
            ):
                result.append(int(cleaned))
        return result

    @property
    def lesson_group_id_int(self) -> int:
        """Guruh ID sini xavfsiz int ga aylantirish."""
        try:
            return int(self.LESSON_GROUP_ID)
        except (ValueError, TypeError):
            return 0

    def is_admin(self, telegram_id: int) -> bool:
        """Berilgan telegram_id adminlar ro'yxatida borligini tekshirish."""
        return telegram_id in self.admin_ids_list

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
