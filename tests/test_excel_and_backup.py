"""
Falcon Kibertexnology School - Excel eksport va zaxira nusxa (backup) testlari.
"""

import os

import openpyxl
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.models import Student
from app.database.session import init_db
from app.utils.backup import perform_db_backup
from app.utils.excel_export import generate_school_excel_report


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
async def test_excel_export_generation(async_session: AsyncSession) -> None:
    """Excel hisobot fayli to'g'ri yaratilishi va varaqlar mavjudligini tekshirish."""
    # O'quvchi qo'shamiz
    st = Student(
        full_name="Excel Test O'quvchi",
        level="boshlang'ich",
        group_name="KOR-EXCEL",
        is_active=True,
    )
    async_session.add(st)
    await async_session.commit()

    filepath = await generate_school_excel_report(async_session)
    assert os.path.exists(filepath)
    assert filepath.endswith(".xlsx")

    # openpyxl orqali o'qib tekshirish
    wb = openpyxl.load_workbook(filepath)
    assert "O'quvchilar" in wb.sheetnames
    assert "Baholar" in wb.sheetnames
    assert "Davomat" in wb.sheetnames

    # Tozalash
    try:
        os.remove(filepath)
    except Exception:
        pass


def test_sqlite_db_backup(tmp_path: object) -> None:
    """Baza faylini backups/ papkasiga nusxalash tekshiruvi."""
    # Test uchun soxta db fayl yaratamiz
    fake_db = tmp_path / "test_school.db"
    fake_db.write_text("SQLite format 3 test header")

    backup_dir = tmp_path / "backups"
    dest = perform_db_backup(db_file_path=str(fake_db), backup_folder=str(backup_dir))

    assert dest != ""
    assert os.path.exists(dest)
    assert os.path.basename(dest).startswith("falcon_school_backup_")
