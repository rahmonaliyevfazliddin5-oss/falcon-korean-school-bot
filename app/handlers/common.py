"""
Falcon Kibertexnology School - Umumiy komandalar handlerlari (/start, /admin, /export, /checkgroup).
Barcha xabarlar 'Falcon Kibertexnology School' brendi va protect_content=True bilan jo'natiladi.
"""

import os

from aiogram import Bot, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import User
from app.database.repositories.school_info_repo import SchoolInfoRepository
from app.database.repositories.user_repo import UserRepository
from app.keyboards.builders import get_main_menu_keyboard
from app.services.lessons import LessonService
from app.states import AdminLoginStates
from app.utils.excel_export import generate_school_excel_report
from app.utils.security import admin_security

common_router = Router(name="common_router")


@common_router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    current_user: User,
    session: AsyncSession,
) -> None:
    """
    /start komandasi.
    Foydalanuvchi bazada bo'lmasa avtomatik 'parent' roliga o'tadi.
    Asosiy menyu rolga qarab chiqariladi.
    """
    await state.clear()
    role = current_user.role if current_user else "user"
    kb = get_main_menu_keyboard(role=role)

    school_repo = SchoolInfoRepository(session)
    about_text = await school_repo.get_info("about_school")

    welcome_text = (
        "🦅 **Falcon Kibertexnology School** — Koreys tili botiga xush kelibsiz!\n\n"
        f"Hurmatli **{message.from_user.full_name if message.from_user else 'foydalanuvchi'}**!\n"
        "Ushbu bot orqali koreys tili darslaridagi davomat, baholar, "
        "o'quvchilar reytingi va video darslarni kuzatib borishingiz mumkin.\n\n"
        f"{about_text}\n\n"
        "👇 Kerakli bo'limni tanlash uchun pastdagi menyudan foydalaning:"
    )

    await message.answer(
        text=welcome_text,
        reply_markup=kb,
        protect_content=True,
    )


@common_router.message(Command("admin"))
async def cmd_admin(
    message: Message,
    state: FSMContext,
    current_user: User,
) -> None:
    """
    /admin komandasi.
    Agar foydalanuvchi allaqachon admin bo'lsa, to'g'ridan-to'g'ri admin panelni ochadi.
    Aks holda, Admin ID raqamini so'raydi (FSM orqali).
    """
    # Tekshirish: agar foydalanuvchi allaqachon admin bo'lsa
    if current_user and current_user.role == "admin":
        kb = get_main_menu_keyboard(role="admin")
        await message.answer(
            "🦅 **Falcon Kibertexnology School**\n\n"
            "👋 Siz allaqachon administrator sifatida tizimdasiz!\n"
            "Admin paneli boshqaruv menyusi faol.",
            reply_markup=kb,
            protect_content=True,
        )
        return

    # Foydalanuvchi bloklanganligini tekshirish
    is_blk, remaining = admin_security.is_blocked(message.from_user.id)
    if is_blk:
        await message.answer(
            f"🚫 **Xavfsizlik cheklovi:** Siz 10 daqiqaga bloklangansiz.\n"
            f"Qolgan vaqt: {remaining // 60} daqiqa.",
            protect_content=True,
        )
        return

    await state.set_state(AdminLoginStates.waiting_for_admin_id)
    await message.answer(
        "🦅 **Falcon Kibertexnology School**\n\n"
        "🔐 **Administrator tizimiga kirish**\n"
        "Iltimos, tasdiqlash uchun **Admin panel ID** raqamini kiriting:",
        protect_content=True,
    )


