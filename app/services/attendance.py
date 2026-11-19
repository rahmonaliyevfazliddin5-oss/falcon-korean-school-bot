"""
Falcon Kibertexnology School - Davomat xizmati (AttendanceService).
Dars davomatini belgilash, statistikani hisoblash va hisobotlar tayyorlash.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Attendance
from app.database.repositories.attendance_repo import AttendanceRepository


class AttendanceService:
    """Davomat jarayonlarini boshqarish xizmati."""

    VALID_STATUSES = {"keldi", "kelmadi", "sababli"}

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AttendanceRepository(session)

    async def mark_attendance(self, student_id: int, lesson_id: int, status: str) -> Attendance:
        """
        O'quvchi davomatini belgilash yoki yangilash.
        status: 'keldi', 'kelmadi', 'sababli'
        """
        status_clean = status.strip().lower()
        if status_clean not in self.VALID_STATUSES:
            raise ValueError(
                f"Noto'g'ri holat: {status}. Ruxsat etilgan: {', '.join(self.VALID_STATUSES)}"
            )
        return await self.repo.create_or_update(
            student_id=student_id, lesson_id=lesson_id, status=status_clean
        )

    async def mark_all_present(self, lesson_id: int, student_ids: list[int]) -> int:
        """Darsdagi barcha o'quvchilarni 'keldi' deb belgilash."""
        return await self.repo.bulk_mark_lesson(
            lesson_id=lesson_id, student_ids=student_ids, status="keldi"
        )

    async def get_student_stats(self, student_id: int) -> dict[str, Any]:
        """
        O'quvchi davomat statistikasini olish:
        qatnashgan, qoldirgan, sababli, umumiy, foiz.
        """
        return await self.repo.get_student_stats(student_id)

    async def get_top_absent_report(self, limit: int = 10) -> list[dict[str, Any]]:
        """Eng ko'p dars qoldirgan o'quvchilar hisoboti."""
        return await self.repo.get_top_absent_students(limit=limit)

    async def get_lesson_attendance(self, lesson_id: int) -> list[Attendance]:
        """Dars bo'yicha barcha davomat yozuvlari."""
        return await self.repo.get_by_lesson_id(lesson_id)
