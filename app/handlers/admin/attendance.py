"""
Falcon Kibertexnology School - Admin: Davomat handlerlari.
Darsni tanlash -> har bir o'quvchi uchun davomat belgilash / qayta belgilash,
'Hammasi keldi' ommaviy tugmasi va eng ko'p dars qoldirganlar hisoboti.
"""

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.lesson_repo import LessonRepository
from app.database.repositories.student_repo import StudentRepository
from app.keyboards.builders import get_attendance_marking_keyboard
from app.keyboards.callbacks import AttendanceCallback
from app.services.attendance import AttendanceService
from app.utils.filters import IsAdminFilter

admin_attendance_router = Router(name="admin_attendance_router")
admin_attendance_router.message.filter(IsAdminFilter())
admin_attendance_router.callback_query.filter(IsAdminFilter())


@admin_attendance_router.message(F.text == "📋 Davomat")
async def handle_attendance_menu(message: Message, session: AsyncSession) -> None:
    """Admin menyusidagi '📋 Davomat' tugmasi bosilganda darslar ro'yxatini ko'rsatish."""
    lesson_repo = LessonRepository(session)
    lessons = await lesson_repo.get_all_lessons(limit=10)

    if not lessons:
        await message.answer(
            "🦅 **Falcon Kibertexnology School**\n\n"
            "⚠️ Hozircha bazada darslar mavjud emas.\n"
            "Davomat belgilash uchun avval '🎥 Video dars' bo'limidan dars yarating.",
            protect_content=True,
        )
        return

    buttons = [
        [
            InlineKeyboardButton(
                text=f"📅 {l.title} ({l.status})",
                callback_data=AttendanceCallback(action="select_lesson", lesson_id=l.id).pack(),
            )
        ]
        for l in lessons
    ]

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        "🦅 **Falcon Kibertexnology School**\n\n"
        "📋 **Davomat bo'limi:**\n"
        "Davomatini belgilamoqchi bo'lgan darsni tanlang:",
        reply_markup=kb,
        protect_content=True,
    )


@admin_attendance_router.callback_query(AttendanceCallback.filter(F.action == "select_lesson"))
async def open_lesson_attendance(
    callback: CallbackQuery,
    callback_data: AttendanceCallback,
    session: AsyncSession,
) -> None:
    """Dars bo'yicha barcha o'quvchilar davomat kartasini chiqarish."""
    lesson_repo = LessonRepository(session)
    student_repo = StudentRepository(session)
    att_service = AttendanceService(session)

    lesson = await lesson_repo.get_by_id(callback_data.lesson_id)
    if not lesson:
        await callback.answer("⚠️ Dars topilmadi!", show_alert=True)
        return

    students = await student_repo.get_all_active()
    existing_records = await att_service.get_lesson_attendance(lesson.id)
    current_statuses = {r.student_id: r.status for r in existing_records}

    kb = get_attendance_marking_keyboard(
        lesson_id=lesson.id,
        students=students,
        current_statuses=current_statuses,
    )

    await callback.message.edit_text(
        f"📋 **Davomat belgilash:**\n"
        f"📌 Dars: **{lesson.title}**\n\n"
        f"O'quvchi holatini o'zgartirish uchun uning ustiga bosing:\n"
        f"(Holatlar: ⚪️ -> ✅ Keldi -> ❌ Kelmadi -> 📄 Sababli)",
        reply_markup=kb,
    )
    await callback.answer()


@admin_attendance_router.callback_query(AttendanceCallback.filter(F.action == "toggle"))
async def toggle_student_attendance(
    callback: CallbackQuery,
    callback_data: AttendanceCallback,
    session: AsyncSession,
) -> None:
    """O'quvchi holatini bittadan aylantirib belgilash."""
    # Sikl: bo'sh/boshqa -> keldi -> kelmadi -> sababli -> keldi
    status_cycle = {
        "": "keldi",
        "keldi": "kelmadi",
        "kelmadi": "sababli",
        "sababli": "keldi",
    }
    next_status = status_cycle.get(callback_data.status, "keldi")

    att_service = AttendanceService(session)
    await att_service.mark_attendance(
        student_id=callback_data.student_id,
        lesson_id=callback_data.lesson_id,
        status=next_status,
    )

    # Klaviaturani qayta yuklaymiz
    student_repo = StudentRepository(session)
    students = await student_repo.get_all_active()
    existing_records = await att_service.get_lesson_attendance(callback_data.lesson_id)
    current_statuses = {r.student_id: r.status for r in existing_records}

    kb = get_attendance_marking_keyboard(
        lesson_id=callback_data.lesson_id,
        students=students,
        current_statuses=current_statuses,
    )
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer(f"Belgilandi: {next_status}")


@admin_attendance_router.callback_query(AttendanceCallback.filter(F.action == "mark_all"))
async def mark_all_students_present(
    callback: CallbackQuery,
    callback_data: AttendanceCallback,
    session: AsyncSession,
) -> None:
    """Barcha o'quvchilarni 'keldi' deb belgilash."""
    student_repo = StudentRepository(session)
    att_service = AttendanceService(session)

    students = await student_repo.get_all_active()
    student_ids = [s.id for s in students]

    await att_service.mark_all_present(lesson_id=callback_data.lesson_id, student_ids=student_ids)

    existing_records = await att_service.get_lesson_attendance(callback_data.lesson_id)
    current_statuses = {r.student_id: r.status for r in existing_records}

    kb = get_attendance_marking_keyboard(
        lesson_id=callback_data.lesson_id,
        students=students,
        current_statuses=current_statuses,
    )
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer("✅ Barcha o'quvchilar 'keldi' deb belgilandi!", show_alert=True)


@admin_attendance_router.callback_query(AttendanceCallback.filter(F.action == "finish"))
async def finish_attendance_marking(callback: CallbackQuery) -> None:
    """Davomatni yakunlash."""
    await callback.message.edit_text(
        "✅ **Davomat muvaffaqiyatli saqlandi!**\n"
        "O'quvchilarning davomat ko'rsatkichlari yangilandi.",
    )
    await callback.answer()
