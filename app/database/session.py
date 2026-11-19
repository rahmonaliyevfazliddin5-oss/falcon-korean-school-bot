"""
Falcon Kibertexnology School - Ma'lumotlar bazasi ulanishlari va sessiyalari.
SQLAlchemy 2.0 asinxron sessiyalarni boshqaradi.
"""

from collections.abc import AsyncGenerator
from sqlite3 import Connection as SQLite3Connection

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.database.models import Base, SchoolInfo

# Asinxron engine yaratish
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
)


# SQLite uchun Foreign Key cheklovlarini va WAL rejimini sozlash
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection: object, connection_record: object) -> None:
    """SQLite da Foreign Key cheklovlarini, WAL rejimini va timeoutni yoqadi."""
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


# Sessiyalar fabrikasi
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Asinxron sessiya kontekst generatori."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db(target_engine: AsyncEngine | None = None) -> None:
    """
    Ma'lumotlar bazasi jadvallarini yaratadi va boshlang'ich ma'lumotlarni kiritadi.
    """
    eng = target_engine or engine

    # Agar testlarda boshqa engine berilsa, unga ham pragma ulaymiz
    if target_engine and target_engine is not engine:

        @event.listens_for(target_engine.sync_engine, "connect")
        def set_sqlite_pragma_test(dbapi_conn: object, conn_rec: object) -> None:
            if isinstance(dbapi_conn, SQLite3Connection):
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Boshlang'ich maktab ma'lumotini kiritish (agar mavjud bo'lmasa)
    session_factory = async_sessionmaker(bind=eng, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        stmt = select(SchoolInfo).where(SchoolInfo.key == "about_school")
        res = await session.execute(stmt)
        about = res.scalar_one_or_none()
        if not about:
            default_about = SchoolInfo(
                key="about_school",
                content=(
                    "🦅 Falcon Kibertexnology School — Zamonaviy texnologiyalar va "
                    "chuqurlashtirilgan koreys tili maktabi!\n\n"
                    "Bizda siz koreys tilini boshlang'ich darajadan TOPIK 6 gacha sifatli o'rganishingiz, "
                    "Koreyada nufuzli grantlar asosida o'qish imkoniyatini qo'lga kiritishingiz mumkin.\n\n"
                    "📍 Manzil: Toshkent shahri\n"
                    "📞 Aloqa: +998 (90) 123-45-67"
                ),
            )
            session.add(default_about)
            await session.commit()
