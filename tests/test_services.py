"""
Falcon Kibertexnology School - Xizmatlar (Services) qatlami testlari.
Baholash, reyting formulasi (qo'lda hisoblangan tekshiruv bilan),
davomat foizi va dars xizmati (mock lar bilan) to'liq sinovdan o'tkaziladi.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.models import User
from app.database.repositories import (
    LessonRepository,
    StudentRepository,
)
from app.database.session import init_db
from app.services import (
    AttendanceService,
    GradingService,
    LessonService,
    RatingService,
)


@pytest.fixture
async def async_session() -> AsyncSession:
    """Xotiradagi test bazasi fixture'i."""
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
async def test_grading_service(async_session: AsyncSession) -> None:
    """GradingService: o'rtacha ball, oxirgi 10 baho, haftalik/oylik o'rtacha."""
    student_repo = StudentRepository(async_session)
    student = await student_repo.create(
        full_name="Anvar Narzullayev", level="boshlang'ich", group_name="KOR-1"
    )

    grading = GradingService(async_session)

    # 1. Baho qo'shish
    await grading.add_grade(student.id, score=5, created_by=1, comment="A'lo")
    await grading.add_grade(student.id, score=3, created_by=1, comment="O'rtacha")
    await grading.add_grade(student.id, score=4, created_by=1, comment="Yaxshi")

    # 2. O'rtacha baho: (5 + 3 + 4) / 3 = 4.0
    avg = await grading.get_student_average(student.id)
    assert avg == 4.0

    # 3. Oxirgi baholar
    recent = await grading.get_recent_grades(student.id, limit=2)
    assert len(recent) == 2
    assert recent[0].score == 4  # Oxirgi qo'shilgan

    # 4. Haftalik va oylik o'rtacha
    weekly_avg = await grading.get_weekly_average(student.id)
    assert weekly_avg == 4.0
    monthly_avg = await grading.get_monthly_average(student.id)
    assert monthly_avg == 4.0

    # 5. Noto'g'ri baho uchun ValueError
    with pytest.raises(ValueError):
        await grading.add_grade(student.id, score=6, created_by=1)


@pytest.mark.asyncio
async def test_attendance_service(async_session: AsyncSession) -> None:
    """
    AttendanceService: belgilash, qayta belgilash,
    10 darsdan 3 ta qoldirganda 70% bo'lishi va nol dars holati.
    """
    student_repo = StudentRepository(async_session)
    lesson_repo = LessonRepository(async_session)
    att_service = AttendanceService(async_session)

    student = await student_repo.create(
        full_name="Dilshod Karimov", level="o'rta", group_name="KOR-2"
    )

    # Nol dars holati
    zero_stats = await att_service.get_student_stats(student.id)
    assert zero_stats["total"] == 0
    assert zero_stats["percentage"] == 0.0

    # 10 ta dars yaratish
    lessons = []
    for i in range(10):
        l = await lesson_repo.create(
            title=f"Dars {i + 1}",
            starts_at=datetime.now(UTC) - timedelta(days=10 - i),
        )
        lessons.append(l)

    # 7 tasiga 'keldi', 3 tasiga 'kelmadi'
    for i in range(7):
        await att_service.mark_attendance(student.id, lessons[i].id, "keldi")
    for i in range(7, 10):
        await att_service.mark_attendance(student.id, lessons[i].id, "kelmadi")

    stats = await att_service.get_student_stats(student.id)
    assert stats["total"] == 10
    assert stats["attended"] == 7
    assert stats["missed"] == 3
    # 7 / 10 * 100 = 70.0%
    assert stats["percentage"] == 70.0

    # Qayta belgilash: 9-darsni 'kelmadi' dan 'sababli' ga o'zgartiramiz
    await att_service.mark_attendance(student.id, lessons[9].id, "sababli")
    updated_stats = await att_service.get_student_stats(student.id)
    assert updated_stats["missed"] == 2
    assert updated_stats["excused"] == 1
    assert updated_stats["total"] == 10

    # Top absent report
    top_absent = await att_service.get_top_absent_report(10)
    assert len(top_absent) >= 1
    assert top_absent[0]["student_id"] == student.id
    assert top_absent[0]["missed_count"] == 2


