"""
Falcon Kibertexnology School - Maktab ma'lumotlari ombori (SchoolInfoRepository).
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import SchoolInfo


class SchoolInfoRepository:
    """Maktab haqidagi matnlarni olish va tahrirlash ombori."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_info(self, key: str = "about_school") -> str:
        """Kalit bo'yicha ma'lumot matnini olish."""
        stmt = select(SchoolInfo).where(SchoolInfo.key == key)
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()
        if record:
            return record.content
        return "Falcon Kibertexnology School — Zamonaviy koreys tili maktabi!"

    async def set_info(self, key: str, content: str) -> SchoolInfo:
        """Kalit bo'yicha ma'lumot matnini yangilash yoki yaratish."""
        stmt = select(SchoolInfo).where(SchoolInfo.key == key)
        res = await self.session.execute(stmt)
        record = res.scalar_one_or_none()
        if record:
            record.content = content.strip()
        else:
            record = SchoolInfo(key=key, content=content.strip())
            self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record