@common_router.message(AdminLoginStates.waiting_for_admin_id)
async def process_admin_id_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """
    Admin ID tekshiruvi:
    1. Raqam ekanligi validatsiya qilinadi.
    2. entered_id '07070707' (o'zgarmas doimiy panel ID) yoki haqiqiy Telegram ID ga mosligi tekshiriladi.
    3. 3 ta xatoda 10 daqiqalik blok qo'yiladi.
    """
    entered_text = message.text.strip() if message.text else ""
    if not entered_text or not entered_text.isdigit():
        await message.answer(
            "⚠️ Iltimos, faqat butun son ko'rinishidagi Admin ID kiriting:",
            protect_content=True,
        )
        return

    actual_id = message.from_user.id if message.from_user else 0

    success, reply_text = admin_security.verify_login(
        actual_telegram_id=actual_id, entered_id=entered_text
    )

    if not success:
        await message.answer(reply_text, protect_content=True)
        # Agar blok holatiga tushsa FSM holatini tozalaymiz
        is_blk, _ = admin_security.is_blocked(actual_id)
        if is_blk:
            await state.clear()
        return

    # Kirish muvaffaqiyatli: foydalanuvchi rolini 'admin' qilamiz
    user_repo = UserRepository(session)
    await user_repo.set_role(telegram_id=actual_id, role="admin")
    await state.clear()

    admin_kb = get_main_menu_keyboard(role="admin")
    await message.answer(
        "🦅 **Falcon Kibertexnology School**\n\n"
        "🎉 **Tabriklaymiz! Siz administrator sifatida muvaffaqiyatli tizimga kirdingiz!**\n\n"
        "Quyidagi tugmalar orqali maktab jarayonlarini to'liq boshqarishingiz mumkin:\n"
        "👥 O'quvchilar | ⭐ Baholash | 📋 Davomat | 📝 Izohlar\n"
        "🎥 Video dars | 🏆 Reyting | 📊 Statistika",
        reply_markup=admin_kb,
        protect_content=True,
    )


@common_router.message(Command("export"))
async def cmd_export(
    message: Message,
    current_user: User,
    session: AsyncSession,
) -> None:
    """
    /export komandasi (Faqat admin uchun).
    O'quvchilar, baholar va davomat ma'lumotlarini Excel formatida yuboradi.
    """
    if not current_user or current_user.role != "admin":
        await message.answer(
            "⛔️ Bu buyruqdan faqat administratorlar foydalana oladi!",
            protect_content=True,
        )
        return

    await message.answer(
        "📊 Ma'lumotlar to'planmoqda va Excel fayl shakllantirilmoqda, kuting...",
        protect_content=True,
    )

    try:
        filepath = await generate_school_excel_report(session)
        doc = FSInputFile(filepath, filename=os.path.basename(filepath))
        await message.answer_document(
            document=doc,
            caption=(
                "🦅 **Falcon Kibertexnology School**\n\n"
                "📁 Barcha o'quvchilar, baholar va davomat bo'yicha to'liq hisobot."
            ),
            protect_content=True,
        )
    except Exception as e:
        await message.answer(
            f"❌ Excel eksport qilishda xatolik yuz berdi: {e!s}",
            protect_content=True,
        )


@common_router.message(Command("checkgroup"))
async def cmd_checkgroup(
    message: Message,
    bot: Bot,
    current_user: User,
    session: AsyncSession,
) -> None:
    """
    /checkgroup komandasi (Faqat admin uchun).
    Bot dars guruhida admin ekanligini va Restrict saving content yoqilganligini tekshiradi.
    """
    if not current_user or current_user.role != "admin":
        await message.answer(
            "⛔️ Bu buyruqdan faqat administratorlar foydalana oladi!",
            protect_content=True,
        )
        return

    lesson_service = LessonService(session)
    status_info = await lesson_service.check_group_status(
        bot=bot, group_id=settings.lesson_group_id_int
    )

    is_admin_str = "✅ Ha" if status_info["is_admin"] else "❌ Yo'q"
    is_protected_str = "✅ Yoqilgan" if status_info["has_protected_content"] else "❌ O'chirilgan"
    group_title = status_info.get("title", "Noma'lum")

    status_text = (
        "🦅 **Falcon Kibertexnology School**\n\n"
        "🔒 **Guruh xavfsizligi va Bot huquqlari tekshiruvi:**\n\n"
        f"📌 Guruh ID: `{status_info['group_id']}`\n"
        f"🏷 Guruh nomi: **{group_title}**\n"
        f"🤖 Bot Administrator: {is_admin_str}\n"
        f"🛡 Kontentni himoyalash (Restrict saving content): {is_protected_str}\n\n"
        f"📝 Xulosa: {status_info['message']}"
    )

    await message.answer(status_text, protect_content=True)
