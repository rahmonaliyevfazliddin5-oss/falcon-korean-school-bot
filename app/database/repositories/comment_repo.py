"""
Falcon Kibertexnology School - Dars izohlari ombori (LessonCommentRepository).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import LessonComment


class LessonCommentRepository:
    """Darsga qoldirilgan izohlar uchun CRUD amallari."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, lesson_id: int, telegram_id: int, text: str) -> LessonComment:
        """Darsga izoh qo'shish."""
        comment = LessonComment(
            lesson_id=lesson_id,
            telegram_id=telegram_id,
            text=text.strip(),
        )
        self.session.add(comment)
        await self.session.commit()
        await self.session.refresh(comment)
        return comment

    async def get_by_id(self, comment_id: int) -> LessonComment | None:
        """ID bo'yicha izohni olish."""
        stmt = select(LessonComment).where(LessonComment.id == comment_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_lesson_id(self, lesson_id: int) -> list[LessonComment]:
        """Dars bo'yicha barcha izohlarni olish."""
        stmt = (
            select(LessonComment)
            .where(LessonComment.lesson_id == lesson_id)
            .order_by(LessonComment.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def delete(self, comment_id: int) -> bool:
        """Dars izohini o'chirish."""
        comment = await self.get_by_id(comment_id)
        if not comment:
            return False
        await self.session.delete(comment)
        await self.session.commit()
        return True
