"""
Falcon Kibertexnology School - Aiogram CallbackData fabriklari.
Barcha inline tugmalar CallbackData orqali xavfsiz va tiplashtirilgan holda boshqariladi.
Admin va Foydalanuvchi prefikslari ajratilgan.
"""

from aiogram.filters.callback_data import CallbackData

# ==================== ADMIN CALLBACKS ====================


class NavCallback(CallbackData, prefix="nav"):
    """Admin sahifalash va navigatsiya callbacki."""

    target: str
    page: int = 0
    search: str | None = None


class StudentActionCallback(CallbackData, prefix="st_act"):
    """Admin o'quvchi kartochkasi amallari (Baholash, Davomat, Izoh, Chiqarish, Bog'lash)."""

    action: str  # view, grade, att, note, delete_confirm, delete_do, link_parent
    student_id: int


class GradeCallback(CallbackData, prefix="grd"):
    """Admin baho qo'yish callbacki."""

    action: str  # score, cancel
    student_id: int
    score: int


class AttendanceCallback(CallbackData, prefix="att"):
    """Admin davomat belgilash callbacki."""

    action: str  # select_lesson, toggle, mark_all, finish
    lesson_id: int
    student_id: int = 0
    status: str = ""  # keldi, kelmadi, sababli


class NoteActionCallback(CallbackData, prefix="note"):
    """Admin o'qituvchi izohlari callbacki."""

    action: str  # add, edit, delete, list, view_single
    student_id: int
    note_id: int = 0


class LessonControlCallback(CallbackData, prefix="lsn"):
    """Admin video darslarni boshqarish callbacki."""

    action: str  # create, start_choose, do_start, end, view_comments
    lesson_id: int = 0


class AdminMenuCallback(CallbackData, prefix="adm"):
    """Admin menyusi callbacki."""

    section: str  # students, grading, attendance, notes, lessons, rating, stats


# ==================== ODDIY FOYDALANUVCHI CALLBACKS ====================


class UserNavCallback(CallbackData, prefix="usr_nav"):
    """Foydalanuvchi sahifalash callbacki (o'quvchilar va reyting)."""

    target: str  # students, students_noop, rating, rating_noop, search_student
    page: int = 0
    search: str | None = None


class UserStudentCallback(CallbackData, prefix="usr_st"):
    """Foydalanuvchi o'quvchi ko'rish callbacki (kartochka, izohlar, davomat)."""

    action: str  # view, notes, attendance, back
    student_id: int


class UserLessonCallback(CallbackData, prefix="usr_lsn"):
    """Foydalanuvchi dars callbacki (izoh qoldirish)."""

    action: str  # comment, view
    lesson_id: int = 0
