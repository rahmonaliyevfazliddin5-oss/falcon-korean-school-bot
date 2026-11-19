"""
Falcon Kibertexnology School - Foydalanuvchi interfeysi va Xavfsizlik testlari.
Oddiy foydalanuvchi faqat o'qish huquqiga ega:
- O'quvchilar ro'yxati (sahifalash va qidiruv)
- O'quvchi kartochkasi (shaxsiy ma'lumotlarsiz)
- O'qituvchi izohlari va davomat ko'rsatkichlari
- TOP-10 va to'liq reyting (sahifalash)
- Hozirgi dars va darsga izoh qoldirish
- Maktab haqida ma'lumot
- Barcha admin callback_data lari oddiy foydalanuvchidan to'liq himoyalangan (show_alert=True)
- 20 parallel (konkurent) so'rovlar ostida bazaning barqaror ishlashi.
"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from sqlite3 import Connection as SQLite3Connection
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, Message
from aiogram.types import User as TelegramUser
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.models import Grade, Lesson, Student, TeacherNote
from app.database.session import init_db
from app.handlers.user.dashboard import (
    user_about_school,
    user_comment_menu_click,
    user_current_lesson,
    user_process_search_query,
    user_rating_full_callback,
    user_rating_menu_click,
    user_rating_top_callback,
    user_save_comment,
    user_start_search,
    user_students_menu_click,
    user_view_student_attendance,
    user_view_student_card,
    user_view_student_notes,
)
from app.keyboards.callbacks import (
    UserNavCallback,
    UserStudentCallback,
)
from app.middlewares.auth import DatabaseAndAuthMiddleware
from app.states import LessonCommentStates, StudentSearchStates


class MockFSMContext:
    """FSM holatlarini taqlid qiluvchi mock sinf."""

    def __init__(self) -> None:
        self.state_val: str | None = None
        self.data: dict = {}

    async def set_state(self, state: any = None) -> None:
        self.state_val = str(state)

    async def get_state(self) -> str | None:
        return self.state_val

    async def update_data(self, **kwargs: any) -> None:
        self.data.update(kwargs)

    async def get_data(self) -> dict:
        return self.data.copy()

    async def clear(self) -> None:
        self.state_val = None
        self.data.clear()


def make_mock_message(user_id: int = 12345, text: str = "") -> Message:
    """Mock Message obyekti."""
    msg = MagicMock(spec=Message)
    msg.from_user = TelegramUser(
        id=user_id, is_bot=False, first_name="TestUser", full_name="Test User"
    )
    msg.text = text
    msg.answer = AsyncMock()
    msg.edit_text = AsyncMock()
    return msg


def make_mock_callback(user_id: int = 12345, data: str = "") -> CallbackQuery:
    """Mock CallbackQuery obyekti."""
    cb = MagicMock(spec=CallbackQuery)
    cb.from_user = TelegramUser(
        id=user_id, is_bot=False, first_name="TestUser", full_name="Test User"
    )
    cb.data = data
    cb.message = MagicMock(spec=Message)
    cb.message.answer = AsyncMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


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


@pytest.mark.asyncio
async def test_user_students_flow_and_card(async_session: AsyncSession) -> None:
    """
    Foydalanuvchi o'quvchilar ro'yxatini ko'rishi, qidirishi va
    o'quvchi kartochkasini shaxsiy ma'lumotlarsiz tekshirishi.
    """
    # 1. Faol va nofaol o'quvchilar yaratamiz
    active_st = Student(
        full_name="Alisher Navoiy",
        level="yuqori",
        group_name="KOR-TOP",
        is_active=True,
    )
    inactive_st = Student(
        full_name="Bobur Mirzo",
        level="o'rta",
        group_name="KOR-MID",
        is_active=False,
    )
    async_session.add_all([active_st, inactive_st])
    await async_session.commit()
    await async_session.refresh(active_st)

    # 2. O'quvchilar ro'yxatini so'rash
    msg = make_mock_message(1001)
    state = MockFSMContext()
    await user_students_menu_click(msg, async_session, state)  # type: ignore[arg-type]
    assert msg.answer.call_count == 1
    call_args = msg.answer.call_args
    assert "Falcon Kibertexnology School" in call_args[0][0]
    assert "Jami faol o'quvchilar soni: **1 nafar**" in call_args[0][0]
    assert call_args[1].get("protect_content") is True

    # 3. Qidiruv boshlash
    cb_search = make_mock_callback(1001)
    await user_start_search(cb_search, state)  # type: ignore[arg-type]
    assert await state.get_state() == str(StudentSearchStates.waiting_for_query)

    # Qidiruv qisqa so'z
    msg_short = make_mock_message(1001, "a")
    await user_process_search_query(msg_short, state, async_session)  # type: ignore[arg-type]
    assert "kamida 2 ta harf" in msg_short.answer.call_args[0][0]

    # Qidiruv to'g'ri so'z
    msg_query = make_mock_message(1001, "Alisher")
    await user_process_search_query(msg_query, state, async_session)  # type: ignore[arg-type]
    assert "Alisher" in msg_query.answer.call_args[0][0]

    # Qidiruvda nofaol o'quvchi topilmasligi kerak
    msg_query_inactive = make_mock_message(1001, "Bobur")
    await user_process_search_query(msg_query_inactive, state, async_session)  # type: ignore[arg-type]
    assert "0 ta o'quvchi topildi" in msg_query_inactive.answer.call_args[0][0]

    # 4. O'quvchi kartochkasini ochish
    cb_card = make_mock_callback(1001)
    card_data = UserStudentCallback(action="view", student_id=active_st.id)
    await user_view_student_card(cb_card, card_data, async_session)
    card_text = cb_card.message.edit_text.call_args[0][0]
    assert "Alisher Navoiy" in card_text
    assert "KOR-TOP" in card_text
    assert "O'rtacha ball" in card_text
    # Shaxsiy ma'lumotlar yo'qligini tekshirish
    assert "telefon" not in card_text.lower()
    assert "telegram_id" not in card_text.lower()

    # Nofaol o'quvchi kartochkasi ochilmasligi kerak
    cb_card_inactive = make_mock_callback(1001)
    inactive_card_data = UserStudentCallback(action="view", student_id=inactive_st.id)
    await user_view_student_card(cb_card_inactive, inactive_card_data, async_session)
    assert cb_card_inactive.answer.call_args[1].get("show_alert") is True

    # 5. O'qituvchi izohlarini ko'rish
    note = TeacherNote(
        student_id=active_st.id,
        text="Grammatika qoidalarini mustahkam egallagan.",
        created_by=999,
        created_at=datetime.now(UTC),
    )
    async_session.add(note)
    await async_session.commit()

    cb_notes = make_mock_callback(1001)
    notes_data = UserStudentCallback(action="notes", student_id=active_st.id)
    await user_view_student_notes(cb_notes, notes_data, async_session)
    notes_text = cb_notes.message.edit_text.call_args[0][0]
    assert "Grammatika qoidalarini" in notes_text

    # 6. Davomat hisobotini ko'rish
    cb_att = make_mock_callback(1001)
    att_data = UserStudentCallback(action="attendance", student_id=active_st.id)
    await user_view_student_attendance(cb_att, att_data, async_session)
    att_text = cb_att.message.edit_text.call_args[0][0]
    assert "Davomat hisoboti" in att_text


@pytest.mark.asyncio
async def test_user_rating_and_pagination(async_session: AsyncSession) -> None:
    """Foydalanuvchi reytingi va to'liq sahifalash testlari."""
    # 5 ta o'quvchi qo'shamiz
    for i in range(1, 6):
        st = Student(
            full_name=f"Talaba {i}",
            level="boshlang'ich",
            group_name="KOR-1",
            is_active=True,
        )
        async_session.add(st)
    await async_session.commit()

    # TOP-10 menyusi
    msg_rating = make_mock_message(1001)
    await user_rating_menu_click(msg_rating, async_session)
    assert "Falcon Kibertexnology School" in msg_rating.answer.call_args[0][0]
    assert "TOP-" in msg_rating.answer.call_args[0][0]

    # To'liq ro'yxat callback
    cb_full = make_mock_callback(1001)
    nav_data = UserNavCallback(target="rating_full", page=0)
    await user_rating_full_callback(cb_full, nav_data, async_session)
    full_text = cb_full.message.edit_text.call_args[0][0]
    assert "to'liq reytingi" in full_text
    assert "🥇" in full_text

    # TOP-10 ga qaytish callback
    cb_top = make_mock_callback(1001)
    await user_rating_top_callback(cb_top, async_session)
    assert "TOP-" in cb_top.message.edit_text.call_args[0][0]


