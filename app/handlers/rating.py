"""
Falcon Kibertexnology School - Reyting Handlerlari (rating.py).
Botdagi '🏆 Reyting' doimiy reply-tugmasi orqali haftalik TOP-4 reytingni chiqaradi.
"""

from aiogram import F, Router
from aiogram.types import Message

import db

rating_router = Router(name="weekly_rating_router")


@rating_router.message(F.text == "🏆 Reyting")
async def handle_weekly_rating_menu(message: Message) -> None:
    """
    Haftalik TOP-4 reytingni chiqarish:
    - Hafta: Dushanba dan Shanba gacha.
    - Ballar: uyga vazifa baholari yig'indisi.
    - Faqat top-4 ko'rsatiladi.
    - Ballar teng bo'lsa, ism bo'yicha alifbo tartibida.
    - Baho bo'lmasa: 'Hozircha reyting yo'q'.
    - Qarz / jarima / davomat ma'lumotlari kiritilmaydi.
    """
    text, _ = await db.get_weekly_top_rating()
    await message.answer(text=text, protect_content=True)
