"""
Falcon Kibertexnology School - Davomat ombori (AttendanceRepository).
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Attendance, Student


class AttendanceRepository:
    """Davomat uchun CRUD va statistika amallari."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_or_update(self, student_id: int, lesson_id: int, status: str) -> Attendance:
        """
        Davomatni belgilaydi yoki mavjud bo'lsa yangilaydi (dublikat yaratmaydi).
        """
        existing = await self.get_by_student_and_lesson(student_id, lesson_id)
        if existing:
            existing.status = status
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        attendance = Attendance(
            student_id=student_id,
            lesson_id=lesson_id,
            status=status,
        )
        self.session.add(attendance)
        await self.session.commit()
        await self.session.refresh(attendance)
        return attendance

    async def get_by_id(self, attendance_id: int) -> Attendance | None:
        """ID bo'yicha davomat yozuvini olish."""
        stmt = select(Attendance).where(Attendance.id == attendance_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_student_and_lesson(self, student_id: int, lesson_id: int) -> Attendance | None:
        """O'quvchi va dars bo'yicha davomat yozuvini olish."""
        stmt = select(Attendance).where(
            Attendance.student_id == student_id,
            Attendance.lesson_id == lesson_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_lesson_id(self, lesson_id: int) -> list[Attendance]:
        """Dars bo'yicha barcha davomat yozuvlarini olish."""
        stmt = (
            select(Attendance)
            .where(Attendance.lesson_id == lesson_id)
            .order_by(Attendance.id.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_by_student_id(self, student_id: int) -> list[Attendance]:
        """O'quvchi bo'yicha barcha davomat yozuvlarini olish."""
        stmt = (
            select(Attendance)
            .where(Attendance.student_id == student_id)
            .order_by(Attendance.created_at.desc(), Attendance.id.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def bulk_mark_lesson(self, lesson_id: int, student_ids: list[int], status: str) -> int:
        """
        Dars uchun ko'rsatilgan barcha o'quvchilarga bir xil holat (masalan: 'keldi') qo'yish.
        """
        count = 0
        for s_id in student_ids:
            await self.create_or_update(student_id=s_id, lesson_id=lesson_id, status=status)
            count += 1
        return count

    async def get_student_stats(self, student_id: int) -> dict[str, Any]:
        """
        O'quvchining davomat statistikasini hisoblash:
        qatnashgan (keldi), qoldirgan (kelmadi), sababli, umumiy, foiz.
        """
        stmt = select(Attendance).where(Attendance.student_id == student_id)
        res = await self.session.execute(stmt)
        records = list(res.scalars().all())

        total = len(records)
        attended = sum(1 for r in records if r.status == "keldi")
        missed = sum(1 for r in records if r.status == "kelmadi")
        excused = sum(1 for r in records if r.status == "sababli")

        if total == 0:
            percentage = 0.0
        else:
            percentage = round((attended / total) * 100.0, 1)

        return {
            "student_id": student_id,
            "attended": attended,
            "missed": missed,
            "excused": excused,
            "total": total,
            "percentage": percentage,
        }

    async def get_top_absent_students(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Eng ko'p dars qoldirgan (kelmadi holati ko'p bo'lgan) faol o'quvchilar ro'yxati.
        """
        stmt = (
            select(
                Student.id,
                Student.full_name,
                Student.group_name,
                func.count(Attendance.id).label("missed_count"),
            )
            .join(Attendance, Attendance.student_id == Student.id)
            .where(
                Attendance.status == "kelmadi",
                Student.is_active == True,
            )
            .group_by(Student.id, Student.full_name, Student.group_name)
            .order_by(func.count(Attendance.id).desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        rows = res.all()
        return [
            {
                "student_id": row[0],
                "full_name": row[1],
                "group_name": row[2],
                "missed_count": row[3],
            }
            for row in rows
        ]

    async def delete(self, attendance_id: int) -> bool:
        """Davomat yozuvini o'chirish."""
        rec = await self.get_by_id(attendance_id)
        if not rec:
            return False
        await self.session.delete(rec)
        await self.session.commit()
        return True
