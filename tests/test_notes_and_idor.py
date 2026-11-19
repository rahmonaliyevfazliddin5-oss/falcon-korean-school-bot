"""
Falcon Kibertexnology School - O'qituvchi izohlari va IDOR xavfsizlik testlari.
Izoh qo'shish, tahrirlash, o'chirish va ota-onaning faqat o'z farzandi
ma'lumotlarini ko'ra olishi (boshqa o'quvchi ma'lumotlariga ruxsatsiz kirishdan himoya) tekshiriladi.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.repositories.grade_repo import GradeRepository
from app.database.repositories.note_repo import TeacherNoteRepository
from app.database.repositories.student_repo import StudentRepository
from app.database.session import init_db
from app.handlers.parent.dashboard import get_parent_student
from app.keyboards.builders import get_main_menu_keyboard


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
async def test_teacher_notes_crud(async_session: AsyncSession) -> None:
    """Izoh qo'shish, tahrirlash va o'chirish amallari."""
    student_repo = StudentRepository(async_session)
    note_repo = TeacherNoteRepository(async_session)

    student = await student_repo.create(
        full_name="Otabek Shokirov", level="o'rta", group_name="KOR-202"
    )

    # 1. Qo'shish
    note = await note_repo.create(
        student_id=student.id,
        text="Fazliddin hulqi yaxshi, darslarni qoldirmay qatnashadi.",
        created_by=777,
    )
    assert note.id is not None
    assert note.text == "Fazliddin hulqi yaxshi, darslarni qoldirmay qatnashadi."
    note_id = note.id

    # 2. Tahrirlash
    updated = await note_repo.update(
        note_id=note_id, text="Yangi matn: Grammatikani a'lo o'zlashtirdi."
    )
    assert updated is not None
    assert updated.text == "Yangi matn: Grammatikani a'lo o'zlashtirdi."

    # 3. O'chirish
    deleted = await note_repo.delete(note_id)
    assert deleted is True
    assert await note_repo.get_by_id(note_id) is None


@pytest.mark.asyncio
async def test_idor_protection_parent_can_only_access_own_child_data(
    async_session: AsyncSession,
) -> None:
    """
    IDOR tekshiruvi:
    Ota-ona A (ID: 1001) faqat O'quvchi A ma'lumotlarini ko'ra oladi.
    Ota-ona B (ID: 1002) faqat O'quvchi B ma'lumotlarini ko'ra oladi.
    Ota-ona A ga boshqa o'quvchining izohlari yoki baholari mutlaqo chiqmaydi!
    """
    student_repo = StudentRepository(async_session)
    note_repo = TeacherNoteRepository(async_session)
    grade_repo = GradeRepository(async_session)

    # O'quvchi A va Ota-ona A (1001)
    student_a = await student_repo.create(
        full_name="O'quvchi A",
        level="boshlang'ich",
        group_name="KOR-1",
        parent_telegram_id=1001,
    )
    await note_repo.create(student_id=student_a.id, text="A uchun maxfiy izoh", created_by=999)
    await grade_repo.create(student_id=student_a.id, score=5, created_by=999, comment="A bahosi")

    # O'quvchi B va Ota-ona B (1002)
    student_b = await student_repo.create(
        full_name="O'quvchi B",
        level="yuqori",
        group_name="KOR-2",
        parent_telegram_id=1002,
    )
    await note_repo.create(student_id=student_b.id, text="B uchun maxfiy izoh", created_by=999)
    await grade_repo.create(student_id=student_b.id, score=3, created_by=999, comment="B bahosi")

    # 1. Ota-ona A o'z farzandini so'raydi
    found_a = await get_parent_student(telegram_id=1001, session=async_session)
    assert found_a is not None
    assert found_a.id == student_a.id
    assert found_a.full_name == "O'quvchi A"

    # Ota-ona A faqat O'quvchi A izohlarini oladi
    notes_a = await note_repo.get_by_student_id(found_a.id)
    assert len(notes_a) == 1
    assert notes_a[0].text == "A uchun maxfiy izoh"

    # 2. Ota-ona B o'z farzandini so'raydi
    found_b = await get_parent_student(telegram_id=1002, session=async_session)
    assert found_b is not None
    assert found_b.id == student_b.id
    assert found_b.full_name == "O'quvchi B"

    # Ota-ona B faqat O'quvchi B izohlarini oladi
    notes_b = await note_repo.get_by_student_id(found_b.id)
    assert len(notes_b) == 1
    assert notes_b[0].text == "B uchun maxfiy izoh"

    # 3. Begona / bog'lanmagan foydalanuvchi (1003) so'raganda None qaytadi
    unlinked = await get_parent_student(telegram_id=1003, session=async_session)
    assert unlinked is None


def test_main_menu_by_role() -> None:
    """Rolga qarab menyu tugmalari to'g'ri chiqishini tekshirish."""
    # 1. Admin menyusi
    admin_kb = get_main_menu_keyboard(role="admin")
    admin_button_texts = [btn.text for row in admin_kb.keyboard for btn in row]
    assert "👥 O'quvchilar" in admin_button_texts
    assert "⭐ Baholash" in admin_button_texts
    assert "📋 Davomat" in admin_button_texts
    assert "📝 Izohlar" in admin_button_texts
    assert "🎥 Video dars" in admin_button_texts
    assert "🏆 Reyting" in admin_button_texts
    assert "📊 Statistika" in admin_button_texts

    # 2. Oddiy foydalanuvchi menyusi
    user_kb = get_main_menu_keyboard(role="user")
    user_button_texts = [btn.text for row in user_kb.keyboard for btn in row]
    assert "👥 O'quvchilar" in user_button_texts
    assert "🏆 Reyting" in user_button_texts
    assert "🎥 Hozirgi dars" in user_button_texts
    assert "💬 Dars haqida izoh" in user_button_texts
    assert "ℹ️ Maktab haqida" in user_button_texts
    # Admin tugmalari oddiy foydalanuvchida bo'lmasligi kerak
    assert "⭐ Baholash" not in user_button_texts
    assert "📊 Statistika" not in user_button_texts
