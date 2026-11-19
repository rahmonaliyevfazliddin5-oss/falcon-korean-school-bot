"""
Falcon Kibertexnology School - Foydalanuvchilar ombori (UserRepository).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


class UserRepository:
    """Foydalanuvchilar uchun CRUD operatsiyalari."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Telegram ID bo'yicha foydalanuvchini olish."""
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        """Baza ID bo'yicha foydalanuvchini olish."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_update(
        self, telegram_id: int, full_name: str, role: str = "parent"
    ) -> User:
        """
        Foydalanuvchi mavjud bo'lsa ma'lumotlarini yangilaydi, aks holda yangi yaratadi.
        """
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.full_name = full_name
            await self.session.commit()
            await self.session.refresh(user)
            return user

        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            role=role,
            is_active=True,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def set_role(self, telegram_id: int, role: str) -> User | None:
        """Foydalanuvchi rolini o'zgartirish."""
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.role = role
            await self.session.commit()
            await self.session.refresh(user)
        return user

    async def get_all_users(self) -> list[User]:
        """Barcha foydalanuvchilarni olish."""
        stmt = select(User).order_by(User.id.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, user_id: int) -> bool:
        """Foydalanuvchini bazadan to'liq o'chirish."""
        user = await self.get_by_id(user_id)
        if user:
            await self.session.delete(user)
            await self.session.commit()
            return True
        return False
