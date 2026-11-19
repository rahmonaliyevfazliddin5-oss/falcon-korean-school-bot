"""
Falcon Kibertexnology School - Klaviaturalar va Rejalashtiruvchi (Scheduler) testlari.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.models import Lesson, Student, TeacherNote, User
from app.database.session import init_db
from app.keyboards.builders import (
    get_attendance_marking_keyboard,
    get_delete_confirm_keyboard,
    get_grading_keyboard,
    get_lesson_control_keyboard,
    get_main_menu_keyboard,
    get_notes_keyboard,
    get_student_card_keyboard,
    get_students_pagination_keyboard,
)
from app.utils.scheduler import (
    check_and_send_lesson_reminders,
    setup_background_scheduler,
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


def test_keyboards_generation() -> None:
    """Barcha klaviatura generatorlarini to'liq sinab ko'rish."""
    # 1. Main menu
    adm_kb = get_main_menu_keyboard("admin")
    assert len(adm_kb.keyboard) == 4
    user_kb = get_main_menu_keyboard("user")
    assert len(user_kb.keyboard) == 3

    # 2. Student card
    card_kb = get_student_card_keyboard(10)
    assert len(card_kb.inline_keyboard) == 4

    # 3. Delete confirm
    del_kb = get_delete_confirm_keyboard(10)
    assert len(del_kb.inline_keyboard) == 1

    # 4. Grading
    grd_kb = get_grading_keyboard(10)
    assert len(grd_kb.inline_keyboard) == 2

    # 5. Pagination
    st1 = Student(id=1, full_name="A", level="bosh", group_name="G1")
    st2 = Student(id=2, full_name="B", level="bosh", group_name="G1")
    pag_kb = get_students_pagination_keyboard(
        [st1, st2], page=0, total_count=10, page_size=2, search="test"
    )
    assert len(pag_kb.inline_keyboard) >= 3

    # 6. Attendance marking
    att_kb = get_attendance_marking_keyboard(
        lesson_id=1, students=[st1], current_statuses={1: "keldi"}
    )
    assert len(att_kb.inline_keyboard) == 2

    # 7. Notes keyboard
    note = TeacherNote(id=1, student_id=1, text="Izoh matni", created_by=777)
    notes_kb = get_notes_keyboard(student_id=1, notes=[note])
    assert len(notes_kb.inline_keyboard) == 3

    # 8. Lesson control
    lsn = Lesson(id=1, title="Dars", starts_at=datetime.now(UTC))
    active_lsn_kb = get_lesson_control_keyboard(active_lesson=lsn)
    assert len(active_lsn_kb.inline_keyboard) == 1
    inactive_lsn_kb = get_lesson_control_keyboard(active_lesson=None)
    assert len(inactive_lsn_kb.inline_keyboard) == 3


@pytest.mark.asyncio
async def test_scheduler_functions(
    async_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scheduler eslatma yuborish funksiyasi tekshiruvi."""
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()

    # Dars va foydalanuvchi qo'shamiz (10 daqiqadan keyin boshlanadigan dars)
    starts = datetime.now(UTC) + timedelta(minutes=10)
    lesson = Lesson(
        title="Tez kunda boshlanuvchi dars",
        starts_at=starts,
        status="rejalashtirilgan",
    )
    user = User(telegram_id=999888, full_name="O'quvchi", role="parent", is_active=True)
    async_session.add_all([lesson, user])
    await async_session.commit()

    # Sessionmaker ni almashtirish
    session_factory = async_sessionmaker(
        bind=async_session.bind, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr("app.utils.scheduler.async_session_maker", session_factory)

    await check_and_send_lesson_reminders(mock_bot)
    assert mock_bot.send_message.call_count == 1
    assert "Dars eslatmasi" in mock_bot.send_message.call_args[1]["text"]

    # Scheduler instansiyasini sozlash
    sched = setup_background_scheduler(mock_bot)
    assert sched is not None
    assert len(sched.get_jobs()) == 2
