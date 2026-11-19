"""
Falcon Kibertexnology School - Telegram Mini App Testlari.
1. initData tekshiruvi (to'g'ri/noto'g'ri/eskirgan)
2. Admin bo'lmagan foydalanuvchiga 403
3. Jarima to'planishi (10k + 10k = 20k)
4. Dublikat jarima bo'lmasligi
5. To'lovdan keyin qoldiq (100 000 - 10 000 = 90 000)
6. Ortiqcha to'lov rad etilishi
7. Reyting tartibi va top-4
8. Yakshanba rad etilishi
9. Davomat xabarida qarz ma'lumoti yo'qligi
"""

import hashlib
import hmac
import json
import time
import urllib.parse
from unittest.mock import AsyncMock, MagicMock

import pytest

import db
from api.auth import admin_required, validate_telegram_init_data
from app.config import settings


# Yordamchi: Telegram WebApp initData yaratuvchisi
def generate_test_init_data(
    user_id: int,
    bot_token: str,
    first_name: str = "Test",
    auth_date: int | None = None,
    tamper_hash: bool = False,
) -> str:
    date_val = int(time.time()) if auth_date is None else auth_date
    user_json = json.dumps({"id": user_id, "first_name": first_name}, separators=(",", ":"))

    params = {
        "auth_date": str(date_val),
        "query_id": "AAHdF6IzAAAAAN0XojP",
        "user": user_json,
    }

    # Data check string
    sorted_pairs = sorted(params.items(), key=lambda x: x[0])
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_pairs)

    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    cal_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if tamper_hash:
        cal_hash = "invalid_hash_1234567890abcdef"

    params["hash"] = cal_hash
    return urllib.parse.urlencode(params)


@pytest.fixture
async def temp_db(tmp_path):
    """Har bir test uchun alohida vaqtinchalik SQLite ma'lumotlar bazasi."""
    db_file = str(tmp_path / "test_miniapp.db")
    await db.init_db(db_path=db_file)
    return db_file


# ==================== 1. INITDATA TEKSHIRUVI ====================
def test_init_data_validation_valid():
    """To'g'ri initData tekshiruvdan muvaffaqiyatli o'tishi kerak."""
    token = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
    init_data = generate_test_init_data(user_id=777888, bot_token=token)

    is_valid, user = validate_telegram_init_data(init_data, bot_token=token)
    assert is_valid is True
    assert user["id"] == 777888
    assert user["first_name"] == "Test"


def test_init_data_validation_tampered():
    """Hash o'zgartirilgan bo'lsa rad etilishi kerak."""
    token = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
    init_data = generate_test_init_data(user_id=777888, bot_token=token, tamper_hash=True)

    is_valid, user = validate_telegram_init_data(init_data, bot_token=token)
    assert is_valid is False
    assert user == {}


def test_init_data_validation_expired():
    """24 soatdan (86400s) eski auth_date rad etilishi kerak."""
    token = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
    expired_date = int(time.time()) - 90000  # 25 soat oldin
    init_data = generate_test_init_data(user_id=777888, bot_token=token, auth_date=expired_date)

    is_valid, user = validate_telegram_init_data(init_data, bot_token=token)
    assert is_valid is False
    assert user == {}


# ==================== 2. ADMIN BO'LMAGANGA 403 ====================
@pytest.mark.asyncio
async def test_admin_required_forbidden_for_non_admin(monkeypatch):
    """Admin bo'lmagan oddiy obunachi/ota-ona API ga so'rov yuborsa 403 qaytishi kerak."""
    token = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
    monkeypatch.setattr(settings, "BOT_TOKEN", token)
    monkeypatch.setattr(settings, "ADMIN_IDS", "6156573399,8218024366")

    # Oddiy foydalanuvchi: 999000 (ADMIN_IDS da yo'q)
    non_admin_init = generate_test_init_data(user_id=999000, bot_token=token)

    @admin_required
    async def dummy_endpoint(request):
        from aiohttp import web

        return web.json_response({"ok": True})

    req = MagicMock()
    req.headers = {"X-Telegram-Init-Data": non_admin_init}
    req.query = {}

    resp = await dummy_endpoint(req)
    assert resp.status == 403

    # Admin foydalanuvchi: 6156573399 (ADMIN_IDS da bor)
    admin_init = generate_test_init_data(user_id=6156573399, bot_token=token)
    req.headers = {"X-Telegram-Init-Data": admin_init}

    resp_admin = await dummy_endpoint(req)
    assert resp_admin.status == 200


