"""
Falcon Kibertexnology School - Xizmatlar (Services) paketi eksporti.
"""

from app.services.attendance import AttendanceService
from app.services.grading import GradingService
from app.services.lessons import LessonService
from app.services.rating import RatingService

__all__ = [
    "AttendanceService",
    "GradingService",
    "LessonService",
    "RatingService",
]
