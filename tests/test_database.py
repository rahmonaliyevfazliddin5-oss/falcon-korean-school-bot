"""
Falcon Kibertexnology School - Ma'lumotlar bazasi testlari.
Barcha modellar CRUD amallari, CheckConstraint va UniqueConstraint tekshiruvlari.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.models import Attendance, Grade
from app.database.repositories import (
    AttendanceRepository,
    GradeRepository,
    LessonCommentRepository,
    LessonRepository,
    SchoolInfoRepository,
    StudentRepository,
    TeacherNoteRepository,
    UserRepository,
)
from app.database.session import init_db


@pytest.fixture
async def async_session() -> AsyncSession:
    """Xotirada ishlovchi SQLite bazasi va asinxron sessiya fixture'i."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    await init_db(target_engine=engine)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_user_crud(async_session: AsyncSession) -> None:
    """User modeli CRUD amallarini tekshirish."""
    repo = UserRepository(async_session)

    # Create
    user = await repo.create_or_update(
        telegram_id=111222333, full_name="Ali Valiyev", role="parent"
    )
    assert user.id is not None
    assert user.telegram_id == 111222333
    assert user.role == "parent"

    # Read
    found = await repo.get_by_telegram_id(111222333)
    assert found is not None
    assert found.full_name == "Ali Valiyev"

    # Update role
    updated = await repo.set_role(111222333, "admin")
    assert updated is not None
    assert updated.role == "admin"

    # Delete
    deleted = await repo.delete(user.id)
    assert deleted is True
    assert await repo.get_by_telegram_id(111222333) is None


@pytest.mark.asyncio
async def test_student_crud(async_session: AsyncSession) -> None:
    """Student modeli CRUD va soft delete amallarini tekshirish."""
    repo = StudentRepository(async_session)

    # Create
    student = await repo.create(
        full_name="Kim Min Su",
        level="boshlang'ich",
        group_name="KOR-101",
        parent_telegram_id=999888,
    )
    assert student.id is not None
    assert student.is_active is True

    # Read
    found = await repo.get_by_id(student.id)
    assert found is not None
    assert found.full_name == "Kim Min Su"

    # Parent link read
    parent_students = await repo.get_by_parent_telegram_id(999888)
    assert len(parent_students) == 1
    assert parent_students[0].id == student.id

    # Soft delete
    soft_deleted = await repo.soft_delete(student.id)
    assert soft_deleted is True
    assert len(await repo.get_by_parent_telegram_id(999888)) == 0

    # Permanent delete
    perm_deleted = await repo.delete_permanent(student.id)
    assert perm_deleted is True
    assert await repo.get_by_id(student.id) is None


@pytest.mark.asyncio
async def test_lesson_crud(async_session: AsyncSession) -> None:
    """Lesson modeli CRUD amallarini tekshirish."""
    repo = LessonRepository(async_session)

    # Create
    starts = datetime.now(UTC)
    lesson = await repo.create(title="Hangul Alifbosi 1-dars", starts_at=starts, created_by=777)
    assert lesson.id is not None
    assert lesson.status == "rejalashtirilgan"

    # Read
    found = await repo.get_by_id(lesson.id)
    assert found is not None
    assert found.title == "Hangul Alifbosi 1-dars"

    # Update status to active
    active_lesson = await repo.update_status(lesson.id, "davom_etmoqda")
    assert active_lesson is not None
    assert active_lesson.status == "davom_etmoqda"

    current = await repo.get_active_lesson()
    assert current is not None
    assert current.id == lesson.id

    # Finish lesson
    finished = await repo.update_status(lesson.id, "tugagan")
    assert finished is not None
    assert finished.status == "tugagan"
    assert finished.ended_at is not None

    # Delete
    deleted = await repo.delete(lesson.id)
    assert deleted is True
    assert await repo.get_by_id(lesson.id) is None


@pytest.mark.asyncio
async def test_grade_crud_and_constraints(async_session: AsyncSession) -> None:
    """Grade modeli CRUD amallari va ball cheklovlari (CheckConstraint) tekshiruvi."""
    student_repo = StudentRepository(async_session)
    grade_repo = GradeRepository(async_session)

    student = await student_repo.create(
        full_name="Park Ji Sung", level="o'rta", group_name="KOR-201"
    )
    student_id = student.id

    # To'g'ri baho yaratish (1-5 oralig'ida)
    grade = await grade_repo.create(
        student_id=student_id, score=5, created_by=777, comment="A'lo natija!"
    )
    assert grade.id is not None
    assert grade.score == 5
    grade_id = grade.id

    # Read
    grades = await grade_repo.get_by_student_id(student_id)
    assert len(grades) == 1
    assert grades[0].comment == "A'lo natija!"

    # Score 6 qo'shilganda xato berishi kerak
    with pytest.raises(IntegrityError):
        invalid_high = Grade(
            student_id=student_id, score=6, created_by=777, comment="Noqonuniy ball"
        )
        async_session.add(invalid_high)
        await async_session.commit()
    await async_session.rollback()

    # Score 0 qo'shilganda xato berishi kerak
    with pytest.raises(IntegrityError):
        invalid_low = Grade(student_id=student_id, score=0, created_by=777, comment="Nol ball")
        async_session.add(invalid_low)
        await async_session.commit()
    await async_session.rollback()

    # Delete
    deleted = await grade_repo.delete(grade_id)
    assert deleted is True


