"""
Falcon Kibertexnology School - Handlerlar birlik (Unit) testlari.
Common, Admin va Parent handlerlarining barcha tarmoqlari sinovdan o'tkaziladi.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, Message
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database.models import Lesson, Student, User
from app.database.session import init_db
from app.handlers.admin.attendance import (
    finish_attendance_marking,
    handle_attendance_menu,
    mark_all_students_present,
    open_lesson_attendance,
)
from app.handlers.admin.grading import (
    handle_grading_menu,
    handle_score_choice,
    prompt_grade_selection,
    save_grade_without_comment,
)
from app.handlers.admin.lessons import (
    handle_video_lessons_menu,
    process_lesson_time,
    process_lesson_title,
    start_lesson_creation,
)
from app.handlers.admin.notes import (
    handle_notes_menu,
    open_student_notes,
    prompt_add_note,
    save_new_note,
)
from app.handlers.admin.stats import handle_admin_rating, handle_admin_stats
from app.handlers.admin.students import (
    confirm_delete_student,
    execute_soft_delete,
    finalize_add_student,
    handle_students_menu_click,
    process_link_parent_id,
    process_student_group,
    process_student_level_callback,
    process_student_name,
    process_student_search_query,
    prompt_link_parent,
    skip_parent_id_callback,
    start_add_student,
    start_student_search,
)
from app.handlers.common import (
    cmd_admin,
    cmd_checkgroup,
    cmd_export,
    cmd_start,
    process_admin_id_input,
)
from app.handlers.parent.dashboard import (
    handle_about_school,
    handle_current_lesson,
    handle_my_attendance,
    handle_my_child,
    handle_my_grades,
    handle_teacher_notes,
    handle_user_rating,
    prompt_lesson_comment,
    save_user_lesson_comment,
)
from app.keyboards.callbacks import (
    AttendanceCallback,
    GradeCallback,
    LessonControlCallback,
    NoteActionCallback,
    StudentActionCallback,
)


@pytest.fixture
async def async_session() -> AsyncSession:
    """Xotiradagi test bazasi fixture'i."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    await init_db(target_engine=engine)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


def make_mock_message(
    user_id: int = 12345, text: str = "", full_name: str = "Test User"
) -> Message:
    """Mock aiogram Message yaratish yordamchisi."""
    msg = MagicMock(spec=Message)
    msg.from_user = TelegramUser(id=user_id, is_bot=False, first_name="Test", full_name=full_name)
    msg.text = text
    msg.answer = AsyncMock()
    msg.answer_document = AsyncMock()
    msg.edit_text = AsyncMock()
    msg.edit_reply_markup = AsyncMock()
    return msg


def make_mock_callback(user_id: int = 12345, data: str = "") -> CallbackQuery:
    """Mock aiogram CallbackQuery yaratish yordamchisi."""
    cb = MagicMock(spec=CallbackQuery)
    cb.from_user = TelegramUser(id=user_id, is_bot=False, first_name="Test", full_name="Test User")
    cb.data = data
    cb.answer = AsyncMock()
    cb.message = make_mock_message(user_id=user_id)
    return cb


class MockFSMContext:
    """Ishonchli xotiradagi FSM kontekst imitatori."""

    def __init__(self, initial: dict | None = None) -> None:
        self._data: dict = initial.copy() if initial else {}
        self.set_state = AsyncMock()
        self.clear = AsyncMock(side_effect=self._clear)
        self.update_data = AsyncMock(side_effect=self._update)
        self.get_data = AsyncMock(side_effect=self._get)

    def _clear(self) -> None:
        self._data.clear()

    def _update(self, **kwargs: object) -> dict:
        self._data.update(kwargs)
        return self._data

    def _get(self) -> dict:
        return self._data.copy()


