"""
Falcon Kibertexnology School - Admin: Statistika va Reyting handlerlari.
Maktab bo'yicha umumiy ko'rsatkichlar, dars qoldirganlar tahlili va TOP-10 reyting.
"""

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Grade, Lesson, Student
from app.services.attendance import AttendanceService
from app.services.rating import RatingService
from app.utils.filters import IsAdminFilter

admin_stats_router = Router(name="admin_stats_router")
admin_stats_router.message.filter(IsAdminFilter())
admin_stats_router.callback_query.filter(IsAdminFilter())


@admin_stats_router.message(F.text == "🏆 Reyting")
async def handle_admin_rating(message: Message, session: AsyncSession) -> None:
    """Admin uchun o'quvchilar reytingini chiqarish."""
    rating_service = RatingService(session)
    ratings = await rating_service.get_all_ratings()
    text = rating_service.format_rating_message(ratings, top_limit=10)
    await message.answer(text, protect_content=True)


@admin_stats_router.message(F.text == "📊 Statistika")
async def handle_admin_stats(message: Message, session: AsyncSession) -> None:
    """Admin uchun maktabning umumiy statistikasi va eng ko'p dars qoldirganlar hisoboti."""
    att_service = AttendanceService(session)

    # 1. Umumiy hisoblar
    st_count_res = await session.execute(
        select(func.count(Student.id)).where(Student.is_active == True)
    )
    total_students = st_count_res.scalar() or 0

    lsn_count_res = await session.execute(select(func.count(Lesson.id)))
    total_lessons = lsn_count_res.scalar() or 0

    grd_res = await session.execute(select(func.count(Grade.id), func.avg(Grade.score)))
    grd_row = grd_res.one()
    total_grades = grd_row[0] or 0
    avg_school_score = float(grd_row[1]) if grd_row[1] is not None else 0.0

    # 2. Eng ko'p dars qoldirgan 10 o'quvchi
    top_absent = await att_service.get_top_absent_report(limit=10)

    text = (
        "🦅 **Falcon Kibertexnology School — Umumiy Statistika**\n\n"
        f"👥 Faol o'quvchilar soni: **{total_students} nafar**\n"
        f"📚 Jami o'tilgan/rejalashtirilgan darslar: **{total_lessons} ta**\n"
        f"⭐️ Jami qo'yilgan baholar: **{total_grades} ta**\n"
        f"📈 Maktab bo'yicha o'rtacha o'zlashtirish: **{avg_school_score:.2f} ball**\n\n"
        "─────────────────────\n"
        "⚠️ **Eng ko'p dars qoldirgan o'quvchilar (TOP-10):**\n"
    )

    if not top_absent:
        text += "Davomat bo'yicha qoldirilgan darslar yo'q! Barcha darslarga qatnashilgan."
    else:
        for idx, item in enumerate(top_absent, start=1):
            text += (
                f"{idx}. {item['full_name']} ({item['group_name']}) — "
                f"**{item['missed_count']} ta dars qoldirgan**\n"
            )

    await message.answer(text, protect_content=True)
