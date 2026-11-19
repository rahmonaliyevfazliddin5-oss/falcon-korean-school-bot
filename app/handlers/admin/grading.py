"""
Falcon Kibertexnology School - Admin: Baholash handlerlari.
O'quvchini tanlash -> 1-5 baho tugmalari -> ixtiyoriy izoh -> saqlash.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.student_repo import StudentRepository
from app.keyboards.builders import get_grading_keyboard, get_student_card_keyboard
from app.keyboards.callbacks import GradeCallback, StudentActionCallback
from app.services.grading import GradingService
from app.states import GradingStates
from app.utils.filters import IsAdminFilter

admin_grading_router = Router(name="admin_grading_router")
admin_grading_router.message.filter(IsAdminFilter())
admin_grading_router.callback_query.filter(IsAdminFilter())


@admin_grading_router.message(F.text == "⭐ Baholash")
async def handle_grading_menu(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Admin menyusidagi '⭐ Baholash' tugmasi bosilganda o'quvchilar ro'yxatini ko'rsatish."""
    await state.clear()
    student_repo = StudentRepository(session)
    students, _ = await student_repo.get_active_students(offset=0, limit=20)

    if not students:
        await message.answer(
            "⚠️ Hozircha baholash uchun faol o'quvchilar yo'q.",
            protect_content=True,
        )
        return

    buttons = [
        [
            InlineKeyboardButton(
                text=f"⭐️ {st.full_name} ({st.group_name})",
                callback_data=StudentActionCallback(action="grade", student_id=st.id).pack(),
            )
        ]
        for st in students
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        "🦅 **Falcon Kibertexnology School**\n\n"
        "⭐ **Baholash bo'limi:**\n"
        "Baho qo'yish uchun o'quvchini tanlang:",
        reply_markup=kb,
        protect_content=True,
    )


@admin_grading_router.callback_query(StudentActionCallback.filter(F.action == "grade"))
async def prompt_grade_selection(
    callback: CallbackQuery,
    callback_data: StudentActionCallback,
    session: AsyncSession,
) -> None:
    """1 dan 5 gacha baho qo'yish tugmalarini chiqarish."""
    student_repo = StudentRepository(session)
    student = await student_repo.get_by_id(callback_data.student_id)
    if not student:
        await callback.answer("⚠️ O'quvchi topilmadi!", show_alert=True)
        return

    kb = get_grading_keyboard(student.id)
    await callback.message.edit_text(
        f"⭐️ **O'quvchini baholash:**\n\n"
        f"👤 {student.full_name} ({student.group_name})\n"
        f"Qo'ymoqchi bo'lgan bahoyingizni tanlang:",
        reply_markup=kb,
    )
    await callback.answer()


@admin_grading_router.callback_query(GradeCallback.filter(F.action == "score"))
async def handle_score_choice(
    callback: CallbackQuery,
    callback_data: GradeCallback,
    state: FSMContext,
) -> None:
    """Baho tanlangach, ixtiyoriy izoh so'rash."""
    await state.set_state(GradingStates.waiting_for_comment)
    await state.update_data(student_id=callback_data.student_id, score=callback_data.score)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏩ O'tkazib yuborish (Izohsiz)",
                    callback_data="skip_grade_comment",
                )
            ]
        ]
    )
    await callback.message.edit_text(
        f"⭐️ **Tanlangan baho: {callback_data.score} ball**\n\n"
        "Ushbu baho uchun izoh kiritasizmi?\n"
        "(Masalan: *Lug'at yodlash bo'yicha mustaqil ish*)\n"
        "Yoki 'O'tkazib yuborish' tugmasini bosing:",
        reply_markup=kb,
    )
    await callback.answer()


@admin_grading_router.callback_query(
    GradingStates.waiting_for_comment, F.data == "skip_grade_comment"
)
async def save_grade_without_comment(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Izohsiz bahoni saqlash."""
    data = await state.get_data()
    await state.clear()

    grading_service = GradingService(session)
    grade = await grading_service.add_grade(
        student_id=data["student_id"],
        score=data["score"],
        created_by=callback.from_user.id,
        comment=None,
    )
    new_avg = await grading_service.get_student_average(grade.student_id)

    await callback.message.edit_text(
        f"✅ **Baho muvaffaqiyatli saqlandi!**\n\n"
        f"⭐️ Ball: {grade.score}\n"
        f"📈 O'quvchining yangi o'rtacha bali: **{new_avg:.2f}**",
        reply_markup=get_student_card_keyboard(grade.student_id),
    )
    await callback.answer()


@admin_grading_router.message(GradingStates.waiting_for_comment)
async def save_grade_with_comment(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Izoh bilan birga bahoni saqlash."""
    comment_text = message.text.strip() if message.text else ""
    data = await state.get_data()
    await state.clear()

    grading_service = GradingService(session)
    grade = await grading_service.add_grade(
        student_id=data["student_id"],
        score=data["score"],
        created_by=message.from_user.id if message.from_user else 0,
        comment=comment_text,
    )
    new_avg = await grading_service.get_student_average(grade.student_id)

    await message.answer(
        f"✅ **Baho va izoh muvaffaqiyatli saqlandi!**\n\n"
        f"⭐️ Ball: {grade.score}\n"
        f"📝 Izoh: {grade.comment}\n"
        f"📈 O'quvchining yangi o'rtacha bali: **{new_avg:.2f}**",
        reply_markup=get_student_card_keyboard(grade.student_id),
        protect_content=True,
    )