# ==================== COMMON HANDLER TESTS ====================
@pytest.mark.asyncio
async def test_cmd_start_and_admin(async_session: AsyncSession) -> None:
    """/start va /admin komandalari unit testi."""
    msg = make_mock_message(101, "/start")
    user = User(telegram_id=101, full_name="User", role="parent")
    state = MockFSMContext()

    # /start
    await cmd_start(msg, state, user, async_session)  # type: ignore[arg-type]
    assert msg.answer.call_count == 1
    assert "Falcon Kibertexnology School" in msg.answer.call_args[1]["text"]

    # /admin (foydalanuvchi admin bo'lmaganda ID so'raydi)
    msg_admin = make_mock_message(101, "/admin")
    await cmd_admin(msg_admin, state, user)  # type: ignore[arg-type]
    assert state.set_state.call_count == 1

    # /admin (allaqachon admin bo'lganda)
    admin_user = User(telegram_id=101, full_name="Admin", role="admin")
    await cmd_admin(msg_admin, state, admin_user)  # type: ignore[arg-type]
    assert "allaqachon administrator" in msg_admin.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_process_admin_id_input(async_session: AsyncSession) -> None:
    """Admin ID kiritilganda tekshirish."""
    state = MockFSMContext()

    # Son kiritilmaganda
    msg_bad = make_mock_message(101, "abc")
    await process_admin_id_input(msg_bad, state, async_session)  # type: ignore[arg-type]
    assert "faqat butun son" in msg_bad.answer.call_args[0][0]

    # To'g'ri admin ID
    settings.ADMIN_IDS = "101"
    msg_ok = make_mock_message(101, "101")
    await process_admin_id_input(msg_ok, state, async_session)  # type: ignore[arg-type]
    assert "Tabriklaymiz" in msg_ok.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_cmd_export_and_checkgroup(async_session: AsyncSession) -> None:
    """/export va /checkgroup buyruqlari unit testi."""
    parent_user = User(telegram_id=201, full_name="Parent", role="parent")
    admin_user = User(telegram_id=101, full_name="Admin", role="admin")

    msg = make_mock_message(101)

    # Parent /export -> rad etiladi
    await cmd_export(msg, parent_user, async_session)
    assert "faqat administratorlar" in msg.answer.call_args[0][0]

    # Admin /export -> fayl jo'natadi
    await cmd_export(msg, admin_user, async_session)
    assert msg.answer_document.call_count == 1

    # /checkgroup parent -> rad
    mock_bot = MagicMock()
    await cmd_checkgroup(msg, mock_bot, parent_user, async_session)
    assert "faqat administratorlar" in msg.answer.call_args[0][0]

    # /checkgroup admin
    await cmd_checkgroup(msg, mock_bot, admin_user, async_session)
    assert "Guruh xavfsizligi" in msg.answer.call_args[0][0]


# ==================== ADMIN STUDENTS TESTS ====================
@pytest.mark.asyncio
async def test_admin_students_handlers(async_session: AsyncSession) -> None:
    """Admin o'quvchilar boshqaruvi handlerlari."""
    state = MockFSMContext()

    # Ro'yxat
    msg = make_mock_message(101, "👥 O'quvchilar")
    await handle_students_menu_click(msg, async_session, state)  # type: ignore[arg-type]
    assert msg.answer.call_count == 1

    # Qidiruv
    cb = make_mock_callback(101)
    await start_student_search(cb, state)  # type: ignore[arg-type]
    assert state.set_state.call_count == 1

    msg_q = make_mock_message(101, "Ali")
    await process_student_search_query(msg_q, state, async_session)  # type: ignore[arg-type]
    assert msg_q.answer.call_count == 1

    # O'quvchi qo'shish FSM oqimi
    await start_add_student(cb, state)  # type: ignore[arg-type]
    msg_name = make_mock_message(101, "Bobur Aliyev")
    await process_student_name(msg_name, state)  # type: ignore[arg-type]

    cb_lvl = make_mock_callback(101, "level:o'rta")
    await process_student_level_callback(cb_lvl, state)  # type: ignore[arg-type]

    msg_grp = make_mock_message(101, "KOR-200")
    await process_student_group(msg_grp, state)  # type: ignore[arg-type]

    await skip_parent_id_callback(cb, state)  # type: ignore[arg-type]

    # Tasdiqlash
    await state.update_data(full_name="Bobur Aliyev", level="o'rta", group_name="KOR-200")
    await finalize_add_student(cb, state, async_session)  # type: ignore[arg-type]
    assert "muvaffaqiyatli qo'shildi" in cb.message.edit_text.call_args[0][0]

    # O'quvchini chiqarish (soft delete)
    st_act = StudentActionCallback(action="delete_confirm", student_id=1)
    await confirm_delete_student(cb, st_act)
    st_del = StudentActionCallback(action="delete_do", student_id=1)
    await execute_soft_delete(cb, st_del, async_session)
    assert "muvaffaqiyatli chiqarib tashlandi" in cb.message.edit_text.call_args[0][0]

    # Ota-ona ID bog'lash
    st_link = StudentActionCallback(action="link_parent", student_id=1)
    await prompt_link_parent(cb, st_link, state)  # type: ignore[arg-type]
    await state.update_data(student_id=1)
    msg_pid = make_mock_message(101, "888777")
    await process_link_parent_id(msg_pid, state, async_session)  # type: ignore[arg-type]
    assert msg_pid.answer.call_count == 1


