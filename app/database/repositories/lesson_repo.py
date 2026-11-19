"""
Falcon Kibertexnology School - Darslar ombori (LessonRepository).
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Lesson


class LessonRepository:
    """Darslar modeli uchun CRUD va qidiruv amallari."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        title: str,
        starts_at: datetime,
        created_by: int | None = None,
    ) -> Lesson:
        """Yangi dars rejalashtirish."""
        # Agar vaqt zonasi bo'lmasa, UTC ga keltiramiz
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=UTC)

        lesson = Lesson(
            title=title.strip(),
            starts_at=starts_at,
            status="rejalashtirilgan",
            created_by=created_by,
        )
        self.session.add(lesson)
        await self.session.commit()
        await self.session.refresh(lesson)
        return lesson

    async def get_by_id(self, lesson_id: int) -> Lesson | None:
        """ID bo'yicha darsni olish."""
        stmt = select(Lesson).where(Lesson.id == lesson_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_active_lesson(self) -> Lesson | None:
        """Hozir davom etayotgan darsni olish."""
        stmt = (
            select(Lesson).where(Lesson.status == "davom_etmoqda").order_by(Lesson.starts_at.desc())
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_next_scheduled_lesson(self) -> Lesson | None:
        """Keyingi rejalashtirilgan darsni olish."""
        now = datetime.now(UTC)
        stmt = (
            select(Lesson)
            .where(
                Lesson.status == "rejalashtirilgan",
                Lesson.starts_at >= now,
            )
            .order_by(Lesson.starts_at.asc())
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_all_lessons(self, limit: int = 50) -> list[Lesson]:
        """Barcha darslar ro'yxatini olish."""
        stmt = select(Lesson).order_by(Lesson.starts_at.desc()).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update_status(
        self,
        lesson_id: int,
        status: str,
        ended_at: datetime | None = None,
    ) -> Lesson | None:
        """Dars holatini yangilash (masalan: 'davom_etmoqda', 'tugagan')."""
        lesson = await self.get_by_id(lesson_id)
        if not lesson:
            return None
        lesson.status = status
        if ended_at:
            if ended_at.tzinfo is None:
                ended_at = ended_at.replace(tzinfo=UTC)
            lesson.ended_at = ended_at
        elif status == "tugagan" and not lesson.ended_at:
            lesson.ended_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(lesson)
        return lesson

    async def delete(self, lesson_id: int) -> bool:
        """Darsni o'chirish."""
        lesson = await self.get_by_id(lesson_id)
        if not lesson:
            return False
        await self.session.delete(lesson)
        await self.session.commit()
        return True
