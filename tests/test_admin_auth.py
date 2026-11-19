"""
Falcon Kibertexnology School - Admin autentifikatsiyasi va xavfsizlik testlari.
(1) ADMIN_IDS dagi odam to'g'ri ID bilan kira oladi;
(2) Oddiy foydalanuvchi o'z ID sini yozsa rad etiladi;
(3) Birovning admin ID sini yozsa rad etiladi;
(4) 3 xato urinishdan keyin blok ishlaydi;
(5) Parent admin callback/handlerlariga kira olmaydi.
"""

from unittest.mock import MagicMock

import pytest
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.database.models import User
from app.utils.filters import IsAdminFilter
from app.utils.security import AdminSecurityManager


@pytest.fixture
def clean_security_manager() -> AdminSecurityManager:
    """Yangi xavfsizlik menejeri nusxasi."""
    return AdminSecurityManager(block_duration_seconds=600)


def test_admin_can_login_with_correct_id(
    clean_security_manager: AdminSecurityManager,
) -> None:
    """(1) ADMIN_IDS dagi odam to'g'ri ID bilan muvaffaqiyatli kira oladi."""
    settings.ADMIN_IDS = "999001,999002"

    admin_id = 999001
    success, msg = clean_security_manager.verify_login(
        actual_telegram_id=admin_id, entered_id=admin_id
    )
    assert success is True
    assert "muvaffaqiyatli" in msg.lower()


def test_admin_can_login_with_permanent_panel_id(
    clean_security_manager: AdminSecurityManager,
) -> None:
    """O'zgarmas doimiy Admin Panel ID '07070707' orqali muvaffaqiyatli kirish."""
    success, msg = clean_security_manager.verify_login(
        actual_telegram_id=6156573399, entered_id="07070707"
    )
    assert success is True
    assert "muvaffaqiyatli" in msg.lower()


def test_ordinary_user_entering_own_id_is_rejected(
    clean_security_manager: AdminSecurityManager,
) -> None:
    """(2) Oddiy foydalanuvchi o'z ID sini yozsa rad etiladi."""
    settings.ADMIN_IDS = "999001,999002"

    normal_user_id = 555111
    success, msg = clean_security_manager.verify_login(
        actual_telegram_id=normal_user_id, entered_id=normal_user_id
    )
    assert success is False
    assert "ruxsat yo'q" in msg.lower()


def test_ordinary_user_entering_someone_elses_admin_id_is_rejected(
    clean_security_manager: AdminSecurityManager,
) -> None:
    """(3) Birovning admin ID sini yozsa rad etiladi (ID spoofing himoyasi)."""
    settings.ADMIN_IDS = "999001,999002"

    normal_user_id = 555111
    target_admin_id = 999001

    success, msg = clean_security_manager.verify_login(
        actual_telegram_id=normal_user_id, entered_id=target_admin_id
    )
    assert success is False
    assert "ruxsat yo'q" in msg.lower()


def test_three_failed_attempts_triggers_10_minute_block(
    clean_security_manager: AdminSecurityManager,
) -> None:
    """(4) 3 xato urinishdan keyin 10 daqiqalik blok ishga tushadi."""
    settings.ADMIN_IDS = "999001,999002"

    attacker_id = 1234567

    # 1-urinish
    ok1, _ = clean_security_manager.verify_login(attacker_id, 111)
    assert ok1 is False

    # 2-urinish
    ok2, _ = clean_security_manager.verify_login(attacker_id, 222)
    assert ok2 is False

    # 3-urinish
    ok3, msg3 = clean_security_manager.verify_login(attacker_id, 333)
    assert ok3 is False
    assert "10 daqiqaga bloklandingiz" in msg3

    # Hozir bloklangan
    is_blk, remaining = clean_security_manager.is_blocked(attacker_id)
    assert is_blk is True
    assert remaining > 0

    # 4-urinishda to'g'ri admin ID kiritmoqchi bo'lsa ham rad etiladi
    ok4, msg4 = clean_security_manager.verify_login(attacker_id, 999001)
    assert ok4 is False
    assert "bloklangansiz" in msg4


@pytest.mark.asyncio
async def test_parent_cannot_access_admin_handlers_and_callbacks() -> None:
    """(5) Parent (ota-ona) admin filtri orqali admin handlerlariga kira olmaydi."""
    admin_filter = IsAdminFilter()

    # Admin foydalanuvchi tekshiruvi
    admin_user = User(telegram_id=999001, full_name="Admin", role="admin")
    mock_msg = MagicMock(spec=Message)
    is_admin_allowed = await admin_filter(mock_msg, current_user=admin_user)
    assert is_admin_allowed is True

    # Ota-ona (parent) foydalanuvchi tekshiruvi
    parent_user = User(telegram_id=888001, full_name="Ota", role="parent")
    is_parent_allowed = await admin_filter(mock_msg, current_user=parent_user)
    assert is_parent_allowed is False

    # Begona yoki tizimga kirmagan foydalanuvchi
    is_guest_allowed = await admin_filter(mock_msg, current_user=None)
    assert is_guest_allowed is False

    # CallbackQuery bilan ham xuddi shunday rad etiladi
    mock_cb = MagicMock(spec=CallbackQuery)
    is_parent_cb_allowed = await admin_filter(mock_cb, current_user=parent_user)
    assert is_parent_cb_allowed is False
