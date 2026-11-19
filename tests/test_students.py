"""
Falcon Kibertexnology School - O'quvchilar bo'limi testlari.
O'quvchi qo'shish, qidirish, 20 ta o'quvchi bilan sahifalash (pagination)
va soft delete amallari tekshiriladi.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.repositories.student_repo import StudentRepository
from app.database.session import init_db


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
async def test_add_student_and_link_parent(async_session: AsyncSession) -> None:
    """O'quvchi qo'shish va ota-onani bog'lash tekshiruvi."""
    repo = StudentRepository(async_session)

    student = await repo.create(
        full_name="Kim Min Jae",
        level="boshlang'ich",
        group_name="KOR-101",
        parent_telegram_id=None,
    )
    assert student.id is not None
    assert student.full_name == "Kim Min Jae"
    assert student.parent_telegram_id is None
    assert student.is_active is True

    # Ota-onani bog'lash
    linked = await repo.link_parent(student.id, parent_telegram_id=987654321)
    assert linked is not None
    assert linked.parent_telegram_id == 987654321

    # Ota-ona ID bo'yicha qidirish
    parent_students = await repo.get_by_parent_telegram_id(987654321)
    assert len(parent_students) == 1
    assert parent_students[0].id == student.id


@pytest.mark.asyncio
async def test_pagination_with_20_students(async_session: AsyncSession) -> None:
    """20 ta o'quvchi yaratib, sahifalash (har sahifada 8 ta) to'g'ri ishlashini tekshirish."""
    repo = StudentRepository(async_session)

    # 20 ta o'quvchi qo'shamiz
    for i in range(1, 21):
        # Format: O'quvchi 01, O'quvchi 02 ...
        await repo.create(
            full_name=f"O'quvchi {i:02d}",
            level="boshlang'ich" if i <= 10 else "o'rta",
            group_name="KOR-A" if i <= 10 else "KOR-B",
        )

    # 1-sahifa (offset=0, limit=8)
    page1, total1 = await repo.get_active_students(offset=0, limit=8)
    assert total1 == 20
    assert len(page1) == 8
    assert page1[0].full_name == "O'quvchi 01"
    assert page1[7].full_name == "O'quvchi 08"

    # 2-sahifa (offset=8, limit=8)
    page2, total2 = await repo.get_active_students(offset=8, limit=8)
    assert total2 == 20
    assert len(page2) == 8
    assert page2[0].full_name == "O'quvchi 09"
    assert page2[7].full_name == "O'quvchi 16"

    # 3-sahifa (offset=16, limit=8) -> oxirgi 4 ta o'quvchi
    page3, total3 = await repo.get_active_students(offset=16, limit=8)
    assert total3 == 20
    assert len(page3) == 4
    assert page3[0].full_name == "O'quvchi 17"
    assert page3[3].full_name == "O'quvchi 20"


@pytest.mark.asyncio
async def test_student_search_by_name(async_session: AsyncSession) -> None:
    """Ism bo'yicha qidiruv (case-insensitive va qisman moslik)."""
    repo = StudentRepository(async_session)

    await repo.create("Fazliddin Xoldorov", "yuqori", "KOR-ADV")
    await repo.create("Jasur Xoldorov", "o'rta", "KOR-INT")
    await repo.create("Malika Rahimova", "boshlang'ich", "KOR-BEG")

    # 'xoldorov' bo'yicha qidiruv (2 ta chiqishi kerak)
    res_xoldorov, count_x = await repo.get_active_students(search_query="xoldorov")
    assert count_x == 2
    assert len(res_xoldorov) == 2

    # 'Fazliddin' bo'yicha qidiruv (1 ta chiqishi kerak)
    res_fazliddin, count_f = await repo.get_active_students(search_query="fazliddin")
    assert count_f == 1
    assert res_fazliddin[0].full_name == "Fazliddin Xoldorov"

    # Mavjud bo'lmagan ism
    res_none, count_none = await repo.get_active_students(search_query="Noma'lum")
    assert count_none == 0
    assert len(res_none) == 0


@pytest.mark.asyncio
async def test_soft_delete(async_session: AsyncSession) -> None:
    """
    Chiqarib tashlash (soft delete):
    is_active=False bo'ladi, ro'yxatdan yo'qoladi, lekin bazada saqlanadi.
    """
    repo = StudentRepository(async_session)

    st = await repo.create("Temur Aliyev", "boshlang'ich", "KOR-1", parent_telegram_id=444555)
    student_id = st.id

    # Faol ro'yxatda bor
    active_list, count_before = await repo.get_active_students()
    assert count_before == 1

    # Soft delete qilish
    deleted = await repo.soft_delete(student_id)
    assert deleted is True

    # Endi faol ro'yxatda chiqmaydi
    active_after, count_after = await repo.get_active_students()
    assert count_after == 0
    assert len(active_after) == 0

    # Ota-onaning faol farzandlari ro'yxatida ham chiqmaydi
    p_students = await repo.get_by_parent_telegram_id(444555)
    assert len(p_students) == 0

    # Lekin to'g'ridan-to'g'ri bazadan ID orqali o'qiganda ma'lumotlar saqlanib turadi
    raw_st = await repo.get_by_id(student_id)
    assert raw_st is not None
    assert raw_st.full_name == "Temur Aliyev"
    assert raw_st.is_active is False
