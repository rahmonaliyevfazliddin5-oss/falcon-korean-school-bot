"""
Falcon Kibertexnology School - Rejalashtiruvchi vazifalar (Scheduler).
15 daqiqa oldin dars eslatmalari va kunlik zaxira nusxa olish vazifalarini boshqaradi.
"""

import logging
from datetime import UTC, datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.database.models import Lesson, User
from app.database.session import async_session_maker
from app.utils.backup import perform_db_backup

logger = logging.getLogger(__name__)

# Eslatma yuborilgan darslar ID lari (takroran eslatmaslik uchun)
_reminded_lessons: set[int] = set()


async def check_and_send_lesson_reminders(bot: Bot) -> None:
    """Dars boshlanishiga 15 daqiqa qolganida barcha foydalanuvchilarga eslatma yuborish."""
    now = datetime.now(UTC)
    target_window = now + timedelta(minutes=15)

    async with async_session_maker() as session:
        stmt = select(Lesson).where(
            Lesson.status == "rejalashtirilgan",
            Lesson.starts_at > now,
            Lesson.starts_at <= target_window,
        )
        res = await session.execute(stmt)
        upcoming_lessons = list(res.scalars().all())

        if not upcoming_lessons:
            return

        users_res = await session.execute(select(User).where(User.is_active == True))
        users = list(users_res.scalars().all())

        for lesson in upcoming_lessons:
            if lesson.id in _reminded_lessons:
                continue

            _reminded_lessons.add(lesson.id)
            time_str = lesson.starts_at.strftime("%H:%M")
            text = (
                "🦅 **Falcon Kibertexnology School**\n\n"
                f"⏰ **Dars eslatmasi!**\n"
                f"15 daqiqadan so'ng darsimiz boshlanadi!\n\n"
                f"📌 **Mavzu:** {lesson.title}\n"
                f"🕐 **Boshlanish vaqti:** {time_str}\n\n"
                "Iltimos, darsga o'z vaqtida tayyor bo'ling!"
            )

            for u in users:
                try:
                    await bot.send_message(
                        chat_id=u.telegram_id,
                        text=text,
                        protect_content=True,
                    )
                except Exception:
                    pass

            logger.info(
                f"[SCHEDULER REMINDER] Dars #{lesson.id} '{lesson.title}' uchun eslatmalar yuborildi."
            )


def setup_background_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Asinxron schedulerni sozlash va ishga tushirish."""
    scheduler = AsyncIOScheduler()

    # Har 1 daqiqada yaqinlashib kelayotgan darslarni tekshirish
    scheduler.add_job(
        check_and_send_lesson_reminders,
        "interval",
        minutes=1,
        args=[bot],
        id="lesson_reminder_job",
        replace_existing=True,
    )

    # Kunlik soat 03:00 da avtomatik zaxira nusxa olish
    scheduler.add_job(
        perform_db_backup,
        "cron",
        hour=3,
        minute=0,
        id="daily_db_backup_job",
        replace_existing=True,
    )

    return scheduler
