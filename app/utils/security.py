"""
Falcon Kibertexnology School - Xavfsizlik va Admin login nazoratchisi.
Noto'g'ri urinishlarni hisoblash va 10 daqiqaga bloklash mantiqini boshqaradi.
"""

import logging
import time

from app.config import settings

logger = logging.getLogger(__name__)


# O'zgarmas doimiy Admin Panel ID raqami
ADMIN_PANEL_ID: str = "07070707"


class AdminSecurityManager:
    """Admin tizimiga kirish xavfsizligini ta'minlovchi menejer."""

    def __init__(self, block_duration_seconds: int = 600) -> None:
        self.block_duration = block_duration_seconds
        # user_id -> [urinish_vaqtlari]
        self._failed_attempts: dict[int, list[float]] = {}
        # user_id -> blok_tugash_vaqti
        self._blocked_users: dict[int, float] = {}

    def is_blocked(self, telegram_id: int) -> tuple[bool, int]:
        """
        Foydalanuvchi bloklanganligini tekshiradi.
        Qaytaradi: (bloklanganmi, qolgan_soniyalar)
        """
        now = time.time()
        blocked_until = self._blocked_users.get(telegram_id, 0)
        if now < blocked_until:
            remaining = int(blocked_until - now)
            return True, remaining
        elif telegram_id in self._blocked_users:
            # Blok muddati tugagan bo'lsa, tozalaymiz
            del self._blocked_users[telegram_id]
            self._failed_attempts.pop(telegram_id, None)
        return False, 0

    def verify_login(self, actual_telegram_id: int, entered_id: int | str) -> tuple[bool, str]:
        """
        Admin kirishini tekshiradi.
        XAVFSIZLIK QOIDALARI:
        1. Bloklangan bo'lsa darhol rad etiladi.
        2. Kiritilgan kod o'zgarmas ADMIN_PANEL_ID ('07270727') ga teng bo'lishi,
           yoki kiritilgan ID ham ADMIN_IDS da bo'lib, haqiqiy Telegram ID ga teng bo'lishi kerak.
        3. 3 marta xato bo'lsa 10 daqiqaga bloklanadi va log yoziladi.
        """
        is_blk, remaining = self.is_blocked(actual_telegram_id)
        if is_blk:
            return (
                False,
                f"❌ Xavfsizlik cheklovi: Siz 10 daqiqaga bloklangansiz. Qolgan vaqt: {remaining // 60} daqiqa.",
            )

        now = time.time()
        entered_str = str(entered_id).strip()

        # O'zgarmas doimiy Admin Panel ID (07070707) tekshiruvi
        is_panel_id_match = entered_str in (ADMIN_PANEL_ID, "7070707")

        # Telegram ID tekshiruvi (agar ADMIN_IDS ro'yxatida bo'lsa)
        admin_list = settings.admin_ids_list
        is_telegram_id_match = False
        try:
            numeric_val = int(entered_str)
            is_telegram_id_match = (numeric_val in admin_list) and (
                numeric_val == actual_telegram_id
            )
        except (ValueError, TypeError):
            is_telegram_id_match = False

        is_valid = is_panel_id_match or is_telegram_id_match

        if is_valid:
            # Muvaffaqiyatli kirishda urinishlar tarixini tozalaymiz
            self._failed_attempts.pop(actual_telegram_id, None)
            logger.info(
                f"[ADMIN LOGIN SUCCESS] Telegram ID: {actual_telegram_id} muvaffaqiyatli admin bo'ldi."
            )
            return True, "✅ Kirish muvaffaqiyatli! Admin panel ochildi."

        # Noto'g'ri urinish
        attempts = self._failed_attempts.setdefault(actual_telegram_id, [])
        # Faqat so'nggi 10 daqiqadagi urinishlarni saqlaymiz
        attempts = [t for t in attempts if now - t < self.block_duration]
        attempts.append(now)
        self._failed_attempts[actual_telegram_id] = attempts

        if len(attempts) >= 3:
            self._blocked_users[actual_telegram_id] = now + self.block_duration
            logger.warning(
                f"[SECURITY ALERT] Telegram ID: {actual_telegram_id} 3 marta noto'g'ri admin login kiritdi va 10 daqiqaga bloklandi!"
            )
            return (
                False,
                "🚫 Siz 3 marta noto'g'ri ID kiritdingiz va xavfsizlik maqsadida 10 daqiqaga bloklandingiz!",
            )

        remaining_attempts = 3 - len(attempts)
        logger.warning(
            f"[ADMIN LOGIN FAILED] Telegram ID: {actual_telegram_id} noto'g'ri ID kiritdi: {entered_id}. Qolgan urinishlar: {remaining_attempts}"
        )
        return (
            False,
            f"⛔️ Ruxsat yo'q! Kiritilgan ID noto'g'ri. Qolgan urinishlar soni: {remaining_attempts}",
        )


# Global yagona nusxa
admin_security = AdminSecurityManager()
