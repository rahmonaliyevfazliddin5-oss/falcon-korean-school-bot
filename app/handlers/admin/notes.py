"""
Falcon Kibertexnology School - Admin: O'qituvchi izohlari handlerlari.
O'quvchiga izoh qo'shish, ko'rish, tahrirlash va o'chirish.
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

from app.database.repositories.note_repo import TeacherNoteRepository
from app.database.repositories.student_repo import StudentRepository
from app.keyboards.builders import get_notes_keyboard, get_student_card_keyboard
from app.keyboards.callbacks import NoteActionCallback, StudentActionCallback
from app.states import NoteStates
from app.utils.filters import IsAdminFilter

admin_notes_router = Router(name="admin_notes_router")
admin_notes_router.message.filter(IsAdminFilter())
admin_notes_router.callback_query.filter(IsAdminFilter())


@admin_notes_router.message(F.text == "📝 Izohlar")
async def handle_notes_menu(message: Message, session: AsyncSession) -> None:
    """Admin menyusidagi '📝 Izohlar' tugmasi."""
    student_repo = StudentRepository(session)
    students, _ = await student_repo.get_active_students(offset=0, limit=20)

    if not students:
        await message.answer("⚠️ Hozircha faol o'quvchilar yo'q.", protect_content=True)
        return

    buttons = [
        [
            InlineKeyboardButton(
                text=f"📝 {st.full_name} ({st.group_name})",
                callback_data=StudentActionCallback(action="note", student_id=st.id).pack(),
            )
        ]
        for st in students
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        "🦅 **Falcon Kibertexnology School**\n\n"
        "📝 **O'qituvchi izohlari bo'limi:**\n"
        "Izoh yozish yoki ko'rish uchun o'quvchini tanlang:",
        reply_markup=kb,
        protect_content=True,
    )


@admin_notes_router.callback_query(StudentActionCallback.filter(F.action == "note"))
async def open_student_notes(
    callback: CallbackQuery,
    callback_data: StudentActionCallback,
    session: AsyncSession,
) -> None:
    """O'quvchining izohlari ro'yxatini chiqarish."""
    student_repo = StudentRepository(session)
    note_repo = TeacherNoteRepository(session)

    student = await student_repo.get_by_id(callback_data.student_id)
    if not student:
        await callback.answer("⚠️ O'quvchi topilmadi!", show_alert=True)
        return

    notes = await note_repo.get_by_student_id(student.id, limit=10)
    kb = get_notes_keyboard(student.id, notes)

    header = (
        f"🦅 **Falcon Kibertexnology School**\n\n📝 **O'quvchiga izohlar:** {student.full_name}\n\n"
    )

    if not notes:
        header += "Hozircha hech qanday izoh qoldirilmagan."
    else:
        for idx, n in enumerate(notes, start=1):
            date_str = n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else ""
            header += (
                f'**{idx}.** "{n.text}"\n'
                f"   └ 📅 Sana: {date_str} | O'qituvchi ID: `{n.created_by}`\n\n"
            )

    await callback.message.edit_text(header, reply_markup=kb)
    await callback.answer()


@admin_notes_router.callback_query(NoteActionCallback.filter(F.action == "add"))
async def prompt_add_note(
    callback: CallbackQuery,
    callback_data: NoteActionCallback,
    state: FSMContext,
) -> None:
    """Yangi izoh matnini kiritish so'rovi."""
    await state.set_state(NoteStates.waiting_for_text)
    await state.update_data(student_id=callback_data.student_id)

    await callback.message.answer(
        "📝 **O'quvchi uchun izoh matnini kiriting:**\n"
        "(Masalan: *Fazliddin hulqi yaxshi, darslarni qoldirmay qatnashadi.*)",
        protect_content=True,
    )
    await callback.answer()


@admin_notes_router.message(NoteStates.waiting_for_text)
async def save_new_note(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Yangi izohni saqlash."""
    text = message.text.strip() if message.text else ""
    if len(text) < 3 or len(text) > 1000:
        await message.answer(
            "⚠️ Izoh matni 3 dan 1000 belgiga qadar bo'lishi kerak. Qaytadan kiriting:"
        )
        return

    data = await state.get_data()
    student_id = data["student_id"]
    await state.clear()

    note_repo = TeacherNoteRepository(session)
    await note_repo.create(
        student_id=student_id,
        text=text,
        created_by=message.from_user.id if message.from_user else 0,
    )

    await message.answer(
        "✅ **Izoh muvaffaqiyatli saqlandi!**",
        reply_markup=get_student_card_keyboard(student_id),
        protect_content=True,
    )


@admin_notes_router.callback_query(NoteActionCallback.filter(F.action == "edit"))
async def prompt_edit_note(
    callback: CallbackQuery,
    callback_data: NoteActionCallback,
    state: FSMContext,
) -> None:
    """Izohni tahrirlash so'rovi."""
    await state.set_state(NoteStates.editing_text)
    await state.update_data(note_id=callback_data.note_id, student_id=callback_data.student_id)

    await callback.message.answer(
        "✏️ **Izohning yangi matnini kiriting:**",
        protect_content=True,
    )
    await callback.answer()


@admin_notes_router.message(NoteStates.editing_text)
async def save_edited_note(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Tahrirlangan izohni saqlash."""
    text = message.text.strip() if message.text else ""
    if len(text) < 3:
        await message.answer("⚠️ Yangi matn juda qisqa. Qaytadan kiriting:")
        return

    data = await state.get_data()
    note_id = data["note_id"]
    student_id = data["student_id"]
    await state.clear()

    note_repo = TeacherNoteRepository(session)
    await note_repo.update(note_id=note_id, text=text)

    await message.answer(
        "✅ **Izoh muvaffaqiyatli tahrirlandi!**",
        reply_markup=get_student_card_keyboard(student_id),
        protect_content=True,
    )


@admin_notes_router.callback_query(NoteActionCallback.filter(F.action == "delete"))
async def delete_note(
    callback: CallbackQuery,
    callback_data: NoteActionCallback,
    session: AsyncSession,
) -> None:
    """Izohni o'chirish."""
    note_repo = TeacherNoteRepository(session)
    await note_repo.delete(callback_data.note_id)

    await callback.answer("✅ Izoh o'chirildi!", show_alert=True)
    # Ro'yxatni yangilaymiz
    notes = await note_repo.get_by_student_id(callback_data.student_id)
    kb = get_notes_keyboard(callback_data.student_id, notes)
    await callback.message.edit_reply_markup(reply_markup=kb)
