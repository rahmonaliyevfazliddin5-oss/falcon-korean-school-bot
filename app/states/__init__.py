"""
Falcon Kibertexnology School - Aiogram FSM (Finite State Machine) holatlari.
"""

from aiogram.fsm.state import State, StatesGroup


class AdminLoginStates(StatesGroup):
    """Admin tizimiga kirish FSM holati."""

    waiting_for_admin_id = State()


class StudentAddStates(StatesGroup):
    """O'quvchi qo'shish FSM holatlari."""

    waiting_for_name = State()
    waiting_for_level = State()
    waiting_for_group = State()
    waiting_for_parent_id = State()
    confirm = State()


class StudentSearchStates(StatesGroup):
    """O'quvchini qidirish FSM holati."""

    waiting_for_query = State()


class StudentLinkParentStates(StatesGroup):
    """Ota-ona Telegram ID sini bog'lash FSM holati."""

    waiting_for_parent_id = State()


class GradingStates(StatesGroup):
    """Baholash FSM holatlari."""

    waiting_for_comment = State()


class AttendanceStates(StatesGroup):
    """Davomat belgilash FSM holatlari."""

    marking = State()


class NoteStates(StatesGroup):
    """O'qituvchi izohi FSM holatlari."""

    waiting_for_text = State()
    editing_text = State()


class LessonAddStates(StatesGroup):
    """Yangi dars yaratish FSM holatlari."""

    waiting_for_title = State()
    waiting_for_time = State()


class LessonCommentStates(StatesGroup):
    """Darsga izoh qoldirish FSM holati."""

    waiting_for_comment = State()


class SchoolInfoStates(StatesGroup):
    """Maktab haqidagi matnni tahrirlash FSM holati."""

    waiting_for_text = State()