# ==================== ADMIN GRADING TESTS ====================
@pytest.mark.asyncio
async def test_admin_grading_handlers(async_session: AsyncSession) -> None:
    """Admin baholash handlerlari."""
    state = MockFSMContext()
    msg = make_mock_message(101)

    # O'quvchi qo'shamiz
    st = Student(full_name="Baholash Test", level="o'rta", group_name="G1", is_active=True)
    async_session.add(st)
    await async_session.commit()

    # Baholash menyusi
    await handle_grading_menu(msg, async_session, state)  # type: ignore[arg-type]
    assert msg.answer.call_count == 1

    cb = make_mock_callback(101)
    st_act = StudentActionCallback(action="grade", student_id=st.id)
    await prompt_grade_selection(cb, st_act, async_session)

    grd_cb = GradeCallback(action="score", student_id=st.id, score=5)
    await handle_score_choice(cb, grd_cb, state)  # type: ignore[arg-type]

    # Izohsiz saqlash
    await state.update_data(student_id=st.id, score=5)
    await save_grade_without_comment(cb, state, async_session)  # type: ignore[arg-type]
    assert "muvaffaqiyatli saqlandi" in cb.message.edit_text.call_args[0][0]


# ==================== ADMIN ATTENDANCE TESTS ====================
@pytest.mark.asyncio
async def test_admin_attendance_handlers(async_session: AsyncSession) -> None:
    """Admin davomat handlerlari."""
    msg = make_mock_message(101)

    # Dars yaratamiz
    lesson = Lesson(
        title="Dars 1",
        starts_at=datetime.now(UTC),
        status="rejalashtirilgan",
    )
    async_session.add(lesson)
    await async_session.commit()

    await handle_attendance_menu(msg, async_session)
    assert msg.answer.call_count == 1

    cb = make_mock_callback(101)
    att_cb = AttendanceCallback(action="select_lesson", lesson_id=lesson.id)
    await open_lesson_attendance(cb, att_cb, async_session)

    # Hammasi keldi
    cb_all = make_mock_callback(101)
    att_all = AttendanceCallback(action="mark_all", lesson_id=lesson.id)
    await mark_all_students_present(cb_all, att_all, async_session)
    assert cb_all.answer.call_count == 1

    # Yakunlash
    cb_fin = make_mock_callback(101)
    await finish_attendance_marking(cb_fin)
    assert "muvaffaqiyatli saqlandi" in cb_fin.message.edit_text.call_args[0][0]


