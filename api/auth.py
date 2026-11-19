"""
Falcon Kibertexnology School - Telegram WebApp Autentifikatsiya moduli.
initData ni HMAC-SHA256 orqali serverda to'liq tekshirish va rollarni aniqlash.
"""

import hashlib
import hmac
import json
import logging
import time
import urllib.parse
from functools import wraps
from typing import Any, Callable

from aiohttp import web

from app.config import settings

logger = logging.getLogger(__name__)


def validate_telegram_init_data(
    init_data_raw: str,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> tuple[bool, dict[str, Any]]:
    """
    Telegram WebApp initData ni HMAC-SHA256 orqali tekshirish.
    Telegram rasmiy spetsifikatsiyasi:
    1. hash parametri olinadi va ajratiladi.
    2. Qolgan parametrlar alifbo tartibida 'k=v\\n' ko'rinishida birlashtiriladi.
    3. secret_key = HMAC-SHA256("WebAppData", bot_token).
    4. signature = HMAC-SHA256(secret_key, data_check_string).
    5. auth_date 24 soatdan (86400 soniya) eski bo'lmasligi shart.
    Qaytaradi: (haqiqiymi, user_dict)
    """
    if not init_data_raw or not bot_token:
        return False, {}

    try:
        parsed_params = urllib.parse.parse_qsl(init_data_raw, keep_blank_values=True)
        param_dict = dict(parsed_params)

        received_hash = param_dict.get("hash")
        if not received_hash:
            return False, {}

        # auth_date tekshiruvi (24 soat)
        auth_date_raw = param_dict.get("auth_date")
        if not auth_date_raw:
            return False, {}

        try:
            auth_date = int(auth_date_raw)
        except ValueError:
            return False, {}

        now = int(time.time())
        # auth_date 24 soatdan eski yoki kelajakdagi (5 daqiqadan ko'p) bo'lsa rad etiladi
        if now - auth_date > max_age_seconds or auth_date > now + 300:
            return False, {}

        # data_check_string hosil qilish: hash dan boshqa barcha parametrlarni saralash
        sorted_pairs = sorted([(k, v) for k, v in parsed_params if k != "hash"], key=lambda x: x[0])
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_pairs)

        # secret_key: HMAC-SHA256("WebAppData", bot_token)
        secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()

        # calculated_hash: HMAC-SHA256(secret_key, data_check_string)
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return False, {}

        user_json = param_dict.get("user")
        user_dict = json.loads(user_json) if user_json else {}
        return True, user_dict
    except Exception as e:
        logger.warning(f"initData tekshirishda xatolik: {e}")
        return False, {}


def extract_init_data(request: web.Request) -> str:
    """So'rovdan initData qatorini ajratib olish (Header yoki query param)."""
    # 1. Maxsus X-Telegram-Init-Data headeri
    header_val = request.headers.get("X-Telegram-Init-Data")
    if header_val:
        return header_val.strip()

    # 2. Authorization: Bearer <initData>
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    # 3. Query param (odatda dastlabki GET so'rovda)
    query_val = request.query.get("initData")
    if query_val:
        return query_val.strip()

    return ""


def get_authenticated_user(request: web.Request) -> tuple[bool, bool, dict[str, Any]]:
    """
    So'rovni tekshiradi va foydalanuvchi ma'lumotlarini qaytaradi.
    Qaytaradi: (is_valid, is_admin, user_dict)
    """
    init_data = extract_init_data(request)
    if not init_data:
        return False, False, {}

    is_valid, user_dict = validate_telegram_init_data(
        init_data_raw=init_data,
        bot_token=settings.BOT_TOKEN,
    )

    if not is_valid or not user_dict:
        return False, False, {}

    telegram_id = user_dict.get("id")
    if not telegram_id:
        return False, False, {}

    is_admin = settings.is_admin(int(telegram_id))
    return True, is_admin, user_dict


def admin_required(handler: Callable) -> Callable:
    """
    API endpointlar uchun faqat ADMIN/O'QITUVCHI ga ruxsat beruvchi dekorator.
    Agar initData haqiqiy bo'lmasa -> 401 Unauthorized.
    Agar foydalanuvchi ADMIN_IDS da bo'lmasa -> 403 Forbidden.
    """

    @wraps(handler)
    async def wrapper(request: web.Request, *args: Any, **kwargs: Any) -> web.Response:
        is_valid, is_admin, user_dict = get_authenticated_user(request)

        if not is_valid:
            return web.json_response(
                {"error": "Avtorizatsiyadan o'tilmagan yoki yaroqsiz initData."},
                status=401,
            )

        if not is_admin:
            return web.json_response(
                {"error": "Ruxsat yo'q. Ushbu tizim faqat o'qituvchi/admin uchun."},
                status=403,
            )

        request["telegram_user"] = user_dict
        return await handler(request, *args, **kwargs)

    return wrapper
