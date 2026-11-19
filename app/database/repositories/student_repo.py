"""
Falcon Kibertexnology School - O'quvchilar ombori (StudentRepository).
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Student


class StudentRepository:
    """O'quvchilar modeli uchun CRUD operatsiyalari."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        full_name: str,
        level: str,
        group_name: str,
        parent_telegram_id: int | None = None,
        user_telegram_id: int | None = None,
    ) -> Student:
        """Yangi o'quvchi qo'shish."""
        student = Student(
            full_name=full_name.strip(),
            level=level.strip(),
            group_name=group_name.strip(),
            parent_telegram_id=parent_telegram_id,
            user_telegram_id=user_telegram_id,
            is_active=True,
        )
        self.session.add(student)
        await self.session.commit()
        await self.session.refresh(student)
        return student

    async def get_by_id(self, student_id: int) -> Student | None:
        """ID bo'yicha o'quvchini olish."""
        stmt = select(Student).where(Student.id == student_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_parent_telegram_id(self, parent_telegram_id: int) -> list[Student]:
        """Ota-onaning Telegram ID si bo'yicha bog'langan faol o'quvchilarni olish."""
        stmt = (
            select(Student)
            .where(
                Student.parent_telegram_id == parent_telegram_id,
                Student.is_active == True,
            )
            .order_by(Student.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user_telegram_id(self, user_telegram_id: int) -> Student | None:
        """O'quvchining o'z Telegram ID si bo'yicha o'quvchini olish."""
        stmt = select(Student).where(
            Student.user_telegram_id == user_telegram_id,
            Student.is_active == True,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_students(
        self, offset: int = 0, limit: int = 8, search_query: str | None = None
    ) -> tuple[list[Student], int]:
        """
        Faol o'quvchilar ro'yxatini sahifalash va qidiruv bilan olish.
        Natijada (o'quvchilar ro'yxati, umumiy_soni) qaytadi.
        """
        base_query = select(Student).where(Student.is_active == True)
        count_query = select(func.count(Student.id)).where(Student.is_active == True)

        if search_query:
            term = f"%{search_query.strip().lower()}%"
            base_query = base_query.where(func.lower(Student.full_name).like(term))
            count_query = count_query.where(func.lower(Student.full_name).like(term))

        # Umumiy soni
        total_res = await self.session.execute(count_query)
        total_count = total_res.scalar() or 0

        # Sahifadagi ro'yxat
        paginated_query = base_query.order_by(Student.full_name.asc()).offset(offset).limit(limit)
        items_res = await self.session.execute(paginated_query)
        students = list(items_res.scalars().all())

        return students, total_count

    async def get_all_active(self) -> list[Student]:
        """Barcha faol o'quvchilar ro'yxati."""
        stmt = select(Student).where(Student.is_active == True).order_by(Student.full_name.asc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def update(self, student_id: int, **kwargs: object) -> Student | None:
        """O'quvchi ma'lumotlarini yangilash."""
        student = await self.get_by_id(student_id)
        if not student:
            return None
        for key, value in kwargs.items():
            if hasattr(student, key):
                setattr(student, key, value)
        await self.session.commit()
        await self.session.refresh(student)
        return student

    async def soft_delete(self, student_id: int) -> bool:
        """O'quvchini chiqarib tashlash (is_active=False qilib saqlab qolish)."""
        student = await self.get_by_id(student_id)
        if not student:
            return False
        student.is_active = False
        await self.session.commit()
        return True

    async def link_parent(self, student_id: int, parent_telegram_id: int) -> Student | None:
        """O'quvchiga ota-ona Telegram ID sini bog'lash."""
        return await self.update(student_id, parent_telegram_id=parent_telegram_id)

    async def delete_permanent(self, student_id: int) -> bool:
        """O'quvchini bazadan butunlay o'chirish (testlar uchun)."""
        student = await self.get_by_id(student_id)
        if not student:
            return False
        await self.session.delete(student)
        await self.session.commit()
        return True
