"""
Falcon Kibertexnology School - Admin: O'quvchilar bo'limi handlerlari.
O'quvchi qo'shish (FSM), qidirish, sahifalash, kartochka ko'rish,
ota-ona ID bog'lash va soft delete amallari.
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

from app.database.repositories.attendance_repo import AttendanceRepository
from app.database.repositories.grade_repo import GradeRepository
from app.database.repositories.student_repo import StudentRepository
from app.keyboards.builders import (
    get_delete_confirm_keyboard,
    get_student_card_keyboard,
    get_students_pagination_keyboard,
)
from app.keyboards.callbacks import (
    NavCallback,
    StudentActionCallback,
)
from app.states import (
    StudentAddStates,
    StudentLinkParentStates,
    StudentSearchStates,
)
from app.utils.filters import IsAdminFilter

admin_students_router = Router(name="admin_students_router")
admin_students_router.message.filter(IsAdminFilter())
admin_students_router.callback_query.filter(IsAdminFilter())


async def show_students_page(
    target_event: Message | CallbackQuery,
    session: AsyncSession,
    page: int = 0,
    search: str | None = None,
) -> None:
    """O'quvchilar ro'yxatini sahifa bo'yicha ko'rsatish yordamchi funksiyasi."""
    student_repo = StudentRepository(session)
    students, total_count = await student_repo.get_active_students(
        offset=page * 8, limit=8, search_query=search
    )

    kb = get_students_pagination_keyboard(
        students=students,
        page=page,
        total_count=total_count,
        page_size=8,
        search=search,
    )

    title = "👥 **Falcon Kibertexnology School — O'quvchilar ro'yxati**\n\n"
    if search:
        title += f"🔍 Qidiruv natijalari: '{search}' ({total_count} ta topildi)\n\n"
    else:
        title += f"Jami faol o'quvchilar soni: **{total_count} ta**\n\n"

    title += "O'quvchi kartochkasini ochish uchun uning ustiga bosing:"

    if isinstance(target_event, CallbackQuery):
        await target_event.message.edit_text(title, reply_markup=kb)
        await target_event.answer()
    else:
        await target_event.answer(title, reply_markup=kb, protect_content=True)


@admin_students_router.message(F.text == "👥 O'quvchilar")
async def handle_students_menu_click(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Admin menyusidagi '👥 O'quvchilar' tugmasi bosilganda."""
    await state.clear()
    await show_students_page(message, session, page=0)


@admin_students_router.callback_query(NavCallback.filter(F.target == "students"))
async def handle_students_nav_callback(
    callback: CallbackQuery,
    callback_data: NavCallback,
    session: AsyncSession,
) -> None:
    """Sahifalash tugmalari (◀️ ▶️)."""
    await show_students_page(
        callback, session, page=callback_data.page, search=callback_data.search
    )


# ==================== QIDIRUV (SEARCH) ====================
@admin_students_router.callback_query(NavCallback.filter(F.target == "search_student"))
async def start_student_search(callback: CallbackQuery, state: FSMContext) -> None:
    """Qidirish boshlash."""
    await state.set_state(StudentSearchStates.waiting_for_query)
    await callback.message.answer(
        "🔍 **O'quvchini qidirish:**\nO'quvchining ism yoki familiyasini kiriting:",
        protect_content=True,
    )
    await callback.answer()


@admin_students_router.message(StudentSearchStates.waiting_for_query)
async def process_student_search_query(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Qidiruv so'zini qabul qilish va natijani chiqarish."""
    query = message.text.strip() if message.text else ""
    if not query or len(query) < 2:
        await message.answer("⚠️ Qidiruv uchun kamida 2 ta harf kiriting:")
        return

    await state.clear()
    await show_students_page(message, session, page=0, search=query)


# ==================== O'QUVCHI QO'SHISH (ADD STUDENT FSM) ====================
@admin_students_router.callback_query(NavCallback.filter(F.target == "add_student"))
async def start_add_student(callback: CallbackQuery, state: FSMContext) -> None:
    """O'quvchi qo'shish FSM jarayonini boshlash."""
    await state.set_state(StudentAddStates.waiting_for_name)
    await callback.message.answer(
        "➕ **Yangi o'quvchi qo'shish (1/4):**\n\n"
        "Iltimos, o'quvchining **Ism va Familiyasini** kiriting (masalan: *Ali Valiyev*):",
        protect_content=True,
    )
    await callback.answer()


@admin_students_router.message(StudentAddStates.waiting_for_name)
async def process_student_name(message: Message, state: FSMContext) -> None:
    """Ismni validatsiya qilish."""
    name = message.text.strip() if message.text else ""
    if len(name) < 3 or len(name) > 100:
        await message.answer(
            "⚠️ Ism-familiya uzunligi 3 va 100 belgi oralig'ida bo'lishi kerak. Qaytadan kiriting:"
        )
        return

    await state.update_data(full_name=name)
    await state.set_state(StudentAddStates.waiting_for_level)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Boshlang'ich", callback_data="level:boshlang'ich"),
                InlineKeyboardButton(text="O'rta", callback_data="level:o'rta"),
                InlineKeyboardButton(text="Yuqori", callback_data="level:yuqori"),
            ]
        ]
    )
    await message.answer(
        "➕ **O'quvchi darajasini tanlang (2/4):**",
        reply_markup=kb,
        protect_content=True,
    )


