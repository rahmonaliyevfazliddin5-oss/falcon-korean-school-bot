"""
Falcon Kibertexnology School - Ota-ona / Foydalanuvchi shaxsiy kabineti handlerlari.
Farzandim kartochkasi, baholar tarixi, davomat, o'qituvchi izohlari,
reyting, hozirgi dars va maktab haqida ma'lumotlar.
IDOR himoyasi to'liq kafolatlangan (ota-ona faqat o'z farzandini ko'ra oladi).
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

from app.database.models import Student, User
from app.database.repositories.attendance_repo import AttendanceRepository
from app.database.repositories.grade_repo import GradeRepository
from app.database.repositories.note_repo import TeacherNoteRepository
from app.database.repositories.school_info_repo import SchoolInfoRepository
from app.database.repositories.student_repo import StudentRepository
from app.keyboards.callbacks import LessonControlCallback
from app.services.lessons import LessonService
from app.services.rating import RatingService
from app.states import LessonCommentStates

parent_router = Router(name="parent_router")


async def get_parent_student(telegram_id: int, session: AsyncSession) -> Student | None:
    """Ota-onaning Telegram ID siga bog'langan faol birinchi o'quvchini olish."""
    student_repo = StudentRepository(session)
    students = await student_repo.get_by_parent_telegram_id(telegram_id)
    return students[0] if students else None


# ==================== 1. 👶 FARZANDIM ====================
@parent_router.message(F.text == "👶 Farzandim")
async def handle_my_child(message: Message, session: AsyncSession, current_user: User) -> None:
    """Bog'langan o'quvchi kartochkasi: o'rtacha ball, davomat, reyting o'rni."""
    user_id = message.from_user.id if message.from_user else 0
    student = await get_parent_student(user_id, session)

    if not student:
        await message.answer(
            "🦅 **Falcon Kibertexnology School**\n\n"
            "⚠️ **Sizga hali hech qaysi o'quvchi bog'lanmagan!**\n\n"
            f"Sizning shaxsiy Telegram ID raqamingiz: `{user_id}`\n\n"
            "Iltimos, ushbu ID raqamni maktab ma'muriyatiga (adminga) taqdim eting. "
            "Admin sizni o'quvchiga bog'lashi kerak.",
            protect_content=True,
        )
        return

    grade_repo = GradeRepository(session)
    att_repo = AttendanceRepository(session)
    rating_service = RatingService(session)

    avg_score = await grade_repo.get_student_average(student.id)
    att_stats = await att_repo.get_student_stats(student.id)
    rank_info = await rating_service.get_student_rank(student.id)
    rank_str = f"#{rank_info['rank']}" if rank_info else "Hisoblanmoqda"

    text = (
        "🦅 **Falcon Kibertexnology School — Farzandingiz ko'rsatkichlari**\n\n"
        f"👤 **O'quvchi:** {student.full_name}\n"
        f"📚 **Guruh:** {student.group_name}\n"
        f"📊 **Daraja:** {student.level}\n\n"
        f"⭐️ **O'rtacha baho:** {avg_score:.2f} / 5.0\n"
        f"📋 **Davomat foizi:** {att_stats['percentage']:.1f}% "
        f"({att_stats['attended']} ta qatnashgan, {att_stats['missed']} ta qoldirgan)\n"
        f"🏆 **Umumiy reytingdagi o'rni:** {rank_str}\n"
    )

    await message.answer(text, protect_content=True)


# ==================== 2. ⭐ BAHOLARIM ====================
@parent_router.message(F.text == "⭐ Baholarim")
async def handle_my_grades(message: Message, session: AsyncSession) -> None:
    """Farzandning oxirgi 10 ta baholari tarixi."""
    user_id = message.from_user.id if message.from_user else 0
    student = await get_parent_student(user_id, session)

    if not student:
        await message.answer("⚠️ Admin sizni o'quvchiga bog'lashi kerak.", protect_content=True)
        return

    grade_repo = GradeRepository(session)
    grades = await grade_repo.get_by_student_id(student.id, limit=10)
    avg_score = await grade_repo.get_student_average(student.id)

    text = (
        f"🦅 **Falcon Kibertexnology School**\n\n"
        f"⭐️ **Baholar tarixi:** {student.full_name}\n"
        f"📈 O'rtacha ball: **{avg_score:.2f}**\n\n"
    )

    if not grades:
        text += "Hozircha o'quvchiga baholar qo'yilmagan."
    else:
        text += "Oxirgi baholar:\n"
        for idx, g in enumerate(grades, start=1):
            date_str = g.created_at.strftime("%Y-%m-%d") if g.created_at else ""
            comment_str = f" - *{g.comment}*" if g.comment else ""
            text += f"{idx}. ⭐️ **{g.score} ball** ({date_str}){comment_str}\n"

    await message.answer(text, protect_content=True)


# ==================== 3. 📋 DAVOMAT ====================
@parent_router.message(F.text == "📋 Davomat")
async def handle_my_attendance(message: Message, session: AsyncSession) -> None:
    """Farzandning davomat ko'rsatkichlari."""
    user_id = message.from_user.id if message.from_user else 0
    student = await get_parent_student(user_id, session)

    if not student:
        await message.answer("⚠️ Admin sizni o'quvchiga bog'lashi kerak.", protect_content=True)
        return

    att_repo = AttendanceRepository(session)
    stats = await att_repo.get_student_stats(student.id)

    text = (
        f"🦅 **Falcon Kibertexnology School**\n\n"
        f"📋 **Davomat hisoboti:** {student.full_name}\n\n"
        f"✅ Darslarga qatnashgan: **{stats['attended']} ta**\n"
        f"❌ Dars qoldirgan (kelmadi): **{stats['missed']} ta**\n"
        f"📄 Sababli qoldirgan: **{stats['excused']} ta**\n"
        f"📚 Jami darslar soni: **{stats['total']} ta**\n"
        f"📊 **Umumiy davomat ko'rsatkichi: {stats['percentage']:.1f}%**\n"
    )

    await message.answer(text, protect_content=True)


