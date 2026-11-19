"""
Falcon Kibertexnology School - Admin: Video darslarni boshqarish handlerlari.
Dars yaratish, boshlash (havola yaratish va broadcast), tugatish va davomatga yo'naltirish.
"""

from datetime import UTC, datetime

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.repositories.lesson_repo import LessonRepository
from app.keyboards.builders import get_lesson_control_keyboard
from app.keyboards.callbacks import AttendanceCallback, LessonControlCallback
from app.services.lessons import LessonService
from app.states import LessonAddStates
from app.utils.filters import IsAdminFilter

admin_lessons_router = Router(name="admin_lessons_router")
admin_lessons_router.message.filter(IsAdminFilter())
admin_lessons_router.callback_query.filter(IsAdminFilter())


@admin_lessons_router.message(F.text == "🎥 Video dars")
async def handle_video_lessons_menu(message: Message, session: AsyncSession) -> None:
    """Admin menyusidagi '🎥 Video dars' boshqaruvi."""
    lesson_service = LessonService(session)
    active, scheduled = await lesson_service.get_current_or_next_lesson()

    text = "🦅 **Falcon Kibertexnology School**\n\n🎥 **Video darslar boshqaruvi:**\n\n"

    if active:
        text += (
            f"🔴 **HOZIR DAVOM ETMOQDA:**\n"
            f"📌 Mavzu: **{active.title}**\n"
            f"🕐 Boshlangan vaqti: {active.starts_at.strftime('%H:%M')}\n\n"
            "Dars tugagach '⏹ Darsni tugatish' tugmasini bosing."
        )
    else:
        text += "⚪️ Hozirda faol dars mavjud emas.\n\n"
        if scheduled:
            text += (
                f"📅 **Keyingi rejalashtirilgan dars:**\n"
                f"📌 Mavzu: **{scheduled.title}**\n"
                f"🕐 Vaqti: {scheduled.starts_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            )

    kb = get_lesson_control_keyboard(active_lesson=active)
    await message.answer(text, reply_markup=kb, protect_content=True)


# ==================== DARS YARATISH (FSM) ====================
@admin_lessons_router.callback_query(LessonControlCallback.filter(F.action == "create"))
async def start_lesson_creation(callback: CallbackQuery, state: FSMContext) -> None:
    """Dars mavzusini so'rash."""
    await state.set_state(LessonAddStates.waiting_for_title)
    await callback.message.answer(
        "📝 **Yangi dars yaratish (1/2):**\n\n"
        "Iltimos, dars mavzusini kiriting:\n"
        "(Masalan: *Koreys tili 10-dars: Fe'llarning o'tgan zamoni*)",
        protect_content=True,
    )
    await callback.answer()


@admin_lessons_router.message(LessonAddStates.waiting_for_title)
async def process_lesson_title(message: Message, state: FSMContext) -> None:
    """Dars mavzusini qabul qilish va vaqtini so'rash."""
    title = message.text.strip() if message.text else ""
    if len(title) < 3:
        await message.answer("⚠️ Dars mavzusi juda qisqa. Qaytadan kiriting:")
        return

    await state.update_data(title=title)
    await state.set_state(LessonAddStates.waiting_for_time)

    await message.answer(
        "🕐 **Dars boshlanish vaqtini kiriting (2/2):**\n\n"
        "Format: `YYYY-MM-DD HH:MM` (Masalan: `2026-11-15 18:30`)\n"
        "Yoki hozir boshlanadigan bo'lsa `hozir` deb yozing:",
        protect_content=True,
    )


@admin_lessons_router.message(LessonAddStates.waiting_for_time)
async def process_lesson_time(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Dars vaqtini qabul qilish va saqlash."""
    time_text = message.text.strip().lower() if message.text else ""
    starts_at = datetime.now(UTC)

    if time_text != "hozir":
        try:
            parsed = datetime.strptime(time_text, "%Y-%m-%d %H:%M")
            starts_at = parsed.replace(tzinfo=UTC)
        except ValueError:
            await message.answer(
                "⚠️ Sana formati noto'g'ri! Iltimos `YYYY-MM-DD HH:MM` ko'rinishida kiriting "
                "yoki `hozir` deb yozing:"
            )
            return

    data = await state.get_data()
    title = data["title"]
    await state.clear()

    lesson_service = LessonService(session)
    lesson = await lesson_service.create_lesson(
        title=title,
        starts_at=starts_at,
        created_by=message.from_user.id if message.from_user else 0,
    )

    await message.answer(
        f"✅ **Yangi dars muvaffaqiyatli rejalashtirildi!**\n\n"
        f"📌 Mavzu: **{lesson.title}**\n"
        f"🕐 Vaqti: {lesson.starts_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        "Dars vaqti yetganda '▶️ Darsni boshlash' tugmasi orqali xabarnoma tarqatishingiz mumkin.",
        protect_content=True,
    )


# ==================== DARSNI BOSHLASH ====================
@admin_lessons_router.callback_query(LessonControlCallback.filter(F.action == "start_choose"))
async def choose_lesson_to_start(callback: CallbackQuery, session: AsyncSession) -> None:
    """Boshlash uchun rejalashtirilgan darsni tanlash."""
    lesson_repo = LessonRepository(session)
    lessons = await lesson_repo.get_all_lessons(limit=10)
    scheduled = [l for l in lessons if l.status == "rejalashtirilgan"]

    if not scheduled:
        await callback.message.answer(
            "⚠️ Boshlash uchun rejalashtirilgan dars yo'q. Avval '➕ Yangi dars yaratish' tugmasini bosing.",
            protect_content=True,
        )
        await callback.answer()
        return

    buttons = [
        [
            InlineKeyboardButton(
                text=f"▶️ {l.title}",
                callback_data=LessonControlCallback(action="do_start", lesson_id=l.id).pack(),
            )
        ]
        for l in scheduled
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await callback.message.edit_text("Qaysi darsni boshlamoqchisiz? Tanlang:", reply_markup=kb)
    await callback.answer()


@admin_lessons_router.callback_query(LessonControlCallback.filter(F.action == "do_start"))
async def execute_start_lesson(
    callback: CallbackQuery,
    callback_data: LessonControlCallback,
    bot: Bot,
    session: AsyncSession,
) -> None:
    """Darsni faollashtirish, havolani olish va bildirishnoma tarqatish."""
    lesson_service = LessonService(session)

    await callback.message.edit_text("⏳ Dars boshlanmoqda va bildirishnomalar yuborilmoqda...")

    lesson, link, sent_count = await lesson_service.start_lesson(
        bot=bot,
        lesson_id=callback_data.lesson_id,
        group_id=settings.lesson_group_id_int,
    )

    if not lesson:
        await callback.message.edit_text("⚠️ Darsni boshlashda xatolik yuz berdi!")
        return

    link_info = f"\n🔗 Havola: {link}" if link else "\n(Guruh havolasi sozlanmagan)"

    await callback.message.edit_text(
        f"🔴 **Dars muvaffaqiyatli boshlandi!**\n\n"
        f"📌 Mavzu: **{lesson.title}**\n"
        f"👥 Yuborilgan xabarnomalar soni: **{sent_count} ta**{link_info}\n\n"
        "Dars tugagach '⏹ Darsni tugatish' tugmasini bosing.",
        reply_markup=get_lesson_control_keyboard(active_lesson=lesson),
    )
    await callback.answer()


# ==================== DARSNI TUGATISH ====================
@admin_lessons_router.callback_query(LessonControlCallback.filter(F.action == "end"))
async def execute_end_lesson(
    callback: CallbackQuery,
    callback_data: LessonControlCallback,
    session: AsyncSession,
) -> None:
    """Darsni tugatish va davomat belgilashga taklif qilish."""
    lesson_service = LessonService(session)
    lesson = await lesson_service.end_lesson(callback_data.lesson_id)

    if not lesson:
        await callback.answer("⚠️ Dars topilmadi!", show_alert=True)
        return

    # Davomat belgilash tugmasi bilan taklif
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Hozir davomat belgilash",
                    callback_data=AttendanceCallback(
                        action="select_lesson", lesson_id=lesson.id
                    ).pack(),
                )
            ]
        ]
    )

    await callback.message.edit_text(
        f"⏹ **Dars yakunlandi!**\n\n"
        f"📌 Mavzu: **{lesson.title}**\n"
        f"🕐 Yakunlangan vaqti: {lesson.ended_at.strftime('%H:%M') if lesson.ended_at else ''}\n\n"
        "O'quvchilar darsda qay darajada qatnashganligini belgilash uchun "
        "quyidagi tugma orqali davomatni to'ldiring:",
        reply_markup=kb,
    )
    await callback.answer()


# ==================== DARS IZOHLARINI KO'RISH ====================
@admin_lessons_router.callback_query(
    LessonControlCallback.filter(F.action.in_({"view_comments", "view_recent_comments"}))
)
async def view_lesson_comments_admin(
    callback: CallbackQuery,
    callback_data: LessonControlCallback,
    session: AsyncSession,
) -> None:
    """Admin uchun dars izohlarini chiqarish."""
    lesson_service = LessonService(session)
    lesson_id = callback_data.lesson_id

    if not lesson_id:
        lesson_repo = LessonRepository(session)
        lessons = await lesson_repo.get_all_lessons(limit=1)
        if lessons:
            lesson_id = lessons[0].id

    if not lesson_id:
        if callback.message:
            await callback.message.answer(
                "⚠️ Hozircha bazada darslar mavjud emas.", protect_content=True
            )
        await callback.answer()
        return

    comments = await lesson_service.get_comments(lesson_id)
    text = f"🦅 **Falcon Kibertexnology School**\n\n💬 **Dars izohlari (Lesson #{lesson_id}):**\n\n"

    if not comments:
        text += "Ushbu dars uchun foydalanuvchilar tomonidan izoh qoldirilmagan."
    else:
        for idx, c in enumerate(comments, start=1):
            date_str = c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else ""
            text += f'**{idx}.** "{c.text}"\n   └ 👤 ID: `{c.telegram_id}` | 📅 {date_str}\n\n'

    if callback.message:
        await callback.message.answer(text, protect_content=True)
    await callback.answer()
