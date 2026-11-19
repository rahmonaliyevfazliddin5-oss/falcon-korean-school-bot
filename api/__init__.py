"""
Falcon Kibertexnology School - API to'plami.
"""

from api.auth import admin_required, get_authenticated_user, validate_telegram_init_data
from api.routes import setup_routes

__all__ = [
    "admin_required",
    "get_authenticated_user",
    "setup_routes",
    "validate_telegram_init_data",
]