# ==================== 3. JARIMA TO'PLANISHI (10k + 10k = 20k) ====================
@pytest.mark.asyncio
async def test_fines_accumulation(temp_db):
    """Dushanba qilmadi +10k, Seshanba qilmadi +10k => qarz 20k to'planishi kerak."""
    student = await db.add_student("Bekzod Rahimov", db_path=temp_db)
    sid = student["id"]

    # Dushanba (2026-11-16) - vazifa qilmadi
    await db.save_grade_record(
        student_id=sid,
        date_str="2026-11-16",
        score=0,
        no_homework=True,
        fine_amount=10000,
        db_path=temp_db,
    )

    # Seshanba (2026-11-17) - vazifa qilmadi
    await db.save_grade_record(
        student_id=sid,
        date_str="2026-11-17",
        score=0,
        no_homework=True,
        fine_amount=10000,
        db_path=temp_db,
    )

    debt_info = await db.get_student_debt(sid, db_path=temp_db)
    assert debt_info["total_fines"] == 20000
    assert debt_info["debt"] == 20000


# ==================== 4. DUBLIKAT JARIMA BO'LMASLIGI ====================
@pytest.mark.asyncio
async def test_duplicate_fine_prevention(temp_db):
    """Bir o'quvchiga ayni bir kunda bir necha marta 'vazifa qilmadi' bosilsa ham faqat 1 ta jarima bo'lishi kerak."""
    student = await db.add_student("Temur Aliyev", db_path=temp_db)
    sid = student["id"]

    # 1-marta bosildi
    await db.save_grade_record(
        student_id=sid,
        date_str="2026-11-18",
        score=0,
        no_homework=True,
        fine_amount=10000,
        db_path=temp_db,
    )

    # Qayta bosildi (xuddi shu sana)
    await db.save_grade_record(
        student_id=sid,
        date_str="2026-11-18",
        score=0,
        no_homework=True,
        fine_amount=10000,
        db_path=temp_db,
    )

    debt_info = await db.get_student_debt(sid, db_path=temp_db)
    assert debt_info["total_fines"] == 10000
    assert debt_info["debt"] == 10000


# ==================== 5. TO'LOVDAN KEYIN QOLDIQ ====================
@pytest.mark.asyncio
async def test_payment_balance_calculation(temp_db):
    """Qarz 100 000 bo'lganda 10 000 to'lansa, qoldiq 90 000 bo'lishi va aniq yozuv chiqishi kerak."""
    student = await db.add_student("Jasur Boboyev", db_path=temp_db)
    sid = student["id"]

    # 100 000 so'm jarima hosil qilish (10 kun)
    days = [
        "2026-11-02",
        "2026-11-03",
        "2026-11-04",
        "2026-11-05",
        "2026-11-06",
        "2026-11-09",
        "2026-11-10",
        "2026-11-11",
        "2026-11-12",
        "2026-11-13",
    ]
    for d in days:
        await db.save_grade_record(
            student_id=sid,
            date_str=d,
            score=0,
            no_homework=True,
            fine_amount=10000,
            db_path=temp_db,
        )

    init_debt = await db.get_student_debt(sid, db_path=temp_db)
    assert init_debt["debt"] == 100000

    # 10 000 so'm to'lov qabul qilish
    result = await db.record_payment(student_id=sid, amount=10000, db_path=temp_db)
    assert result["old_debt"] == 100000
    assert result["paid"] == 10000
    assert result["remaining_debt"] == 90000

    # Xabar formati tekshiruvi: "Qarz 100 000 → to'landi 10 000 → qoldi 90 000 so'm"
    assert "Qarz 100 000 → to'landi 10 000 → qoldi 90 000 so'm" in result["message"]

    final_debt = await db.get_student_debt(sid, db_path=temp_db)
    assert final_debt["debt"] == 90000


