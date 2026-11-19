"""
Falcon Kibertexnology School - O'qituvchi izohlari ombori (TeacherNoteRepository).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import TeacherNote


class TeacherNoteRepository:
    """O'qituvchi izohlari uchun CRUD amallari."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, student_id: int, text: str, created_by: int) -> TeacherNote:
        """O'quvchiga yangi izoh qo'shish."""
        note = TeacherNote(
            student_id=student_id,
            text=text.strip(),
            created_by=created_by,
        )
        self.session.add(note)
        await self.session.commit()
        await self.session.refresh(note)
        return note

    async def get_by_id(self, note_id: int) -> TeacherNote | None:
        """ID bo'yicha izohni olish."""
        stmt = select(TeacherNote).where(TeacherNote.id == note_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_student_id(self, student_id: int, limit: int = 20) -> list[TeacherNote]:
        """O'quvchiga tegishli oxirgi izohlarni olish."""
        stmt = (
            select(TeacherNote)
            .where(TeacherNote.student_id == student_id)
            .order_by(TeacherNote.created_at.desc(), TeacherNote.id.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update(self, note_id: int, text: str) -> TeacherNote | None:
        """Izoh matnini tahrirlash."""
        note = await self.get_by_id(note_id)
        if not note:
            return None
        note.text = text.strip()
        await self.session.commit()
        await self.session.refresh(note)
        return note

    async def delete(self, note_id: int) -> bool:
        """Izohni o'chirish."""
        note = await self.get_by_id(note_id)
        if not note:
            return False
        await self.session.delete(note)
        await self.session.commit()
        return True