@pytest.mark.asyncio
async def test_attendance_crud_and_duplicate_constraint(
    async_session: AsyncSession,
) -> None:
    """Attendance modeli CRUD va (student_id, lesson_id) unikal cheklovi tekshiruvi."""
    student_repo = StudentRepository(async_session)
    lesson_repo = LessonRepository(async_session)
    attendance_repo = AttendanceRepository(async_session)

    student = await student_repo.create(
        full_name="Lee Min Ho", level="yuqori", group_name="KOR-301"
    )
    lesson = await lesson_repo.create(title="Topik 2 Grammatika", starts_at=datetime.now(UTC))
    student_id = student.id
    lesson_id = lesson.id

    # 1. create_or_update orqali yaratish
    att = await attendance_repo.create_or_update(
        student_id=student_id, lesson_id=lesson_id, status="keldi"
    )
    assert att.id is not None
    assert att.status == "keldi"
    att_id = att.id

    # 2. Qayta belgilash (dublikat yaratmaydi, statusni yangilaydi)
    updated_att = await attendance_repo.create_or_update(
        student_id=student_id, lesson_id=lesson_id, status="sababli"
    )
    assert updated_att.id == att_id
    assert updated_att.status == "sababli"

    # 3. Model orqali to'g'ridan-to'g'ri dublikat kiritishga urinish UniqueConstraint xatosi berishi kerak
    with pytest.raises(IntegrityError):
        duplicate = Attendance(student_id=student_id, lesson_id=lesson_id, status="kelmadi")
        async_session.add(duplicate)
        await async_session.commit()
    await async_session.rollback()

    # Delete
    deleted = await attendance_repo.delete(att_id)
    assert deleted is True


@pytest.mark.asyncio
async def test_teacher_notes_and_comments(async_session: AsyncSession) -> None:
    """TeacherNote va LessonComment modellarini tekshirish."""
    student_repo = StudentRepository(async_session)
    lesson_repo = LessonRepository(async_session)
    note_repo = TeacherNoteRepository(async_session)
    comment_repo = LessonCommentRepository(async_session)

    student = await student_repo.create(
        full_name="Song Hye Kyo", level="o'rta", group_name="KOR-202"
    )
    lesson = await lesson_repo.create(title="Talaffuz mashqi", starts_at=datetime.now(UTC))

    # Teacher note
    note = await note_repo.create(
        student_id=student.id,
        text="Darsda juda faol qatnashdi.",
        created_by=777,
    )
    assert note.id is not None
    assert note.text == "Darsda juda faol qatnashdi."
    note_id = note.id

    # Update note
    updated_note = await note_repo.update(note_id, "Yangi izoh matni")
    assert updated_note is not None
    assert updated_note.text == "Yangi izoh matni"

    # Lesson comment
    comment = await comment_repo.create(
        lesson_id=lesson.id,
        telegram_id=123456,
        text="Ajoyib dars bo'ldi, rahmat!",
    )
    assert comment.id is not None
    assert comment.text == "Ajoyib dars bo'ldi, rahmat!"
    comment_id = comment.id

    comments = await comment_repo.get_by_lesson_id(lesson.id)
    assert len(comments) == 1

    # Cleanup
    assert await note_repo.delete(note_id) is True
    assert await comment_repo.delete(comment_id) is True


@pytest.mark.asyncio
async def test_school_info_repo(async_session: AsyncSession) -> None:
    """SchoolInfo ombori tekshiruvi."""
    repo = SchoolInfoRepository(async_session)

    # Standart matn mavjudligi
    info = await repo.get_info("about_school")
    assert "Falcon Kibertexnology School" in info

    # Yangilash
    updated = await repo.set_info("about_school", "Yangi maktab ma'lumotlari: Koreys tili markazi")
    assert updated.content == "Yangi maktab ma'lumotlari: Koreys tili markazi"

    reloaded = await repo.get_info("about_school")
    assert reloaded == "Yangi maktab ma'lumotlari: Koreys tili markazi"
