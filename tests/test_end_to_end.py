"""
Falcon Kibertexnology School - End-to-End integratsion stsenariy testi.
Ketma-ket to'liq jarayon tekshiriladi:
Admin kirishi -> O'quvchi qo'shish -> Baholash -> Dars yaratish/boshlash/tugatish ->
Davomat belgilash -> O'qituvchi izohi -> Reyting hisoblash -> Ota-ona kabinetida aks etishi.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database.models import User
from app.database.repositories.note_repo import TeacherNoteRepository
from app.database.repositories.student_repo import StudentRepository
from app.database.repositories.user_repo import UserRepository
from app.database.session import init_db
from app.handlers.parent.dashboard import get_parent_student
from app.services import (
    AttendanceService,
    GradingService,
    LessonService,
    RatingService,
)
from app.utils.filters import IsAdminFilter
from app.utils.security import AdminSecurityManager


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
async def test_full_end_to_end_scenario(async_session: AsyncSession) -> None:
    """
    To'liq end-to-end stsenariy:
    1. Admin autentifikatsiyasi
    2. O'quvchi qo'shish va ota-onani bog'lash
    3. Baholash
    4. Dars rejalashtirish, boshlash va tugatish
    5. Davomat belgilash
    6. O'qituvchi izohi
    7. Reyting shakllanishi
    8. Ota-onaning ko'rishi (IDOR himoyasi bilan)
    9. Begona foydalanuvchi rad etilishi
    """
    settings.ADMIN_IDS = "99001"
    admin_id = 99001
    parent_id = 88001
    stranger_id = 11001

    user_repo = UserRepository(async_session)
    student_repo = StudentRepository(async_session)
    grade_service = GradingService(async_session)
    att_service = AttendanceService(async_session)
    lesson_service = LessonService(async_session)
    rating_service = RatingService(async_session)
    note_repo = TeacherNoteRepository(async_session)
    sec_manager = AdminSecurityManager()

    # --- 1. Admin kirishi ---
    login_ok, _ = sec_manager.verify_login(actual_telegram_id=admin_id, entered_id=admin_id)
    assert login_ok is True
    admin_user = await user_repo.create_or_update(
        telegram_id=admin_id, full_name="Bosh Admin", role="admin"
    )
    assert admin_user.role == "admin"

    # --- 2. Ota-ona botga /start bosib ro'yxatdan o'tadi ---
    parent_user = await user_repo.create_or_update(
        telegram_id=parent_id, full_name="Karimov Ota", role="parent"
    )
    assert parent_user.role == "parent"

    # Admin o'quvchi qo'shadi va ota-ona ID sini bog'laydi
    student = await student_repo.create(
        full_name="Azizbek Karimov",
        level="boshlang'ich",
        group_name="KOR-101",
        parent_telegram_id=parent_id,
    )
    assert student.id is not None
    assert student.parent_telegram_id == parent_id

    # --- 3. Baholash ---
    grade = await grade_service.add_grade(
        student_id=student.id,
        score=5,
        created_by=admin_id,
        comment="Hangul harflarini to'liq o'zlashtirdi",
    )
    assert grade.score == 5
    avg_score = await grade_service.get_student_average(student.id)
    assert avg_score == 5.0

    # --- 4. Dars yaratish, boshlash va tugatish ---
    lesson = await lesson_service.create_lesson(
        title="1-dars: Koreys tili Hangul alifbosi",
        starts_at=datetime.now(UTC),
        created_by=admin_id,
    )
    assert lesson.id is not None
    assert lesson.status == "rejalashtirilgan"

    # Mock Bot bilan darsni boshlash
    mock_bot = MagicMock()
    mock_invite = MagicMock()
    mock_invite.invite_link = "https://t.me/+falconInvite123"
    mock_bot.create_chat_invite_link = AsyncMock(return_value=mock_invite)
    mock_bot.send_message = AsyncMock()

    started, link, sent = await lesson_service.start_lesson(
        bot=mock_bot, lesson_id=lesson.id, group_id=-100999
    )
    assert started.status == "davom_etmoqda"
    assert link == "https://t.me/+falconInvite123"
    assert sent >= 2  # Admin va Ota-onaga yuborildi

    # Darsni tugatish
    ended = await lesson_service.end_lesson(lesson.id)
    assert ended.status == "tugagan"

    # --- 5. Davomat belgilash ---
    att = await att_service.mark_attendance(
        student_id=student.id, lesson_id=lesson.id, status="keldi"
    )
    assert att.status == "keldi"
    att_stats = await att_service.get_student_stats(student.id)
    assert att_stats["percentage"] == 100.0

    # --- 6. O'qituvchi izohi ---
    note = await note_repo.create(
        student_id=student.id,
        text="Azizbek darsda faol, uyga vazifani vaqtida topshirdi.",
        created_by=admin_id,
    )
    assert note.id is not None

    # --- 7. Reyting hisoblash ---
    ratings = await rating_service.get_all_ratings()
    assert len(ratings) == 1
    # 5.0 * 0.7 + (100 / 100 * 5 * 0.3) = 3.5 + 1.5 = 5.0
    assert ratings[0]["total_score"] == 5.0
    assert ratings[0]["rank"] == 1
    assert ratings[0]["full_name"] == "Azizbek Karimov"

    # --- 8. Ota-onaning ko'rinishi ---
    child = await get_parent_student(parent_id, async_session)
    assert child is not None
    assert child.id == student.id

    child_notes = await note_repo.get_by_student_id(child.id)
    assert len(child_notes) == 1
    assert "Azizbek darsda faol" in child_notes[0].text

    # --- 9. Xavfsizlik: Begona foydalanuvchi tekshiruvi ---
    stranger_child = await get_parent_student(stranger_id, async_session)
    assert stranger_child is None  # Begona ota-onaga hech qanday bola ko'rinmaydi

    admin_filter = IsAdminFilter()
    stranger_user = User(telegram_id=stranger_id, full_name="Begona", role="parent")
    is_stranger_admin = await admin_filter(MagicMock(), current_user=stranger_user)
    assert is_stranger_admin is False  # Admin huquqi berilmaydi