@admin_students_router.callback_query(
    StudentAddStates.waiting_for_level, F.data.startswith("level:")
)
async def process_student_level_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Darajani saqlash va guruh nomini so'rash."""
    level = callback.data.split(":")[1]
    await state.update_data(level=level)
    await state.set_state(StudentAddStates.waiting_for_group)
    await callback.message.answer(
        "➕ **Guruh nomini kiriting (3/4):**\nMasalan: *KOR-101* yoki *Topik-1*:",
        protect_content=True,
    )
    await callback.answer()


@admin_students_router.message(StudentAddStates.waiting_for_group)
async def process_student_group(message: Message, state: FSMContext) -> None:
    """Guruh nomini validatsiya qilish."""
    group = message.text.strip() if message.text else ""
    if not group or len(group) > 50:
        await message.answer("⚠️ Guruh nomi noto'g'ri. Qaytadan kiriting (maksimal 50 belgi):")
        return

    await state.update_data(group_name=group)
    await state.set_state(StudentAddStates.waiting_for_parent_id)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏩ O'tkazib yuborish", callback_data="skip_parent_id")]
        ]
    )
    await message.answer(
        "➕ **Ota-ona Telegram ID raqamini kiriting (4/4):**\n"
        "(Ota-ona botga /start bosganda o'z ID sini bilib oladi)\n"
        "Agar hozir mavjud bo'lmasa, 'O'tkazib yuborish' tugmasini bosing:",
        reply_markup=kb,
        protect_content=True,
    )


@admin_students_router.callback_query(
    StudentAddStates.waiting_for_parent_id, F.data == "skip_parent_id"
)
async def skip_parent_id_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Ota-ona ID sini kiritmasdan o'tkazib yuborish."""
    await state.update_data(parent_telegram_id=None)
    await prompt_student_confirm(callback.message, state)
    await callback.answer()


@admin_students_router.message(StudentAddStates.waiting_for_parent_id)
async def process_student_parent_id(message: Message, state: FSMContext) -> None:
    """Ota-ona Telegram ID raqamini qabul qilish."""
    text = message.text.strip() if message.text else ""
    if not text.isdigit():
        await message.answer(
            "⚠️ Telegram ID faqat sonlardan iborat bo'lishi kerak. Qaytadan kiriting yoki o'tkazib yuboring:"
        )
        return

    await state.update_data(parent_telegram_id=int(text))
    await prompt_student_confirm(message, state)


async def prompt_student_confirm(target: Message, state: FSMContext) -> None:
    """Kiritilgan ma'lumotlarni ko'rsatish va tasdiqlashni so'rash."""
    data = await state.get_data()
    await state.set_state(StudentAddStates.confirm)

    p_id_str = (
        f"`{data.get('parent_telegram_id')}`" if data.get("parent_telegram_id") else "Bog'lanmagan"
    )

    summary = (
        "🦅 **Falcon Kibertexnology School**\n\n"
        "📋 **Yangi o'quvchi ma'lumotlarini tasdiqlang:**\n\n"
        f"👤 **F.I.SH:** {data.get('full_name')}\n"
        f"📊 **Daraja:** {data.get('level')}\n"
        f"👥 **Guruh:** {data.get('group_name')}\n"
        f"🔗 **Ota-ona Telegram ID:** {p_id_str}\n\n"
        "Ma'lumotlar to'g'rimi?"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, tasdiqlash", callback_data="confirm_add_student"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_add_student"),
            ]
        ]
    )
    await target.answer(summary, reply_markup=kb, protect_content=True)