# ==================== 6. ORTIQCHA TO'LOV RAD ETILISHI ====================
@pytest.mark.asyncio
async def test_overpayment_rejected(temp_db):
    """Qarzdan ortiqcha yoki manfiy/nol to'lov rad etilishi kerak."""
    student = await db.add_student("Sardor Qodirov", db_path=temp_db)
    sid = student["id"]

    # 10 000 qarz
    await db.save_grade_record(
        student_id=sid,
        date_str="2026-11-16",
        score=0,
        no_homework=True,
        fine_amount=10000,
        db_path=temp_db,
    )

    # 15 000 to'lashga urinish (qarzdan ko'p)
    with pytest.raises(ValueError, match="oshib ketmasligi kerak"):
        await db.record_payment(student_id=sid, amount=15000, db_path=temp_db)

    # 0 so'm to'lash
    with pytest.raises(ValueError, match="musbat"):
        await db.record_payment(student_id=sid, amount=0, db_path=temp_db)

    # Manfiy to'lov
    with pytest.raises(ValueError, match="musbat"):
        await db.record_payment(student_id=sid, amount=-5000, db_path=temp_db)


# ==================== 7. REYTING TARTIBI VA TOP-4 ====================
@pytest.mark.asyncio
async def test_weekly_top_4_rating(temp_db):
    """Haftalik reyting faqat TOP-4 ko'rsatishi, ball kamayish tartibida, teng bo'lsa alifbo bo'yicha saralanishi kerak."""
    s1 = await db.add_student("Anvar Zokirov", db_path=temp_db)  # 48 ball
    s2 = await db.add_student("Bobur Mirzayev", db_path=temp_db)  # 45 ball
    s3 = await db.add_student("Charos Karimova", db_path=temp_db)  # 41 ball
    s4 = await db.add_student("Davron Saidov", db_path=temp_db)  # 39 ball
    s5 = await db.add_student("Erkin Aliyev", db_path=temp_db)  # 20 ball (top-4 ga kirmaydi)

    # Hafta kunlari (2026-11-16 Dushanbadan 2026-11-21 Shanbagacha)
    # S1: 10 + 10 + 10 + 10 + 8 = 48 ball
    await db.save_grade_record(s1["id"], "2026-11-16", score=10, db_path=temp_db)
    await db.save_grade_record(s1["id"], "2026-11-17", score=10, db_path=temp_db)
    await db.save_grade_record(s1["id"], "2026-11-18", score=10, db_path=temp_db)
    await db.save_grade_record(s1["id"], "2026-11-19", score=10, db_path=temp_db)
    await db.save_grade_record(s1["id"], "2026-11-20", score=8, db_path=temp_db)

    # S2: 45 ball
    await db.save_grade_record(s2["id"], "2026-11-16", score=10, db_path=temp_db)
    await db.save_grade_record(s2["id"], "2026-11-17", score=10, db_path=temp_db)
    await db.save_grade_record(s2["id"], "2026-11-18", score=10, db_path=temp_db)
    await db.save_grade_record(s2["id"], "2026-11-19", score=10, db_path=temp_db)
    await db.save_grade_record(s2["id"], "2026-11-20", score=5, db_path=temp_db)

    # S3: 41 ball
    await db.save_grade_record(s3["id"], "2026-11-16", score=10, db_path=temp_db)
    await db.save_grade_record(s3["id"], "2026-11-17", score=10, db_path=temp_db)
    await db.save_grade_record(s3["id"], "2026-11-18", score=10, db_path=temp_db)
    await db.save_grade_record(s3["id"], "2026-11-19", score=10, db_path=temp_db)
    await db.save_grade_record(s3["id"], "2026-11-20", score=1, db_path=temp_db)

    # S4: 39 ball
    await db.save_grade_record(s4["id"], "2026-11-16", score=10, db_path=temp_db)
    await db.save_grade_record(s4["id"], "2026-11-17", score=10, db_path=temp_db)
    await db.save_grade_record(s4["id"], "2026-11-18", score=10, db_path=temp_db)
    await db.save_grade_record(s4["id"], "2026-11-19", score=9, db_path=temp_db)

    # S5: 20 ball
    await db.save_grade_record(s5["id"], "2026-11-16", score=10, db_path=temp_db)
    await db.save_grade_record(s5["id"], "2026-11-17", score=10, db_path=temp_db)

    text, top_list = await db.get_weekly_top_rating(ref_date_str="2026-11-19", db_path=temp_db)

    assert len(top_list) == 4
    assert top_list[0]["student_id"] == s1["id"]
    assert top_list[0]["total_score"] == 48

    assert top_list[1]["student_id"] == s2["id"]
    assert top_list[1]["total_score"] == 45

    assert top_list[2]["student_id"] == s3["id"]
    assert top_list[2]["total_score"] == 41

    assert top_list[3]["student_id"] == s4["id"]
    assert top_list[3]["total_score"] == 39

    # Format tekshiruvi
    assert "🥇 1. Anvar Zokirov , 48 ball" in text
    assert "🥈 2. Bobur Mirzayev , 45 ball" in text
    assert "🥉 3. Charos Karimova , 41 ball" in text
    assert "4. Davron Saidov , 39 ball" in text
    assert "Erkin Aliyev" not in text
    assert (
        "Agarda farzandingiz bu qatorda bo'lmasa, farzandingiz ustida ko'proq ishlashi kerak!"
        in text
    )


