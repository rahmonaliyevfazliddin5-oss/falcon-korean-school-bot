"""
Falcon Kibertexnology School - Oddiy foydalanuvchi handlerlari (handlers/user/dashboard.py).
Faqat o'qish huquqi: o'quvchilar ro'yxati (sahifalash va qidiruv),
o'quvchi kartochkasi (shaxsiy ma'lumotlarsiz), izohlar, davomat ko'rsatkichlari,
umumiy reyting (TOP-10 va to'liq ro'yxat sahifalash bilan),
hozirgi dars, darsga izoh qoldirish va maktab haqida ma'lumot.
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
from app.database.repositories.note_repo import TeacherNoteRepository
from app.database.repositories.school_info_repo import SchoolInfoRepository
from app.database.repositories.student_repo import StudentRepository
from app.keyboards.builders import (
    get_user_back_to_student_keyboard,
    get_user_rating_keyboard,
    get_user_student_card_keyboard,
    get_user_students_keyboard,
)
from app.keyboards.callbacks import (
    UserLessonCallback,
    UserNavCallback,
    UserStudentCallback,
)
from app.services.attendance import AttendanceService
from app.services.lessons import LessonService
from app.services.rating import RatingService
from app.states import LessonCommentStates, StudentSearchStates

user_router = Router(name="user_router")


async def render_user_students_page(
    target_event: Message | CallbackQuery,
    session: AsyncSession,
    page: int = 0,
    search: str | None = None,
) -> None:
    """Foydalanuvchi uchun o'quvchilar ro'yxatini chiqarish."""
    student_repo = StudentRepository(session)
    students, total_count = await student_repo.get_active_students(
        offset=page * 8, limit=8, search_query=search
    )

    kb = get_user_students_keyboard(
        students=students,
        page=page,
        total_count=total_count,
        page_size=8,
        search=search,
    )

    header = "👥 **Falcon Kibertexnology School — O'quvchilar ro'yxati**\n\n"
    if search:
        header += f"🔍 Qidiruv natijalari: '{search}' ({total_count} ta o'quvchi topildi)\n\n"
    else:
        header += f"Jami faol o'quvchilar soni: **{total_count} nafar**\n\n"

    header += "O'quvchi ko'rsatkichlari bilan tanishish uchun uning ustiga bosing:"

    if isinstance(target_event, CallbackQuery):
        if target_event.message:
            await target_event.message.edit_text(header, reply_markup=kb)
        await target_event.answer()
    else:
        await target_event.answer(header, reply_markup=kb, protect_content=True)


# ==================== 1. 👥 O'QUVCHILAR RO'YXATI ====================
@user_router.message(F.text == "👥 O'quvchilar")
async def user_students_menu_click(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Foydalanuvchi menyusidagi '👥 O'quvchilar' tugmasi."""
    await state.clear()
    await render_user_students_page(message, session, page=0)


@user_router.callback_query(UserNavCallback.filter(F.target == "students"))
async def user_students_nav(
    callback: CallbackQuery, callback_data: UserNavCallback, session: AsyncSession
) -> None:
    """Foydalanuvchi sahifalash navigatsiyasi (◀️ ▶️)."""
    await render_user_students_page(
        callback, session, page=callback_data.page, search=callback_data.search
    )


# ==================== QIDIRUV (SEARCH) ====================
@user_router.callback_query(UserNavCallback.filter(F.target == "search_student"))
async def user_start_search(callback: CallbackQuery, state: FSMContext) -> None:
    """Qidirish boshlash."""
    await state.set_state(StudentSearchStates.waiting_for_query)
    if callback.message:
        await callback.message.answer(
            "🔍 **O'quvchini qidirish:**\nO'quvchining ism yoki familiyasini kiriting:",
            protect_content=True,
        )
    await callback.answer()