@pytest.mark.asyncio
async def test_rating_service_with_hand_calculated_values(
    async_session: AsyncSession,
) -> None:
    """
    RatingService: 5 ta o'quvchi, har xil baho va davomat bilan.
    Kutilgan tartib qo'lda hisoblangan va assert qilinadi.
    Teng ball holatida baholar soni ko'pi ustun chiqishi tekshiriladi.
    Bo'sh bazada xato bermasligi sinovdan o'tadi.
    """
    student_repo = StudentRepository(async_session)
    lesson_repo = LessonRepository(async_session)
    grade_service = GradingService(async_session)
    att_service = AttendanceService(async_session)
    rating_service = RatingService(async_session)

    # 1. Bo'sh baza tekshiruvi
    empty_ratings = await rating_service.get_all_ratings()
    assert empty_ratings == []
    empty_msg = rating_service.format_rating_message(empty_ratings)
    assert "Hozircha reyting uchun ma'lumotlar mavjud emas" in empty_msg

    # 10 ta dars yaratamiz
    lessons = []
    for i in range(10):
        l = await lesson_repo.create(title=f"Dars #{i + 1}", starts_at=datetime.now(UTC))
        lessons.append(l)

    # 5 ta o'quvchi:
    # S1: baholar=[5, 5, 5] (avg=5.0), davomat=10/10 (100%) -> ball = 5.0*0.7 + 1.0*1.5 = 5.0
    # S2: baholar=[4, 4] (avg=4.0), davomat=8/10 (80%) -> ball = 4.0*0.7 + 0.8*1.5 = 4.0 (count=2)
    # S3: baholar=[5, 4] (avg=4.5), davomat=6/10 (60%) -> ball = 4.5*0.7 + 0.6*1.5 = 4.05
    # S4: baholar=[3, 3, 3, 3] (avg=3.0), davomat=10/10 (100%) -> ball = 3.0*0.7 + 1.0*1.5 = 3.6
    # S5: baholar=[4, 4, 4, 4] (avg=4.0), davomat=8/10 (80%) -> ball = 4.0 (count=4) - S2 bilan teng, lekin count ko'p!

    s1 = await student_repo.create("Student Bir", "boshlang'ich", "G1")
    for _ in range(3):
        await grade_service.add_grade(s1.id, 5, 1)
    for l in lessons:
        await att_service.mark_attendance(s1.id, l.id, "keldi")

    s2 = await student_repo.create("Student Ikki", "boshlang'ich", "G1")
    for _ in range(2):
        await grade_service.add_grade(s2.id, 4, 1)
    for i in range(8):
        await att_service.mark_attendance(s2.id, lessons[i].id, "keldi")
    for i in range(8, 10):
        await att_service.mark_attendance(s2.id, lessons[i].id, "kelmadi")

    s3 = await student_repo.create("Student Uch", "o'rta", "G2")
    await grade_service.add_grade(s3.id, 5, 1)
    await grade_service.add_grade(s3.id, 4, 1)
    for i in range(6):
        await att_service.mark_attendance(s3.id, lessons[i].id, "keldi")
    for i in range(6, 10):
        await att_service.mark_attendance(s3.id, lessons[i].id, "kelmadi")

    s4 = await student_repo.create("Student To'rt", "yuqori", "G3")
    for _ in range(4):
        await grade_service.add_grade(s4.id, 3, 1)
    for l in lessons:
        await att_service.mark_attendance(s4.id, l.id, "keldi")

    s5 = await student_repo.create("Student Besh", "o'rta", "G2")
    for _ in range(4):
        await grade_service.add_grade(s5.id, 4, 1)
    for i in range(8):
        await att_service.mark_attendance(s5.id, lessons[i].id, "keldi")
    for i in range(8, 10):
        await att_service.mark_attendance(s5.id, lessons[i].id, "kelmadi")

    # Reytingni olish
    ranked = await rating_service.get_all_ratings()
    assert len(ranked) == 5

    # 1-o'rin: Student Bir (ball: 5.0)
    assert ranked[0]["student_id"] == s1.id
    assert ranked[0]["total_score"] == 5.0
    assert ranked[0]["rank"] == 1

    # 2-o'rin: Student Uch (ball: 4.05)
    assert ranked[1]["student_id"] == s3.id
    assert ranked[1]["total_score"] == 4.05
    assert ranked[1]["rank"] == 2

    # 3-o'rin: Student Besh (ball: 4.0, count=4) -> Teng ball holatida baholar soni ko'p bo'lgani yuqori
    assert ranked[2]["student_id"] == s5.id
    assert ranked[2]["total_score"] == 4.0
    assert ranked[2]["grades_count"] == 4
    assert ranked[2]["rank"] == 3

    # 4-o'rin: Student Ikki (ball: 4.0, count=2)
    assert ranked[3]["student_id"] == s2.id
    assert ranked[3]["total_score"] == 4.0
    assert ranked[3]["grades_count"] == 2
    assert ranked[3]["rank"] == 4

    # 5-o'rin: Student To'rt (ball: 3.6)
    assert ranked[4]["student_id"] == s4.id
    assert ranked[4]["total_score"] == 3.6
    assert ranked[4]["rank"] == 5

    # Format matnida emojilar to'g'ri chiqishi
    msg = rating_service.format_rating_message(ranked)
    assert "🥇" in msg
    assert "🥈" in msg
    assert "🥉" in msg
    assert "Student Bir" in msg


