"""
Falcon Kibertexnology School - Reyting xizmati (RatingService).
O'quvchilar reytingini formulasi bo'yicha hisoblaydi:
umumiy_ball = (o'rtacha_baho * 0.7) + (davomat_foizi / 100 * 5 * 0.3)
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.attendance_repo import AttendanceRepository
from app.database.repositories.grade_repo import GradeRepository
from app.database.repositories.student_repo import StudentRepository


class RatingService:
    """O'quvchilar umumiy reytingini har bir so'rovda hisoblovchi xizmat."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.student_repo = StudentRepository(session)
        self.grade_repo = GradeRepository(session)
        self.attendance_repo = AttendanceRepository(session)

    async def get_all_ratings(self) -> list[dict[str, Any]]:
        """
        Barcha faol o'quvchilarning reytingini hisoblab,
        eng yuqori ball bo'yicha saralangan ro'yxatni qaytaradi.
        """
        students = await self.student_repo.get_all_active()
        if not students:
            return []

        rating_list: list[dict[str, Any]] = []

        for student in students:
            # 1. O'rtacha baho va baholar soni
            grades = await self.grade_repo.get_by_student_id(student.id)
            grades_count = len(grades)
            if grades_count > 0:
                avg_grade = sum(g.score for g in grades) / grades_count
            else:
                avg_grade = 0.0

            # 2. Davomat foizi
            att_stats = await self.attendance_repo.get_student_stats(student.id)
            attendance_pct = att_stats["percentage"]

            # 3. Formula: umumiy_ball = (o'rtacha_baho * 0.7) + (davomat_foizi/100 * 5 * 0.3)
            total_score = round((avg_grade * 0.7) + ((attendance_pct / 100.0) * 5.0 * 0.3), 3)

            rating_list.append(
                {
                    "student_id": student.id,
                    "full_name": student.full_name,
                    "group_name": student.group_name,
                    "level": student.level,
                    "parent_telegram_id": student.parent_telegram_id,
                    "user_telegram_id": student.user_telegram_id,
                    "average_score": round(avg_grade, 2),
                    "grades_count": grades_count,
                    "attendance_percentage": attendance_pct,
                    "total_score": total_score,
                }
            )

        # Saralash:
        # 1-darajali: total_score (kamayish tartibida)
        # 2-darajali: grades_count (teng bo'lsa, baholar soni ko'pi yuqoriroq)
        # 3-darajali: student_id (tenglikda barqaror tartib)
        rating_list.sort(
            key=lambda x: (x["total_score"], x["grades_count"], -x["student_id"]),
            reverse=True,
        )

        # O'rinlarni belgilash
        for idx, item in enumerate(rating_list, start=1):
            item["rank"] = idx

        return rating_list

    async def get_top_n(self, n: int = 10) -> list[dict[str, Any]]:
        """TOP-N reyting ro'yxatini olish."""
        ratings = await self.get_all_ratings()
        return ratings[:n]

    async def get_student_rank(self, student_id: int) -> dict[str, Any] | None:
        """Muayyan o'quvchining reytingdagi o'rni va ko'rsatkichlarini olish."""
        ratings = await self.get_all_ratings()
        for item in ratings:
            if item["student_id"] == student_id:
                return item
        return None

    def format_rating_message(
        self,
        ratings: list[dict[str, Any]],
        highlight_student_id: int | None = None,
        top_limit: int = 10,
    ) -> str:
        """Reyting ro'yxatini Telegram xabari formatiga keltirish."""
        if not ratings:
            return (
                "🦅 **Falcon Kibertexnology School**\n\n"
                "🏆 **O'quvchilar reytingi**\n\n"
                "Hozircha reyting uchun ma'lumotlar mavjud emas."
            )

        lines: list[str] = [
            "🦅 **Falcon Kibertexnology School**",
            "🏆 **Koreys tili kursi o'quvchilari reytingi (TOP-10):**\n",
        ]

        top_slice = ratings[:top_limit]
        medal_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}

        for item in top_slice:
            rank = item["rank"]
            emoji = medal_emojis.get(rank, f"**{rank}.**")
            name = item["full_name"]
            group = item["group_name"]
            score = item["total_score"]
            avg = item["average_score"]
            att = item["attendance_percentage"]

            line = (
                f"{emoji} {name} ({group})\n"
                f"   └ ⭐️ **Ball: {score:.2f}** | Baho: {avg} | Davomat: {att:.0f}%"
            )
            if highlight_student_id and item["student_id"] == highlight_student_id:
                line = f"👉 {line} 👈"
            lines.append(line)

        # Agar foydalanuvchining o'quvchisi top-10 da bo'lmasa, pastida alohida ko'rsatish
        if highlight_student_id:
            user_item = next((x for x in ratings if x["student_id"] == highlight_student_id), None)
            if user_item and user_item["rank"] > top_limit:
                lines.append("\n─────────────────────")
                lines.append(
                    f"📍 **Sizning farzandingiz:** #{user_item['rank']} - {user_item['full_name']}\n"
                    f"   └ ⭐️ **Ball: {user_item['total_score']:.2f}** | Baho: {user_item['average_score']} | "
                    f"Davomat: {user_item['attendance_percentage']:.0f}%"
                )

        return "\n".join(lines)