# ==================== 4. 📝 O'QITUVCHI IZOHI ====================
@parent_router.message(F.text == "📝 O'qituvchi izohi")
async def handle_teacher_notes(message: Message, session: AsyncSession) -> None:
    """O'qituvchining faqat o'z farzandiga yozgan izohlarini ko'rsatish (IDOR himoyasi)."""
    user_id = message.from_user.id if message.from_user else 0
    student = await get_parent_student(user_id, session)

    if not student:
        await message.answer("⚠️ Admin sizni o'quvchiga bog'lashi kerak.", protect_content=True)
        return

    note_repo = TeacherNoteRepository(session)
    notes = await note_repo.get_by_student_id(student.id, limit=10)

    text = (
        f"🦅 **Falcon Kibertexnology School**\n\n"
        f"📝 **O'qituvchi izohlari:** {student.full_name}\n\n"
    )

    if not notes:
        text += "Hozircha o'qituvchi tomonidan izoh qoldirilmagan."
    else:
        for idx, n in enumerate(notes, start=1):
            date_str = n.created_at.strftime("%Y-%m-%d %H:%M") if n.created_at else ""
            text += f'**{idx}.** "{n.text}"\n   └ 📅 {date_str}\n\n'

    await message.answer(text, protect_content=True)


# ==================== 5. 🏆 REYTING ====================
@parent_router.message(F.text == "🏆 Reyting")
async def handle_user_rating(message: Message, session: AsyncSession) -> None:
    """TOP-10 reyting jadvali va farzandning o'z o'rni."""
    user_id = message.from_user.id if message.from_user else 0
    student = await get_parent_student(user_id, session)

    rating_service = RatingService(session)
    ratings = await rating_service.get_all_ratings()
    text = rating_service.format_rating_message(
        ratings=ratings,
        highlight_student_id=student.id if student else None,
        top_limit=10,
    )
    await message.answer(text, protect_content=True)


# ==================== 6. 🎥 HOZIRGI DARS ====================
@parent_router.message(F.text == "🎥 Hozirgi dars")
async def handle_current_lesson(message: Message, session: AsyncSession) -> None:
    """
    Hozirgi dars holatini tekshirish.
    Faol dars bo'lsa qo'shilish tugmasi va izoh qoldirish imkoni,
    bo'lmasa jadval ko'rsatiladi.
    """
    lesson_service = LessonService(session)
    active, scheduled = await lesson_service.get_current_or_next_lesson()

    if active:
        buttons: list[list[InlineKeyboardButton]] = [
            [
                InlineKeyboardButton(
                    text="💬 Dars haqida fikr bildirish",
                    callback_data=LessonControlCallback(
                        action="user_comment", lesson_id=active.id
                    ).pack(),
                )
            ]
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

        text = (
            "🦅 **Falcon Kibertexnology School**\n\n"
            f"🔴 **HOZIRDA DARS DAVOM ETMOQDA!**\n\n"
            f"📌 **Mavzu:** {active.title}\n"
            f"🕐 Boshlangan vaqti: {active.starts_at.strftime('%H:%M')}\n\n"
            "Dars darslar guruhida video chat ko'rinishida bo'lib o'tmoqda."
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
            text += "Yaqin orada rejalashtirilgan yangi darslar mavjud emas."

        await message.answer(text, protect_content=True)


@parent_router.callback_query(LessonControlCallback.filter(F.action == "user_comment"))
async def prompt_lesson_comment(
    callback: CallbackQuery,
    callback_data: LessonControlCallback,
    state: FSMContext,
) -> None:
    """Darsga fikr/izoh yozish so'rovi."""
    await state.set_state(LessonCommentStates.waiting_for_comment)
    await state.update_data(lesson_id=callback_data.lesson_id)

    await callback.message.answer(
        "💬 **Dars haqida fikr yoki savolingizni yozing:**\n"
        "(Ushbu xabaringiz o'qituvchi va ma'muriyatga yetkaziladi)",
        protect_content=True,
    )
    await callback.answer()


@parent_router.message(LessonCommentStates.waiting_for_comment)
async def save_user_lesson_comment(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
    """Foydalanuvchi izohini saqlash."""
    text = message.text.strip() if message.text else ""
    if len(text) < 3:
        await message.answer("⚠️ Fikringiz juda qisqa. Qaytadan yozing:")
        return

    data = await state.get_data()
    lesson_id = data["lesson_id"]
    await state.clear()

    lesson_service = LessonService(session)
    await lesson_service.add_comment(
        lesson_id=lesson_id,
        telegram_id=message.from_user.id if message.from_user else 0,
        text=text,
    )

    await message.answer(
        "✅ **Fikringiz uchun tashakkur! Izohingiz muvaffaqiyatli qabul qilindi.**",
        protect_content=True,
    )


# ==================== 7. ℹ️ MAKTAB HAQIDA ====================
@parent_router.message(F.text == "ℹ️ Maktab haqida")
async def handle_about_school(message: Message, session: AsyncSession) -> None:
    """Maktab haqidagi ma'lumotlarni chiqarish."""
    school_repo = SchoolInfoRepository(session)
    about_text = await school_repo.get_info("about_school")

    text = f"🦅 **Falcon Kibertexnology School**\n\n{about_text}"
    await message.answer(text, protect_content=True)