@admin_students_router.callback_query(StudentAddStates.confirm, F.data == "confirm_add_student")
async def finalize_add_student(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """O'quvchini bazaga saqlash."""
    data = await state.get_data()
    await state.clear()

    student_repo = StudentRepository(session)
    new_student = await student_repo.create(
        full_name=data["full_name"],
        level=data["level"],
        group_name=data["group_name"],
        parent_telegram_id=data.get("parent_telegram_id"),
    )

    await callback.message.edit_text(
        f"✅ **O'quvchi muvaffaqiyatli qo'shildi!**\n\n"
        f"👤 **{new_student.full_name}** (#{new_student.id})\n"
        f"Guruh: {new_student.group_name} | Daraja: {new_student.level}",
        reply_markup=get_student_card_keyboard(new_student.id),
    )
    await callback.answer()


@admin_students_router.callback_query(StudentAddStates.confirm, F.data == "cancel_add_student")
async def cancel_add_student(callback: CallbackQuery, state: FSMContext) -> None:
    """Qo'shishni bekor qilish."""
    await state.clear()
    await callback.message.edit_text("❌ O'quvchi qo'shish bekor qilindi.")
    await callback.answer()


# ==================== O'QUVCHI KARTOCHKASI ====================
@admin_students_router.callback_query(StudentActionCallback.filter(F.action == "view"))
async def show_student_card(
    callback: CallbackQuery,
    callback_data: StudentActionCallback,
    session: AsyncSession,
) -> None:
    """O'quvchi kartochkasini barcha statistikasi bilan ochish."""
    student_repo = StudentRepository(session)
    grade_repo = GradeRepository(session)
    att_repo = AttendanceRepository(session)

    student = await student_repo.get_by_id(callback_data.student_id)
    if not student:
        await callback.answer("⚠️ O'quvchi topilmadi!", show_alert=True)
        return

    avg_score = await grade_repo.get_student_average(student.id)
    att_stats = await att_repo.get_student_stats(student.id)
    parent_str = (
        f"`{student.parent_telegram_id}`" if student.parent_telegram_id else "Bog'lanmagan ⚠️"
    )

    card_text = (
        "🦅 **Falcon Kibertexnology School — O'quvchi Kartochkasi**\n\n"
        f"👤 **F.I.SH:** {student.full_name}\n"
        f"🆔 **ID:** #{student.id}\n"
        f"📚 **Guruh:** {student.group_name}\n"
        f"📊 **Daraja:** {student.level}\n"
        f"⭐️ **O'rtacha ball:** {avg_score:.2f} / 5.0\n"
        f"📋 **Davomat:** {att_stats['percentage']:.1f}% "
        f"({att_stats['attended']} ta kelgan, {att_stats['missed']} ta qoldirgan)\n"
        f"🔗 **Ota-ona Telegram ID:** {parent_str}\n"
    )

    await callback.message.edit_text(card_text, reply_markup=get_student_card_keyboard(student.id))
    await callback.answer()


# ==================== SOFT DELETE ====================
@admin_students_router.callback_query(StudentActionCallback.filter(F.action == "delete_confirm"))
async def confirm_delete_student(
    callback: CallbackQuery, callback_data: StudentActionCallback
) -> None:
    """O'quvchini chiqarishdan avval tasdiq so'rash."""
    await callback.message.edit_text(
        "⚠️ **DIQQAT!**\n\n"
        "Haqiqatan ham ushbu o'quvchini kursdan chiqarib tashlamoqchimisiz?\n"
        "(O'quvchi soft delete qilinadi, baholar va davomat tarixi saqlanib qoladi).",
        reply_markup=get_delete_confirm_keyboard(callback_data.student_id),
    )
    await callback.answer()


@admin_students_router.callback_query(StudentActionCallback.filter(F.action == "delete_do"))
async def execute_soft_delete(
    callback: CallbackQuery,
    callback_data: StudentActionCallback,
    session: AsyncSession,
) -> None:
    """O'quvchini is_active=False qilish (soft delete)."""
    student_repo = StudentRepository(session)
    success = await student_repo.soft_delete(callback_data.student_id)
    if success:
        await callback.message.edit_text(
            "✅ O'quvchi muvaffaqiyatli chiqarib tashlandi (tarix saqlab qolindi).",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="◀️ Ro'yxatga qaytish",
                            callback_data=NavCallback(target="students", page=0).pack(),
                        )
                    ]
                ]
            ),
        )
    else:
        await callback.answer("⚠️ O'quvchini o'chirishda xatolik yuz berdi!")


# ==================== OTA-ONA ID BOG'LASH ====================
@admin_students_router.callback_query(StudentActionCallback.filter(F.action == "link_parent"))
async def prompt_link_parent(
    callback: CallbackQuery,
    callback_data: StudentActionCallback,
    state: FSMContext,
) -> None:
    """Ota-ona Telegram ID sini bog'lash so'rovi."""
    await state.set_state(StudentLinkParentStates.waiting_for_parent_id)
    await state.update_data(student_id=callback_data.student_id)
    await callback.message.answer(
        "🔗 **Ota-ona Telegram ID sini bog'lash:**\n\n"
        "Iltimos, ota-onaning haqiqiy Telegram ID raqamini kiriting:",
        protect_content=True,
    )
    await callback.answer()


@admin_students_router.message(StudentLinkParentStates.waiting_for_parent_id)
async def process_link_parent_id(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Ota-onani o'quvchiga bog'lash."""
    text = message.text.strip() if message.text else ""
    if not text.isdigit():
        await message.answer(
            "⚠️ Telegram ID faqat butun sonlardan iborat bo'lishi kerak. Qaytadan kiriting:"
        )
        return

    data = await state.get_data()
    student_id = data["student_id"]
    await state.clear()

    student_repo = StudentRepository(session)
    updated = await student_repo.link_parent(student_id=student_id, parent_telegram_id=int(text))

    if updated:
        await message.answer(
            f"✅ **Ota-ona muvaffaqiyatli bog'landi!**\n"
            f"O'quvchi: {updated.full_name}\n"
            f"Ota-ona Telegram ID: `{updated.parent_telegram_id}`",
            reply_markup=get_student_card_keyboard(updated.id),
            protect_content=True,
        )
    else:
        await message.answer("⚠️ O'quvchi topilmadi!", protect_content=True)
