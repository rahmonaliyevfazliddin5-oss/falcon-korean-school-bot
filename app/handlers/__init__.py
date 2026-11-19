"""
Falcon Kibertexnology School - Handlerlar paketi.
"""

from aiogram import Router

from app.handlers.admin import admin_router
from app.handlers.common import common_router
from app.handlers.user import user_router

main_router = Router(name="main_application_router")
main_router.include_router(common_router)
main_router.include_router(admin_router)
main_router.include_router(user_router)

__all__ = ["admin_router", "common_router", "main_router", "user_router"]