# ==================== ADMIN NOTES & LESSONS & STATS ====================
@pytest.mark.asyncio
async def test_admin_notes_lessons_stats(async_session: AsyncSession) -> None:
    """Admin izohlar, video darslar va statistika handlerlari."""
    state = MockFSMContext()
    cb = make_mock_callback(101)

    # O'quvchi qo'shamiz
    st = Student(full_name="Izoh O'quvchi", level="o'rta", group_name="KOR-N", is_active=True)
    async_session.add(st)
    await async_session.commit()

    # Izohlar menyusi
    msg_notes = make_mock_message(101)
    await handle_notes_menu(msg_notes, async_session)
    assert msg_notes.answer.call_count == 1

    # O'quvchi izohlarini ochish
    st_note_act = StudentActionCallback(action="note", student_id=st.id)
    await open_student_notes(cb, st_note_act, async_session)
    assert cb.message.edit_text.call_count == 1

    # Izoh qo'shish FSM
    note_add_act = NoteActionCallback(action="add", student_id=st.id)
    await prompt_add_note(cb, note_add_act, state)  # type: ignore[arg-type]
    await state.update_data(student_id=st.id)
    msg_note_text = make_mock_message(101, "Yaxshi o'zlashtirmoqda")
    await save_new_note(msg_note_text, state, async_session)  # type: ignore[arg-type]
    assert "muvaffaqiyatli saqlandi" in msg_note_text.answer.call_args[0][0]

    # Video darslar menyusi
    msg_lessons = make_mock_message(101)
    await handle_video_lessons_menu(msg_lessons, async_session)
    assert msg_lessons.answer.call_count == 1

    # Dars yaratish FSM
    await start_lesson_creation(cb, state)  # type: ignore[arg-type]
    msg_t = make_mock_message(101, "Yangi Koreys darsi")
    await process_lesson_title(msg_t, state)  # type: ignore[arg-type]
    msg_time = make_mock_message(101, "hozir")
    await process_lesson_time(msg_time, state, async_session)  # type: ignore[arg-type]
    assert "muvaffaqiyatli rejalashtirildi" in msg_time.answer.call_args[0][0]

    # Statistika va reyting
    msg_rating = make_mock_message(101)
    await handle_admin_rating(msg_rating, async_session)
    assert msg_rating.answer.call_count == 1

    msg_stats = make_mock_message(101)
    await handle_admin_stats(msg_stats, async_session)
    assert msg_stats.answer.call_count == 1


# ==================== PARENT HANDLER TESTS ====================
@pytest.mark.asyncio
async def test_parent_dashboard_handlers(async_session: AsyncSession) -> None:
    """Ota-ona menyusi handlerlari."""
    msg = make_mock_message(201)
    user = User(telegram_id=201, full_name="Ota", role="parent")

    # Bog'lanmagan ota-ona tekshiruvi
    await handle_my_child(msg, async_session, user)
    assert "Sizga hali hech qaysi o'quvchi bog'lanmagan" in msg.answer.call_args[0][0]

    # O'quvchi bog'laymiz
    st = Student(
        full_name="Farzand Test",
        level="boshlang'ich",
        group_name="KOR-P",
        parent_telegram_id=201,
        is_active=True,
    )
    async_session.add(st)
    await async_session.commit()

    # Farzandim
    await handle_my_child(msg, async_session, user)
    assert "Farzandingiz ko'rsatkichlari" in msg.answer.call_args[0][0]

    # Baholarim
    await handle_my_grades(msg, async_session)
    assert "Baholar tarixi" in msg.answer.call_args[0][0]

    # Davomat
    await handle_my_attendance(msg, async_session)
    assert "Davomat hisoboti" in msg.answer.call_args[0][0]

    # O'qituvchi izohi
    await handle_teacher_notes(msg, async_session)
    assert "O'qituvchi izohlari" in msg.answer.call_args[0][0]

    # Reyting
    await handle_user_rating(msg, async_session)
    assert "Falcon Kibertexnology School" in msg.answer.call_args[0][0]

    # Hozirgi dars
    await handle_current_lesson(msg, async_session)
    assert "Falcon Kibertexnology School" in msg.answer.call_args[0][0]

    # Darsga izoh qoldirish
    state = MockFSMContext()
    cb_com = make_mock_callback(201)
    lsn_ctrl = LessonControlCallback(action="user_comment", lesson_id=1)
    await prompt_lesson_comment(cb_com, lsn_ctrl, state)  # type: ignore[arg-type]

    await state.update_data(lesson_id=1)
    msg_com = make_mock_message(201, "Dars ajoyib o'tdi")
    await save_user_lesson_comment(msg_com, state, async_session)  # type: ignore[arg-type]
    assert "tashakkur" in msg_com.answer.call_args[0][0].lower()

    # Maktab haqida
    await handle_about_school(msg, async_session)
    assert "Falcon Kibertexnology School" in msg.answer.call_args[0][0]
