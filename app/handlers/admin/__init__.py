"""
Falcon Kibertexnology School - Admin handlerlari to'plami.
"""

from aiogram import Router

from app.handlers.admin.attendance import admin_attendance_router
from app.handlers.admin.grading import admin_grading_router
from app.handlers.admin.lessons import admin_lessons_router
from app.handlers.admin.notes import admin_notes_router
from app.handlers.admin.stats import admin_stats_router
from app.handlers.admin.students import admin_students_router

admin_router = Router(name="admin_main_router")
admin_router.include_router(admin_students_router)
admin_router.include_router(admin_grading_router)
admin_router.include_router(admin_attendance_router)
admin_router.include_router(admin_notes_router)
admin_router.include_router(admin_lessons_router)
admin_router.include_router(admin_stats_router)

__all__ = ["admin_router"]
