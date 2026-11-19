"""
Falcon Kibertexnology School - Telegram Bot asosiy kirish nuqtasi (main.py).
Toza arxitektura, xatoliklar global boshqaruvi, loglar (fayl + konsol),
asinxron sessiyalar va fon vazifalari (scheduler).
"""

import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent
from aiohttp import web

import db
from api.routes import setup_routes
from app.config import settings
from app.database.session import init_db
from app.handlers import main_router
from app.middlewares.auth import DatabaseAndAuthMiddleware
from app.middlewares.throttling import ThrottlingMiddleware
from app.utils.scheduler import setup_background_scheduler


def setup_logger() -> None:
    """Konsol va faylga bir vaqtda log yozishni sozlash."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "bot.log")

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Konsol oqimi
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # Fayl oqimi (UTF-8)
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
    except Exception as e:
        sys.stderr.write(f"[WARN] Faylga log yozish sozlanmadi: {e}\n")


logger = logging.getLogger(__name__)


async def global_error_handler(event: ErrorEvent) -> bool:
    """
    Global xatoliklarni ushlash va bot yiqilib ketishini oldini olish.
    Foydalanuvchiga muloyim bildirishnoma beriladi, xato tafsilotlari log faylga yoziladi.
    """
    logger.error(
        f"[GLOBAL ERROR] Xatolik yuz berdi: {event.exception}",
        exc_info=event.exception,
    )

    update = event.update
    target_message = None
    if update.message:
        target_message = update.message
    elif update.callback_query and update.callback_query.message:
        target_message = update.callback_query.message

    if target_message:
        try:
            await target_message.answer(
                "🦅 **Falcon Kibertexnology School**\n\n"
                "⚠️ **Xatolik yuz berdi!**\n"
                "Kechirasiz, tizimda kutilmagan nosozlik yuz berdi. "
                "Iltimos, birozdan so'ng qayta urinib ko'ring yoki ma'muriyatga murojaat qiling.",
                protect_content=True,
            )
        except Exception:
            pass

    return True


async def main() -> None:
    """Botni boshlash va ishga tushirish funksiyasi."""
    setup_logger()
    logger.info("🦅 Falcon Kibertexnology School Telegram Bot ishga tushirilmoqda...")

    if not settings.BOT_TOKEN:
        logger.critical("BOT_TOKEN aniqlanmadi! Iltimos, .env faylini tekshiring.")
        return

    # Ma'lumotlar bazasini initsializatsiya qilish
    try:
        await init_db()
        await db.init_db()
        logger.info("Ma'lumotlar bazasi jadvallari muvaffaqiyatli tekshirildi/yaratildi.")
    except Exception as e:
        logger.error(f"Ma'lumotlar bazasini ishga tushirishda xatolik: {e}")
        return

    # Bot obyekti (barcha xabarlar Markdown va protect_content bilan)
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.MARKDOWN,
            protect_content=True,
        ),
    )

    dp = Dispatcher()

    # Middleware larni ro'yxatdan o'tkazish
    dp.message.middleware(ThrottlingMiddleware(rate_limit=1.0))
    dp.callback_query.middleware(ThrottlingMiddleware(rate_limit=1.0))

    dp.message.middleware(DatabaseAndAuthMiddleware())
    dp.callback_query.middleware(DatabaseAndAuthMiddleware())

    # Routerni ulash
    dp.include_router(main_router)

    # Global xatolik boshqaruvchisi
    dp.errors.register(global_error_handler)

    # Fon rejalashtiruvchisini ishga tushirish (15 daqiqalik eslatmalar va kunlik backup)
    scheduler = setup_background_scheduler(bot)
    scheduler.start()
    logger.info("Fon vazifalari (Scheduler) muvaffaqiyatli ishga tushirildi.")

    # Mini App va API web serverini sozlash
    web_app = web.Application()
    setup_routes(web_app, bot=bot)

    static_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "static"))
    if not os.path.exists(static_dir):
        static_dir = os.path.abspath("static")

    async def index_file_handler(request: web.Request) -> web.FileResponse:
        return web.FileResponse(os.path.join(static_dir, "index.html"))

    web_app.router.add_get("/", index_file_handler)
    web_app.router.add_static("/static/", path=static_dir, name="static")
    web_app.router.add_static("/", path=static_dir, name="root_static")

    web_runner = web.AppRunner(web_app)
    await web_runner.setup()
    web_site = web.TCPSite(web_runner, host="0.0.0.0", port=settings.PORT)
    await web_site.start()
    logger.info(f"📱 Mini App va API serveri http://0.0.0.0:{settings.PORT} da faollashtirildi.")

    try:
        while True:
            try:
                logger.info("Bot polling rejimida tinglashni boshladi.")
                await dp.start_polling(
                    bot,
                    allowed_updates=dp.resolve_used_update_types(),
                    close_bot_session=False,
                )
                break
            except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
                logger.info("Bot to'xtatish signali qabul qilindi.")
                break
            except Exception as e:
                logger.warning(
                    f"Tarmoq yoki ulanishda vaqtinchalik xatolik: {e}. 3 soniyadan so'ng qayta ulaniladi..."
                )
                try:
                    if bot.session and not bot.session.closed:
                        await bot.session.close()
                except Exception:
                    pass
                bot.session = AiohttpSession()
                await asyncio.sleep(3)
    finally:
        try:
            await web_runner.cleanup()
        except Exception:
            pass
        scheduler.shutdown()
        try:
            if bot.session and not bot.session.closed:
                await bot.session.close()
        except Exception:
            pass
        logger.info("Bot faoliyati to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot qo'lda to'xtatildi.")
