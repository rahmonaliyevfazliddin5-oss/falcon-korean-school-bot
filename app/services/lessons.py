"""
Falcon Kibertexnology School - Darslar xizmati (LessonService).
Darslarni rejalashtirish, boshlash (havola yaratish va xabarnoma tarqatish),
tugatish va guruh xavfsizligini tekshirish.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Lesson, LessonComment
from app.database.repositories.comment_repo import LessonCommentRepository
from app.database.repositories.lesson_repo import LessonRepository
from app.database.repositories.user_repo import UserRepository


class LessonService:
    """Darslar va video mashg'ulotlarni boshqarish xizmati."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.lesson_repo = LessonRepository(session)
        self.comment_repo = LessonCommentRepository(session)
        self.user_repo = UserRepository(session)

    async def create_lesson(
        self,
        title: str,
        starts_at: datetime,
        created_by: int | None = None,
    ) -> Lesson:
        """Yangi dars rejalashtirish."""
        return await self.lesson_repo.create(
            title=title, starts_at=starts_at, created_by=created_by
        )

    async def start_lesson(
        self,
        bot: Bot,
        lesson_id: int,
        group_id: int,
    ) -> tuple[Lesson | None, str, int]:
        """
        Darsni boshlash:
        1. Status = 'davom_etmoqda' qilinadi.
        2. Yopiq dars guruhi uchun bir martalik/cheklangan taklif havolasi olinadi.
        3. Barcha faol foydalanuvchilarga xabarnoma yuboriladi.
        Qaytaradi: (lesson, invite_link, yuborilgan_soni)
        """
        lesson = await self.lesson_repo.update_status(lesson_id=lesson_id, status="davom_etmoqda")
        if not lesson:
            return None, "", 0

        # Taklif havolasini yaratish (3 soat amal qiladi, cheklangan a'zolar)
        invite_link_str = ""
        if group_id != 0:
            try:
                expire_time = datetime.now(UTC) + timedelta(hours=3)
                invite = await bot.create_chat_invite_link(
                    chat_id=group_id,
                    name=f"Dars: {lesson.title[:20]}",
                    expire_date=expire_time,
                    member_limit=100,
                )
                invite_link_str = invite.invite_link
            except Exception:
                invite_link_str = ""

        # Foydalanuvchilarga bildirishnoma yuborish
        users = await self.user_repo.get_all_users()
        sent_count = 0

        text = (
            "🦅 **Falcon Kibertexnology School**\n\n"
            f"🔴 **Dars boshlandi:** {lesson.title}\n\n"
            "Darsimiz video chat orqali boshlandi. Marhamat, quyidagi tugma orqali darsga kiring!"
        )

        buttons: list[list[InlineKeyboardButton]] = []
        if invite_link_str:
            buttons.append([InlineKeyboardButton(text="🎥 Darsga qo'shilish", url=invite_link_str)])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

        for user in users:
            if not user.is_active:
                continue
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=text,
                    reply_markup=kb,
                    protect_content=True,
                )
                sent_count += 1
            except Exception:
                # Bloklangan yoki xatolik bo'lsa bot to'xtamasin
                pass

        return lesson, invite_link_str, sent_count

    async def end_lesson(self, lesson_id: int) -> Lesson | None:
        """Darsni yakunlash (status='tugagan')."""
        return await self.lesson_repo.update_status(
            lesson_id=lesson_id, status="tugagan", ended_at=datetime.now(UTC)
        )

    async def get_current_or_next_lesson(
        self,
    ) -> tuple[Lesson | None, Lesson | None]:
        """
        (hozirgi_faol_dars, keyingi_rejalashtirilgan_dars) juftligini qaytaradi.
        """
        active = await self.lesson_repo.get_active_lesson()
        scheduled = await self.lesson_repo.get_next_scheduled_lesson()
        return active, scheduled

    async def add_comment(self, lesson_id: int, telegram_id: int, text: str) -> LessonComment:
        """Dars haqida o'quvchi/ota-ona tomonidan izoh qoldirish."""
        return await self.comment_repo.create(
            lesson_id=lesson_id, telegram_id=telegram_id, text=text
        )

    async def get_comments(self, lesson_id: int) -> list[LessonComment]:
        """Dars bo'yicha barcha izohlarni olish."""
        return await self.comment_repo.get_by_lesson_id(lesson_id)

    async def check_group_status(self, bot: Bot, group_id: int) -> dict[str, Any]:
        """
        Botning guruhdagi adminlik huquqi va 'has_protected_content'
        (kontentni saqlash cheklovi) yoqilganligini tekshiradi.
        """
        result: dict[str, Any] = {
            "group_id": group_id,
            "accessible": False,
            "is_admin": False,
            "has_protected_content": False,
            "title": "",
            "message": "",
        }
        if not group_id:
            result["message"] = "LESSON_GROUP_ID sozlanmagan!"
            return result

        try:
            chat = await bot.get_chat(chat_id=group_id)
            result["accessible"] = True
            result["title"] = getattr(chat, "title", "Dars guruhi")
            result["has_protected_content"] = bool(getattr(chat, "has_protected_content", False))

            bot_info = await bot.get_me()
            member = await bot.get_chat_member(chat_id=group_id, user_id=bot_info.id)
            status = getattr(member, "status", "")
            result["is_admin"] = status in ("administrator", "creator")

            if not result["is_admin"]:
                result["message"] = "Bot guruhda administrator emas! Admin huquqini bering."
            elif not result["has_protected_content"]:
                result["message"] = (
                    "Diqqat: Guruhda 'Kontentni saqlashni cheklash' (Restrict saving content) yoqilmagan! "
                    "Iltimos, guruh sozlamalaridan ushbu himoyani yoqing."
                )
            else:
                result["message"] = (
                    "✅ Barcha xavfsizlik sozlamalari to'g'ri! "
                    "Bot admin va kontent himoyasi yoqilgan."
                )
        except Exception as e:
            result["message"] = f"Guruhni tekshirishda xatolik: {e!s}"

        return result
