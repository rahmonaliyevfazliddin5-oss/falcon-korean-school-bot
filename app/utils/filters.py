"""
Falcon Kibertexnology School - Aiogram maxsus filterlari.
Foydalanuvchi rollarini (admin, ota-ona) xavfsiz tekshirish uchun.
"""

from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message

from app.database.models import User


class IsAdminFilter(Filter):
    """Faqat 'admin' roliga ega foydalanuvchilarni o'tkazuvchi filter."""

    async def __call__(
        self,
        event: Message | CallbackQuery,
        current_user: User | None = None,
    ) -> bool:
        if current_user and current_user.role == "admin":
            return True
        return False


class IsParentFilter(Filter):
    """Ota-ona yoki o'quvchi roliga ega foydalanuvchilar uchun filter."""

    async def __call__(
        self,
        event: Message | CallbackQuery,
        current_user: User | None = None,
    ) -> bool:
        if current_user and current_user.role in ("parent", "student"):
            return True
        return False