@pytest.mark.asyncio
async def test_user_lessons_comments_and_about(async_session: AsyncSession) -> None:
    """Hozirgi dars, darsga izoh qoldirish va maktab haqida ma'lumot."""
    # 1. Hozirgi dars yo'q payti
    msg_lsn = make_mock_message(1001)
    await user_current_lesson(msg_lsn, async_session)
    assert "faol dars mavjud emas" in msg_lsn.answer.call_args[0][0]

    # Faol dars yaratamiz
    lesson = Lesson(
        title="Koreys tili 5-dars: Fe'llar",
        starts_at=datetime.now(UTC),
        status="davom_etmoqda",
        created_by=999,
    )
    async_session.add(lesson)
    await async_session.commit()
    await async_session.refresh(lesson)

    # Faol dars bor payti
    msg_active_lsn = make_mock_message(1001)
    await user_current_lesson(msg_active_lsn, async_session)
    assert "HOZIRDA DARS DAVOM ETMOQDA" in msg_active_lsn.answer.call_args[0][0]

    # 2. Darsga izoh qoldirish
    state = MockFSMContext()
    msg_com_menu = make_mock_message(1001)
    await user_comment_menu_click(msg_com_menu, async_session, state)  # type: ignore[arg-type]
    assert await state.get_state() == str(LessonCommentStates.waiting_for_comment)

    # Izoh saqlash
    msg_com_save = make_mock_message(1001, "Dars juda foydali bo'ldi, rahmat!")
    await user_save_comment(msg_com_save, state, async_session)  # type: ignore[arg-type]
    assert "tashakkur" in msg_com_save.answer.call_args[0][0].lower()

    # 3. Maktab haqida ma'lumot
    msg_about = make_mock_message(1001)
    await user_about_school(msg_about, async_session)
    assert "Falcon Kibertexnology School" in msg_about.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_all_admin_callbacks_rejected_for_regular_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    XAVFSIZLIK TESTI:
    Oddiy (non-admin) foydalanuvchi ADMIN_CALLBACK_PREFIXES dagi barcha prefikslarni
    yoki 'nav:add_student' ni yuborganda, DatabaseAndAuthMiddleware ularning
    barchasini qat'iy rad etadi (show_alert=True bilan) va handlerga o'tkazmaydi!
    """
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    await init_db(target_engine=test_engine)
    test_session_maker = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr("app.middlewares.auth.async_session_maker", test_session_maker)

    middleware = DatabaseAndAuthMiddleware()
    handler = AsyncMock()

    # Tekshiriladigan prefikslar
    admin_samples = [
        "st_act:delete:1",
        "grd:score:1:5",
        "att:mark:1:1:keldi",
        "note:add:1",
        "lsn:start:1",
        "adm:stats:overview",
        "nav:add_student:0",
    ]

    for sample_cb in admin_samples:
        cb = make_mock_callback(user_id=555001, data=sample_cb)
        data: dict = {}

        result = await middleware(handler, cb, data)
        # Handler chaqirilmasligi kerak (None qaytaradi)
        assert result is None
        assert handler.call_count == 0
        # Callback query ga show_alert bilan javob berilgan bo'lishi kerak
        assert cb.answer.call_count >= 1
        last_call = cb.answer.call_args
        assert "Ruxsat yo'q" in last_call[0][0]
        assert last_call[1].get("show_alert") is True
        cb.answer.reset_mock()

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_load_20_requests(tmp_path: Path) -> None:
    """
    YUKLAMA VA KONKURENTLIK TESTI:
    20 ta bir vaqtning o'zida yuborilgan parallel asinxron baza so'rovlari
    (o'quvchi qo'shish, baholash, o'qish) hech qanday bloklanishsiz (database locked)
    va greenlet xatolarisiz to'liq muvaffaqiyatli bajariladi.
    """
    db_file = tmp_path / "concurrent_test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file.as_posix()}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection: object, connection_record: object) -> None:
        if isinstance(dbapi_connection, SQLite3Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=10000")
            cursor.close()

    try:
        await init_db(target_engine=engine)
        session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

        async def worker_task(worker_id: int) -> bool:
            async with session_maker() as session:
                # 1. O'quvchi yaratish
                st = Student(
                    full_name=f"Konkurent O'quvchi {worker_id}",
                    level="boshlang'ich",
                    group_name=f"GRP-{worker_id % 3}",
                    is_active=True,
                )
                session.add(st)
                await session.commit()
                await session.refresh(st)

                # 2. Baho qo'yish
                grd = Grade(
                    student_id=st.id,
                    score=5,
                    created_by=999,
                    comment=f"Worker {worker_id} bahosi",
                )
                session.add(grd)
                await session.commit()

                # 3. O'qish
                loaded = await session.get(Student, st.id)
                return loaded is not None

        # 20 ta parallel vazifani ishga tushirish
        tasks = [worker_task(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 20
        assert all(results) is True
    finally:
        await engine.dispose()
