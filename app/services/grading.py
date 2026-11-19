"""
Falcon Kibertexnology School - Baholash xizmati (GradingService).
O'rtacha ball, so'nggi baholar va haftalik/oylik statistikani hisoblaydi.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Grade
from app.database.repositories.grade_repo import GradeRepository


class GradingService:
    """O'quvchilar baholarini boshqarish va tahlil qilish xizmati."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.grade_repo = GradeRepository(session)

    async def add_grade(
        self,
        student_id: int,
        score: int,
        created_by: int,
        lesson_id: int | None = None,
        comment: str | None = None,
    ) -> Grade:
        """Yangi baho qo'shish (1 dan 5 gacha)."""
        if score < 1 or score > 5:
            raise ValueError("Baho 1 va 5 oralig'ida bo'lishi kerak.")
        return await self.grade_repo.create(
            student_id=student_id,
            score=score,
            created_by=created_by,
            lesson_id=lesson_id,
            comment=comment,
        )

    async def get_student_average(self, student_id: int) -> float:
        """O'quvchining umumiy o'rtacha bahosini olish."""
        return await self.grade_repo.get_student_average(student_id)

    async def get_recent_grades(self, student_id: int, limit: int = 10) -> list[Grade]:
        """O'quvchining oxirgi n ta bahosini olish."""
        return await self.grade_repo.get_by_student_id(student_id, limit=limit)

    async def get_weekly_average(self, student_id: int) -> float:
        """O'quvchining oxirgi 7 kundagi o'rtacha bahosi."""
        one_week_ago = datetime.now(UTC) - timedelta(days=7)
        grades = await self.grade_repo.get_grades_since(student_id, one_week_ago)
        if not grades:
            return 0.0
        return round(sum(g.score for g in grades) / len(grades), 2)

    async def get_monthly_average(self, student_id: int) -> float:
        """O'quvchining oxirgi 30 kundagi o'rtacha bahosi."""
        one_month_ago = datetime.now(UTC) - timedelta(days=30)
        grades = await self.grade_repo.get_grades_since(student_id, one_month_ago)
        if not grades:
            return 0.0
        return round(sum(g.score for g in grades) / len(grades), 2)

    async def get_comprehensive_grade_summary(self, student_id: int) -> dict[str, Any]:
        """O'quvchining barcha baholash ko'rsatkichlari to'plami."""
        all_grades = await self.grade_repo.get_by_student_id(student_id)
        avg_total = await self.get_student_average(student_id)
        avg_week = await self.get_weekly_average(student_id)
        avg_month = await self.get_monthly_average(student_id)
        recent = all_grades[:10]

        return {
            "total_grades_count": len(all_grades),
            "average_overall": avg_total,
            "average_weekly": avg_week,
            "average_monthly": avg_month,
            "recent_grades": recent,
        }
