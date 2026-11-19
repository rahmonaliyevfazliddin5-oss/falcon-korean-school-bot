"""
Falcon Kibertexnology School - Excel eksport utiliti.
O'quvchilar, baholar va davomat ma'lumotlarini chiroyli formatlangan
Excel (.xlsx) faylga eksport qiladi.
"""

import os
from datetime import datetime

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Attendance, Grade, Lesson, Student


async def generate_school_excel_report(session: AsyncSession) -> str:
    """
    Barcha o'quvchilar, baholar va davomat ma'lumotlarini Excel faylga yozadi
    va yaratilgan faylning to'liq yo'lini qaytaradi.
    """
    wb = openpyxl.Workbook()

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")

    # 1. O'quvchilar varag'i
    ws_students = wb.active
    ws_students.title = "O'quvchilar"
    st_headers = [
        "ID",
        "F.I.SH",
        "Daraja",
        "Guruh",
        "Ota-ona Telegram ID",
        "Holati",
        "Qo'shilgan sana",
    ]
    ws_students.append(st_headers)

    res_students = await session.execute(select(Student).order_by(Student.full_name.asc()))
    students = list(res_students.scalars().all())
    for s in students:
        ws_students.append(
            [
                s.id,
                s.full_name,
                s.level,
                s.group_name,
                s.parent_telegram_id or "Bog'lanmagan",
                "Faol" if s.is_active else "Chiqarilgan",
                s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
            ]
        )

    # 2. Baholar varag'i
    ws_grades = wb.create_sheet(title="Baholar")
    gr_headers = [
        "Baho ID",
        "O'quvchi F.I.SH",
        "Ball (1-5)",
        "Dars",
        "Izoh",
        "Qo'ygan Admin ID",
        "Sana",
    ]
    ws_grades.append(gr_headers)

    res_grades = await session.execute(
        select(Grade, Student.full_name, Lesson.title)
        .join(Student, Grade.student_id == Student.id)
        .outerjoin(Lesson, Grade.lesson_id == Lesson.id)
        .order_by(Grade.created_at.desc())
    )
    for gr, st_name, lsn_title in res_grades.all():
        ws_grades.append(
            [
                gr.id,
                st_name,
                gr.score,
                lsn_title or "Mustaqil baholash",
                gr.comment or "",
                gr.created_by,
                gr.created_at.strftime("%Y-%m-%d %H:%M") if gr.created_at else "",
            ]
        )

    # 3. Davomat varag'i
    ws_att = wb.create_sheet(title="Davomat")
    att_headers = ["Davomat ID", "O'quvchi F.I.SH", "Dars mavzusi", "Holat", "Sana"]
    ws_att.append(att_headers)

    res_att = await session.execute(
        select(Attendance, Student.full_name, Lesson.title)
        .join(Student, Attendance.student_id == Student.id)
        .join(Lesson, Attendance.lesson_id == Lesson.id)
        .order_by(Attendance.created_at.desc())
    )
    for att, st_name, lsn_title in res_att.all():
        ws_att.append(
            [
                att.id,
                st_name,
                lsn_title,
                att.status.upper(),
                att.created_at.strftime("%Y-%m-%d %H:%M") if att.created_at else "",
            ]
        )

    # Formatlash va ustun kengliklarini avtomatik to'g'irlash
    for ws in [ws_students, ws_grades, ws_att]:
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # Faylni saqlash
    export_dir = os.path.join(os.getcwd(), "exports")
    os.makedirs(export_dir, exist_ok=True)
    filename = f"falcon_school_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(export_dir, filename)
    wb.save(filepath)

    return filepath