@user_router.message(StudentSearchStates.waiting_for_query)
async def user_process_search_query(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Qidiruv so'zini qabul qilish va natijani chiqarish."""
    query = message.text.strip() if message.text else ""
    if not query or len(query) < 2:
        await message.answer(
            "⚠️ Qidiruv uchun kamida 2 ta harf kiriting:",
            protect_content=True,
        )
        return

    await state.clear()
    await render_user_students_page(message, session, page=0, search=query)


# ==================== 2. O'QUVCHI KARTOCHKASI ====================
@user_router.callback_query(UserStudentCallback.filter(F.action == "view"))
async def user_view_student_card(
    callback: CallbackQuery,
    callback_data: UserStudentCallback,
    session: AsyncSession,
) -> None:
    """
    O'quvchi kartochkasini chiqarish.
    Faqat ruxsat etilgan maydonlar: Ism, daraja, guruh, o'rtacha ball,
    davomat foizi, reyting o'rni, oxirgi baholar.
    Hech qanday shaxsiy ma'lumot (telefon, ota-ona Telegram ID) ko'rsatilmaydi!
    """
    student_repo = StudentRepository(session)
    grade_repo = GradeRepository(session)
    att_repo = AttendanceRepository(session)
    rating_service = RatingService(session)

    student = await student_repo.get_by_id(callback_data.student_id)
    if not student or not student.is_active:
        await callback.answer("⚠️ O'quvchi topilmadi yoki chiqarilgan!", show_alert=True)
        return

    avg_score = await grade_repo.get_student_average(student.id)
    att_stats = await att_repo.get_student_stats(student.id)
    rank_info = await rating_service.get_student_rank(student.id)
    rank_str = f"#{rank_info['rank']}" if rank_info else "Hisoblanmoqda"

    recent_grades = await grade_repo.get_by_student_id(student.id, limit=5)
    if recent_grades:
        grades_str = ", ".join(f"⭐️{g.score}" for g in recent_grades)
    else:
        grades_str = "Hozircha baholar yo'q"

    card_text = (
        "🦅 **Falcon Kibertexnology School — O'quvchi Ko'rsatkichlari**\n\n"
        f"👤 **F.I.SH:** {student.full_name}\n"
        f"📚 **Guruh:** {student.group_name}\n"
        f"📊 **Daraja:** {student.level}\n"
        f"🏆 **Reytingdagi o'rni:** {rank_str}\n\n"
        f"⭐️ **O'rtacha ball:** {avg_score:.2f} / 5.0\n"
        f"📈 **So'nggi baholar:** {grades_str}\n"
        f"📋 **Davomat:** {att_stats['percentage']:.1f}% "
        f"({att_stats['attended']} ta qatnashgan, {att_stats['missed']} ta qoldirgan)\n\n"
        "Batafsil ma'lumot olish uchun tugmalardan foydalaning:"
    )

    kb = get_user_student_card_keyboard(student.id)
    if callback.message:
        await callback.message.edit_text(card_text, reply_markup=kb)
    await callback.answer()


# ==================== 3. 📝 O'QUVCHI IZOHLARI ====================
@user_router.callback_query(UserStudentCallback.filter(F.action == "notes"))
async def user_view_student_notes(
    callback: CallbackQuery,
    callback_data: UserStudentCallback,
    session: AsyncSession,
) -> None:
    """Tanlangan o'quvchi haqida o'qituvchi izohlarini ko'rish (faqat o'qish)."""
    student_repo = StudentRepository(session)
    note_repo = TeacherNoteRepository(session)

    student = await student_repo.get_by_id(callback_data.student_id)
    if not student or not student.is_active:
        await callback.answer("⚠️ O'quvchi topilmadi!", show_alert=True)
        return

    notes = await note_repo.get_by_student_id(student.id, limit=10)

    text = (
        f"🦅 **Falcon Kibertexnology School**\n\n"
        f"📝 **O'qituvchi izohlari:** {student.full_name}\n\n"
    )

    if not notes:
        text += "Ushbu o'quvchi uchun hozircha izohlar qoldirilmagan."
    else:
        for idx, n in enumerate(notes, start=1):
            date_str = n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else ""
            text += f'**{idx}.** "{n.text}"\n   └ 📅 {date_str}\n\n'

    kb = get_user_back_to_student_keyboard(student.id)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ==================== 4. 📋 O'QUVCHI DAVOMATI ====================
@user_router.callback_query(UserStudentCallback.filter(F.action == "attendance"))
async def user_view_student_attendance(
    callback: CallbackQuery,
    callback_data: UserStudentCallback,
    session: AsyncSession,
) -> None:
    """Tanlangan o'quvchining davomat hisobotini ko'rish."""
    student_repo = StudentRepository(session)
    att_service = AttendanceService(session)

    student = await student_repo.get_by_id(callback_data.student_id)
    if not student or not student.is_active:
        await callback.answer("⚠️ O'quvchi topilmadi!", show_alert=True)
        return

    stats = await att_service.get_student_stats(student.id)

    text = (
        f"🦅 **Falcon Kibertexnology School**\n\n"
        f"📋 **Davomat hisoboti:** {student.full_name}\n\n"
        f"✅ Darslarga qatnashgan: **{stats['attended']} ta**\n"
        f"❌ Dars qoldirgan: **{stats['missed']} ta**\n"
        f"📄 Sababli qoldirgan: **{stats['excused']} ta**\n"
        f"📚 Jami darslar soni: **{stats['total']} ta**\n\n"
        f"📊 **Umumiy davomat foizi: {stats['percentage']:.1f}%**\n"
    )

    kb = get_user_back_to_student_keyboard(student.id)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ==================== 5. 🏆 REYTING ====================
@user_router.message(F.text == "🏆 Reyting")
async def user_rating_menu_click(message: Message, session: AsyncSession) -> None:
    """Foydalanuvchi menyusidagi '🏆 Reyting' tugmasi (TOP-10)."""
    rating_service = RatingService(session)
    ratings = await rating_service.get_all_ratings()
    text = rating_service.format_rating_message(ratings, top_limit=10)
    kb = get_user_rating_keyboard(page=0, total_count=len(ratings), is_full=False)
    await message.answer(text, reply_markup=kb, protect_content=True)


@user_router.callback_query(UserNavCallback.filter(F.target == "rating_top"))
async def user_rating_top_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """TOP-10 ga qaytish."""
    rating_service = RatingService(session)
    ratings = await rating_service.get_all_ratings()
    text = rating_service.format_rating_message(ratings, top_limit=10)
    kb = get_user_rating_keyboard(page=0, total_count=len(ratings), is_full=False)
    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@user_router.callback_query(UserNavCallback.filter(F.target == "rating_full"))
async def user_rating_full_callback(
    callback: CallbackQuery,
    callback_data: UserNavCallback,
    session: AsyncSession,
) -> None:
    """Barcha o'quvchilar umumiy reytingi (sahifalash bilan)."""
    rating_service = RatingService(session)
    ratings = await rating_service.get_all_ratings()
    total = len(ratings)

    page = callback_data.page
    page_size = 10
    start_idx = page * page_size
    page_ratings = ratings[start_idx : start_idx + page_size]

    lines = [
        "🦅 **Falcon Kibertexnology School**",
        f"🏆 **Barcha o'quvchilar to'liq reytingi ({total} nafar):**\n",
    ]

    medal_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
    for item in page_ratings:
        rank = item["rank"]
        emoji = medal_emojis.get(rank, f"**{rank}.**")
        lines.append(
            f"{emoji} {item['full_name']} ({item['group_name']})\n"
            f"   └ ⭐️ **Ball: {item['total_score']:.2f}** | Baho: {item['average_score']} | Davomat: {item['attendance_percentage']:.0f}%"
        )

    text = "\n".join(lines)
    kb = get_user_rating_keyboard(page=page, total_count=total, page_size=page_size, is_full=True)

    if callback.message:
        await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ==================== 6. 🎥 HOZIRGI DARS ====================
@user_router.message(F.text == "🎥 Hozirgi dars")
async def user_current_lesson(message: Message, session: AsyncSession) -> None:
    """Faol dars yoki keyingi rejalashtirilgan dars jadvali."""
    lesson_service = LessonService(session)
    active, scheduled = await lesson_service.get_current_or_next_lesson()

    if active:
        buttons = [
            [
                InlineKeyboardButton(
                    text="💬 Dars haqida fikr bildirish",
                    callback_data=UserLessonCallback(action="comment", lesson_id=active.id).pack(),
                )
            ]
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        text = (
            "🦅 **Falcon Kibertexnology School**\n\n"
            f"🔴 **HOZIRDA DARS DAVOM ETMOQDA!**\n\n"
            f"📌 **Mavzu:** {active.title}\n"
            f"🕐 Boshlangan vaqti: {active.starts_at.strftime('%H:%M')}\n\n"
            "Darsimiz guruhda video chat orqali bo'lib o'tmoqda. "
            "Guruhga kirib video qo'ng'iroqqa qo'shiling!"
        )
        await message.answer(text, reply_markup=kb, protect_content=True)
    else:
        text = "🦅 **Falcon Kibertexnology School**\n\n⚪️ **Hozirda faol dars mavjud emas.**\n\n"
        if scheduled:
            text += (
                f"📅 **Keyingi rejalashtirilgan dars:**\n"
                f"📌 **Mavzu:** {scheduled.title}\n"
                f"🕐 **Boshlanish vaqti:** {scheduled.starts_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                "Dars boshlanishidan 15 daqiqa oldin sizga eslatma xabari yuboriladi!"
            )
        else:
            text += "Yaqin orada rejalashtirilgan darslar yo'q."

        await message.answer(text, protect_content=True)


# ==================== 7. 💬 DARS HAQIDA IZOH ====================
@user_router.message(F.text == "💬 Dars haqida izoh")
async def user_comment_menu_click(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    """Foydalanuvchi dars haqida fikr qoldirish menyusi."""
    lesson_service = LessonService(session)
    active, scheduled = await lesson_service.get_current_or_next_lesson()

    target_lesson = active or scheduled
    if not target_lesson:
        await message.answer(
            "🦅 **Falcon Kibertexnology School**\n\n"
            "⚠️ Hozircha fikr qoldirish uchun faol darslar mavjud emas.",
            protect_content=True,
        )
        return

    await state.set_state(LessonCommentStates.waiting_for_comment)
    await state.update_data(lesson_id=target_lesson.id)
    await message.answer(
        f"💬 **'{target_lesson.title}' darsi haqida fikringiz yoki savolingizni yozing:**\n\n"
        "(Sizning izohingiz maktab o'qituvchilariga yetkaziladi)",
        protect_content=True,
    )


@user_router.callback_query(UserLessonCallback.filter(F.action == "comment"))
async def user_comment_callback(
    callback: CallbackQuery,
    callback_data: UserLessonCallback,
    state: FSMContext,
) -> None:
    """Inline tugma orqali darsga fikr bildirish."""
    await state.set_state(LessonCommentStates.waiting_for_comment)
    await state.update_data(lesson_id=callback_data.lesson_id)
    if callback.message:
        await callback.message.answer(
            "💬 **Dars haqida fikr yoki taklifingizni kiriting:**",
            protect_content=True,
        )
    await callback.answer()


@user_router.message(LessonCommentStates.waiting_for_comment)
async def user_save_comment(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Foydalanuvchi dars izohini saqlash."""
    text = message.text.strip() if message.text else ""
    if len(text) < 3:
        await message.answer(
            "⚠️ Fikringiz juda qisqa. Qaytadan kiriting:",
            protect_content=True,
        )
        return

    data = await state.get_data()
    lesson_id = data.get("lesson_id", 0)
    await state.clear()

    if lesson_id:
        lesson_service = LessonService(session)
        user_id = message.from_user.id if message.from_user else 0
        await lesson_service.add_comment(lesson_id=lesson_id, telegram_id=user_id, text=text)

    await message.answer(
        "✅ **Fikringiz uchun tashakkur! Izohingiz muvaffaqiyatli qabul qilindi.**",
        protect_content=True,
    )


# ==================== 8. ℹ️ MAKTAB HAQIDA ====================
@user_router.message(F.text == "ℹ️ Maktab haqida")
async def user_about_school(message: Message, session: AsyncSession) -> None:
    """Maktab haqidagi ma'lumotlar matni."""
    school_repo = SchoolInfoRepository(session)
    about_text = await school_repo.get_info("about_school")

    text = f"🦅 **Falcon Kibertexnology School**\n\n{about_text}"
    await message.answer(text, protect_content=True)
