"""
Falcon Kibertexnology School - Ma'lumotlar ombori paket eksporti.
"""

from app.database.repositories.attendance_repo import AttendanceRepository
from app.database.repositories.comment_repo import LessonCommentRepository
from app.database.repositories.grade_repo import GradeRepository
from app.database.repositories.lesson_repo import LessonRepository
from app.database.repositories.note_repo import TeacherNoteRepository
from app.database.repositories.school_info_repo import SchoolInfoRepository
from app.database.repositories.student_repo import StudentRepository
from app.database.repositories.user_repo import UserRepository

__all__ = [
    "AttendanceRepository",
    "GradeRepository",
    "LessonCommentRepository",
    "LessonRepository",
    "SchoolInfoRepository",
    "StudentRepository",
    "TeacherNoteRepository",
    "UserRepository",
]
