"""
Falcon Kibertexnology School - Antiflood / Throttling Middleware.
Bitta foydalanuvchi 1 soniyada 1 tadan ko'p so'rov yubora olmasligini ta'minlaydi.
"""

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    """Foydalanuvchi so'rovlari chastotasini 1 soniyaga cheklovchi middleware."""

    def __init__(self, rate_limit: float = 1.0) -> None:
        self.rate_limit = rate_limit
        self._user_last_action: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        if (
            isinstance(event, Message)
            and event.from_user
            or isinstance(event, CallbackQuery)
            and event.from_user
        ):
            user_id = event.from_user.id

        if user_id:
            now = time.time()
            last_time = self._user_last_action.get(user_id, 0.0)
            if now - last_time < self.rate_limit:
                # Juda tez so'rov yuborildi
                if isinstance(event, CallbackQuery):
                    try:
                        await event.answer("⚠️ Iltimos, biroz kuting!", show_alert=False)
                    except Exception:
                        pass
                elif isinstance(event, Message):
                    try:
                        await event.answer(
                            "⚠️ Iltimos, juda tez xabar yubormang! (Sekundiga 1 ta so'rov)",
                            protect_content=True,
                        )
                    except Exception:
                        pass
                return None

            self._user_last_action[user_id] = now

        return await handler(event, data)
