"""
Falcon Kibertexnology School - Middleware larni testlash.
ThrottlingMiddleware (chastotalar chegarasi) va DatabaseAndAuthMiddleware.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, Message
from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.session import init_db
from app.middlewares.auth import DatabaseAndAuthMiddleware
from app.middlewares.throttling import ThrottlingMiddleware


@pytest.fixture
async def test_session_maker() -> async_sessionmaker:
    """Xotiradagi test bazasi sessiya fabrikasi."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    await init_db(target_engine=engine)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield session_maker
    await engine.dispose()


@pytest.mark.asyncio
async def test_throttling_middleware() -> None:
    """Throttling: 1 soniyadan tez kelgan so'rovlar bloklanadi."""
    middleware = ThrottlingMiddleware(rate_limit=1.0)
    handler = AsyncMock(return_value="OK")

    user = TelegramUser(id=999, is_bot=False, first_name="Ali")
    message = MagicMock(spec=Message)
    message.from_user = user
    message.answer = AsyncMock()

    # 1-so'rov: muvaffaqiyatli o'tadi
    res1 = await middleware(handler, message, {})
    assert res1 == "OK"
    assert handler.call_count == 1

    # 2-so'rov (darhol): rad etiladi
    res2 = await middleware(handler, message, {})
    assert res2 is None
    assert handler.call_count == 1  # handler qayta chaqirilmadi
    assert message.answer.call_count == 1  # Ogohlantirish berildi

    # CallbackQuery orqali ham tekshirish
    cb = MagicMock(spec=CallbackQuery)
    cb.from_user = user
    cb.answer = AsyncMock()

    res_cb = await middleware(handler, cb, {})
    assert res_cb is None
    assert cb.answer.call_count == 1


@pytest.mark.asyncio
async def test_database_and_auth_middleware(
    test_session_maker: async_sessionmaker, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DatabaseAndAuthMiddleware: sessiya va user obyektini inject qilish."""
    monkeypatch.setattr("app.middlewares.auth.async_session_maker", test_session_maker)

    middleware = DatabaseAndAuthMiddleware()
    handler = AsyncMock(return_value="SUCCESS")

    user = TelegramUser(id=777001, is_bot=False, first_name="Vali", full_name="Vali Aliyev")
    message = MagicMock(spec=Message)
    message.from_user = user

    data: dict = {}
    res = await middleware(handler, message, data)
    assert res == "SUCCESS"
    assert "session" in data
    assert "current_user" in data
    assert data["current_user"] is not None
    assert data["current_user"].telegram_id == 777001
    assert data["current_user"].role == "user"
