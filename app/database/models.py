"""
Falcon Kibertexnology School - SQLAlchemy 2.0 ma'lumotlar bazasi modellari.
Barcha modellar asinxron Mapped/mapped_column sintaksisida yozilgan.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Barcha modellar uchun tayanch klass."""


class User(Base):
    """Foydalanuvchilar modeli (admin, ota-ona, o'quvchi)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(32), default="parent", nullable=False
    )  # admin, parent, student
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<User id={self.id} tg_id={self.telegram_id} role={self.role}>"


class Student(Base):
    """O'quvchilar modeli."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(64), nullable=False)  # boshlang'ich, o'rta, yuqori
    group_name: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    user_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Aloqalar
    grades: Mapped[list["Grade"]] = relationship(
        "Grade", back_populates="student", cascade="all, delete-orphan", passive_deletes=True
    )
    attendances: Mapped[list["Attendance"]] = relationship(
        "Attendance", back_populates="student", cascade="all, delete-orphan", passive_deletes=True
    )
    notes: Mapped[list["TeacherNote"]] = relationship(
        "TeacherNote", back_populates="student", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Student id={self.id} name={self.full_name} group={self.group_name}>"


class Lesson(Base):
    """Darslar modeli."""

    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(64), default="rejalashtirilgan", nullable=False
    )  # rejalashtirilgan, davom_etmoqda, tugagan
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Aloqalar
    attendances: Mapped[list["Attendance"]] = relationship(
        "Attendance", back_populates="lesson", cascade="all, delete-orphan", passive_deletes=True
    )
    grades: Mapped[list["Grade"]] = relationship(
        "Grade", back_populates="lesson", passive_deletes=True
    )
    comments: Mapped[list["LessonComment"]] = relationship(
        "LessonComment", back_populates="lesson", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Lesson id={self.id} title={self.title} status={self.status}>"


class Grade(Base):
    """Baholar modeli."""

    __tablename__ = "grades"
    __table_args__ = (CheckConstraint("score >= 1 AND score <= 5", name="check_grade_score_range"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    lesson_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("lessons.id", ondelete="SET NULL"), nullable=True, index=True
    )
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Aloqalar
    student: Mapped["Student"] = relationship("Student", back_populates="grades")
    lesson: Mapped[Optional["Lesson"]] = relationship("Lesson", back_populates="grades")

    def __repr__(self) -> str:
        return f"<Grade id={self.id} student_id={self.student_id} score={self.score}>"


class Attendance(Base):
    """Davomat modeli."""

    __tablename__ = "attendances"
    __table_args__ = (
        UniqueConstraint("student_id", "lesson_id", name="uq_attendance_student_lesson"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # keldi, kelmadi, sababli
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Aloqalar
    student: Mapped["Student"] = relationship("Student", back_populates="attendances")
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="attendances")

    def __repr__(self) -> str:
        return f"<Attendance id={self.id} student={self.student_id} lesson={self.lesson_id} status={self.status}>"


class TeacherNote(Base):
    """O'qituvchi izohlari modeli."""

    __tablename__ = "teacher_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Aloqa
    student: Mapped["Student"] = relationship("Student", back_populates="notes")

    def __repr__(self) -> str:
        return f"<TeacherNote id={self.id} student_id={self.student_id}>"


class LessonComment(Base):
    """Darsga qoldirilgan izohlar modeli."""

    __tablename__ = "lesson_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Aloqa
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="comments")

    def __repr__(self) -> str:
        return f"<LessonComment id={self.id} lesson_id={self.lesson_id}>"


class SchoolInfo(Base):
    """Maktab haqidagi ma'lumotlar modeli (admin tomonidan tahrirlanadigan)."""

    __tablename__ = "school_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<SchoolInfo key={self.key}>"