# ==================== 8. YAKSHANBA RAD ETILISHI ====================
@pytest.mark.asyncio
async def test_sunday_rejected(temp_db):
    """Yakshanba kuni tanlansa yoki so'rov yuborilsa rad etilishi kerak."""
    student = await db.add_student("Farrux Oripov", db_path=temp_db)
    sid = student["id"]

    # 2026-11-22 - Yakshanba
    assert db.is_sunday("2026-11-22") is True
    assert db.is_sunday("2026-11-21") is False  # Shanba

    with pytest.raises(ValueError, match="Yakshanba dars kuni emas"):
        await db.save_attendance_records(
            "2026-11-22", [{"student_id": sid, "present": 1}], db_path=temp_db
        )

    with pytest.raises(ValueError, match="Yakshanba dars kuni emas"):
        await db.save_grade_record(sid, "2026-11-22", score=5, db_path=temp_db)


# ==================== 9. DAVOMAT XABARIDA QARZ YO'QLIGI ====================
@pytest.mark.asyncio
async def test_attendance_message_no_debt_or_fines(temp_db, monkeypatch):
    """Davomat xabarida jarima yoki qarz haqida hech qanday ma'lumot bo'lmasligi shart."""
    monkeypatch.setattr(db, "get_db_path", lambda: temp_db)

    # O'quvchi va uning qarzi bor
    student = await db.add_student("G'ayrat Ergashev", db_path=temp_db)
    sid = student["id"]

    # O'quvchiga 50 000 so'm jarima qo'shamiz
    await db.save_grade_record(
        sid, "2026-11-16", score=0, no_homework=True, fine_amount=50000, db_path=temp_db
    )

    # Davomat belgilash
    await db.save_attendance_records(
        "2026-11-19", [{"student_id": sid, "present": 1}], db_path=temp_db
    )

    # Xabar matnini tekshirish uchun mock bot
    sent_texts = []
    mock_bot = AsyncMock()
    mock_bot.send_message.side_effect = lambda chat_id, text, **kw: sent_texts.append(text)

    # Foydalanuvchilar jadvaliga obunachi qo'shish
    import aiosqlite

    async with aiosqlite.connect(temp_db) as conn:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, telegram_id INTEGER, is_active INTEGER);"
        )
        await conn.execute("INSERT INTO users (telegram_id, is_active) VALUES (999111, 1);")
        await conn.commit()

    from api.routes import broadcast_attendance_message

    await broadcast_attendance_message(
        bot=mock_bot,
        date_str="2026-11-19",
        was_updated=False,
    )

    assert len(sent_texts) > 0
    msg_text = sent_texts[0]

    # Matn ichida davomat va o'quvchi bo'lishi kerak
    assert "📅 Davomat" in msg_text
    assert "19-noyabr 2026, Payshanba" in msg_text
    assert "G'ayrat Ergashev" in msg_text

    # XABAR ICHIDA JARIMA YOKI QARZ HAQIDA HECH QANDAY MA'LUMOT BO'LMASLIGI SHART
    lower_text = msg_text.lower()
    assert "qarz" not in lower_text
    assert "jarima" not in lower_text
    assert "so'm" not in lower_text
    assert "to'lov" not in lower_text
    assert "50 000" not in lower_text
