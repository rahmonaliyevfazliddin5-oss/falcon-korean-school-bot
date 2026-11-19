"""
Falcon Kibertexnology School - Baholar ombori (GradeRepository).
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Grade


class GradeRepository:
    """Baholar uchun CRUD va agregatsiya amallari."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        student_id: int,
        score: int,
        created_by: int,
        lesson_id: int | None = None,
        comment: str | None = None,
    ) -> Grade:
        """Yangi baho qo'shish."""
        grade = Grade(
            student_id=student_id,
            score=score,
            created_by=created_by,
            lesson_id=lesson_id,
            comment=comment.strip() if comment else None,
        )
        self.session.add(grade)
        await self.session.commit()
        await self.session.refresh(grade)
        return grade

    async def get_by_id(self, grade_id: int) -> Grade | None:
        """ID bo'yicha bahoni olish."""
        stmt = select(Grade).where(Grade.id == grade_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_student_id(self, student_id: int, limit: int | None = None) -> list[Grade]:
        """O'quvchining baholarini kamayish tartibida olish."""
        stmt = (
            select(Grade)
            .where(Grade.student_id == student_id)
            .order_by(Grade.created_at.desc(), Grade.id.desc())
        )
        if limit:
            stmt = stmt.limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_student_average(self, student_id: int) -> float:
        """O'quvchining o'rtacha bahosini hisoblash."""
        stmt = select(func.avg(Grade.score)).where(Grade.student_id == student_id)
        res = await self.session.execute(stmt)
        avg_score = res.scalar()
        return round(float(avg_score), 2) if avg_score is not None else 0.0

    async def get_grades_since(self, student_id: int, since_datetime: datetime) -> list[Grade]:
        """Muayyan sanadan keyingi baholarni olish (haftalik/oylik tahlil uchun)."""
        stmt = (
            select(Grade)
            .where(
                Grade.student_id == student_id,
                Grade.created_at >= since_datetime,
            )
            .order_by(Grade.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_all(self) -> list[Grade]:
        """Barcha baholarni olish."""
        stmt = select(Grade).order_by(Grade.created_at.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def delete(self, grade_id: int) -> bool:
        """Bahoni o'chirish."""
        grade = await self.get_by_id(grade_id)
        if not grade:
            return False
        await self.session.delete(grade)
        await self.session.commit()
        return True