@pytest.mark.asyncio
async def test_lesson_service_workflow(async_session: AsyncSession) -> None:
    """
    LessonService: dars yaratish, boshlash (bildirishnomalar mock bilan tekshiriladi),
    tugatish, faol dars bo'lmaganda javob va invite link mock tekshiruvi.
    """
    lesson_service = LessonService(async_session)

    # Bazaga foydalanuvchilar qo'shamiz
    u1 = User(telegram_id=1001, full_name="Ota 1", role="parent", is_active=True)
    u2 = User(telegram_id=1002, full_name="Ota 2", role="parent", is_active=True)
    async_session.add_all([u1, u2])
    await async_session.commit()

    # 1. Dars yaratish
    starts = datetime.now(UTC) + timedelta(hours=1)
    lesson = await lesson_service.create_lesson(
        title="Koreys tili 5-dars: Fe'l zamonlari",
        starts_at=starts,
        created_by=999,
    )
    assert lesson.id is not None
    assert lesson.status == "rejalashtirilgan"

    # Faol dars hozircha yo'q
    active, sched = await lesson_service.get_current_or_next_lesson()
    assert active is None
    assert sched is not None
    assert sched.id == lesson.id

    # 2. Darsni boshlash (Mock bot bilan)
    mock_bot = MagicMock()
    mock_invite = MagicMock()
    mock_invite.invite_link = "https://t.me/+testInviteHash123"
    mock_bot.create_chat_invite_link = AsyncMock(return_value=mock_invite)
    mock_bot.send_message = AsyncMock()

    started_lesson, link, count = await lesson_service.start_lesson(
        bot=mock_bot, lesson_id=lesson.id, group_id=-1001234567890
    )
    assert started_lesson is not None
    assert started_lesson.status == "davom_etmoqda"
    assert link == "https://t.me/+testInviteHash123"
    assert count == 2  # 2 ta faol foydalanuvchiga yuborildi
    assert mock_bot.send_message.call_count == 2

    # Endi faol dars bor
    active2, _ = await lesson_service.get_current_or_next_lesson()
    assert active2 is not None
    assert active2.id == lesson.id

    # 3. Darsga izoh qoldirish
    comment = await lesson_service.add_comment(
        lesson_id=lesson.id, telegram_id=1001, text="Dars juda tushunarli bo'ldi!"
    )
    assert comment.id is not None
    comments = await lesson_service.get_comments(lesson.id)
    assert len(comments) == 1

    # 4. Darsni tugatish
    ended = await lesson_service.end_lesson(lesson.id)
    assert ended is not None
    assert ended.status == "tugagan"
    assert ended.ended_at is not None

    # Endi yana faol dars yo'q
    active3, _ = await lesson_service.get_current_or_next_lesson()
    assert active3 is None
