"""
Falcon Kibertexnology School - Autentifikatsiya, Sessiya va Callback Xavfsizlik Middleware.
Barcha so'rovlarga asinxron baza sessiyasini yetkazadi,
oddiy foydalanuvchi admin callback_data yuborganida darhol rad etadi.
"""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.database.repositories.user_repo import UserRepository
from app.database.session import async_session_maker

# Faqat administratorlar uchun ruxsat etilgan callback prefikslari va amallari
ADMIN_CALLBACK_PREFIXES = ("st_act:", "grd:", "att:", "note:", "lsn:", "adm:")


class DatabaseAndAuthMiddleware(BaseMiddleware):
    """
    1. Baza sessiyasini (session) ochadi.
    2. Foydalanuvchini (current_user) yuklaydi yoki yaratadi.
    3. Oddiy foydalanuvchi admin callback yuborganida darhol bloklaydi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = None
        if isinstance(event, Message) and event.from_user:
            from_user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            from_user = event.from_user

        async with async_session_maker() as session:
            data["session"] = session
            user_repo = UserRepository(session)

            if from_user:
                user = await user_repo.get_by_telegram_id(from_user.id)
                if not user:
                    full_name = from_user.full_name or from_user.first_name or "Foydalanuvchi"
                    user = await user_repo.create_or_update(
                        telegram_id=from_user.id,
                        full_name=full_name,
                        role="user",
                    )
                data["current_user"] = user
            else:
                data["current_user"] = None

            # XAVFSIZLIK: Admin callback_data ni oddiy foydalanuvchidan himoya qilish
            if isinstance(event, CallbackQuery) and event.data:
                cb_data = event.data
                is_admin_action = any(
                    cb_data.startswith(prefix) for prefix in ADMIN_CALLBACK_PREFIXES
                ) or cb_data.startswith("nav:add_student")

                current_user = data.get("current_user")
                if is_admin_action and (not current_user or current_user.role != "admin"):
                    await event.answer(
                        "⛔️ Ruxsat yo'q! Bu amal faqat administratorlar uchun.",
                        show_alert=True,
                    )
                    return None

            return await handler(event, data)
