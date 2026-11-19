"""
Falcon Kibertexnology School - Ma'lumotlar bazasi boshqaruvi (db.py).
Mini App uchun o'quvchilar, kunlik davomat, uyga vazifa baholari,
jarimalar va to'lovlar jadvallarini asinxron boshqaradi (aiosqlite).
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import aiosqlite

from app.config import settings

logger = logging.getLogger(__name__)

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")

MONTHS_UZ = [
    "",
    "yanvar",
    "fevral",
    "mart",
    "aprel",
    "may",
    "iyun",
    "iyul",
    "avgust",
    "sentabr",
    "oktabr",
    "noyabr",
    "dekabr",
]

DAYS_UZ = [
    "Dushanba",
    "Seshanba",
    "Chorshanba",
    "Payshanba",
    "Juma",
    "Shanba",
    "Yakshanba",
]


def get_db_path() -> str:
    """SQLite fayl yo'lini aniqlash."""
    url = settings.DATABASE_URL
    if "///" in url:
        return url.split("///")[-1]
    return "falcon_school.db"


def get_today_tashkent() -> date:
    """Toshkent vaqti bo'yicha bugungi sanani olish."""
    return datetime.now(TASHKENT_TZ).date()


def is_sunday(d: date | str) -> bool:
    """Berilgan sana Yakshanba ekanligini tekshirish."""
    if isinstance(d, str):
        d = datetime.strptime(d, "%Y-%m-%d").date()
    return d.weekday() == 6


def format_date_uz(d: date | str) -> str:
    """Sanani o'zbekcha chiroyli formatda chiqarish (masalan: 19-noyabr 2026, Payshanba)."""
    if isinstance(d, str):
        d = datetime.strptime(d, "%Y-%m-%d").date()
    day = d.day
    month = MONTHS_UZ[d.month]
    year = d.year
    weekday = DAYS_UZ[d.weekday()]
    return f"{day}-{month} {year}, {weekday}"


async def init_db(db_path: str | None = None) -> None:
    """Mini App jadvallarini yaratish va migratsiyalarni bajarish."""
    path = db_path or get_db_path()
    async with aiosqlite.connect(path) as db:
        await db.execute("PRAGMA foreign_keys = ON;")

        # 1. students jadvali (agar yo'q bo'lsa)
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                level TEXT DEFAULT 'boshlang''ich',
                group_name TEXT DEFAULT 'Asosiy',
                parent_telegram_id INTEGER,
                user_telegram_id INTEGER,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 2. attendance jadvali (kunlik davomat)
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                present INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, date),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
            );
            """
        )

        # 3. grades jadvali (uyga vazifa bahosi: 0-10 ball va izoh)
        # Agar eski bo'sh grades jadvali mavjud bo'lsa va unda 'date' ustuni bo'lmasa, uni almashtiramiz
        cursor = await db.execute("PRAGMA table_info(grades);")
        existing_cols = [row[1] for row in await cursor.fetchall()]
        if existing_cols and "date" not in existing_cols:
            logger.info("Eski grades jadvali yangi formatga yangilanmoqda...")
            await db.execute("DROP TABLE IF EXISTS grades;")

        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                score INTEGER NOT NULL DEFAULT 0,
                comment TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, date),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
            );
            """
        )

        # 4. fines jadvali (kunlik jarimalar: 10 000 so'm)
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS fines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                amount INTEGER NOT NULL DEFAULT 10000,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(student_id, date),
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
            );
            """
        )

        # 5. payments jadvali (qabul qilingan to'lovlar tarixi)
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
            );
            """
        )

        await db.commit()
    logger.info("Mini App ma'lumotlar bazasi jadvallari muvaffaqiyatli tekshirildi.")


# ==================== STUDENTS ====================
async def get_students(
    db_path: str | None = None, active_only: bool = True, search: str = ""
) -> list[dict[str, Any]]:
    """O'quvchilar ro'yxatini olish."""
    path = db_path or get_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT id, full_name, level, group_name, is_active, created_at FROM students"
        conditions: list[str] = []
        params: list[Any] = []

        if active_only:
            conditions.append("is_active = 1")
        if search:
            conditions.append("full_name LIKE ?")
            params.append(f"%{search.strip()}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY full_name COLLATE NOCASE ASC;"
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def add_student(
    full_name: str,
    group_name: str = "Asosiy",
    level: str = "boshlang'ich",
    db_path: str | None = None,
) -> dict[str, Any]:
    """Yangi o'quvchi qo'shish."""
    name = full_name.strip()
    if not name:
        raise ValueError("O'quvchi ism-familiyasi bo'sh bo'lishi mumkin emas.")

    path = db_path or get_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            INSERT INTO students (full_name, group_name, level, is_active)
            VALUES (?, ?, ?, 1)
            RETURNING id, full_name, group_name, level, is_active, created_at;
            """,
            (name, group_name, level),
        )
        row = await cursor.fetchone()
        await db.commit()
        return dict(row) if row else {}


async def update_student(
    student_id: int, full_name: str, db_path: str | None = None
) -> dict[str, Any] | None:
    """O'quvchi ma'lumotlarini tahrirlash."""
    name = full_name.strip()
    if not name:
        raise ValueError("O'quvchi ism-familiyasi bo'sh bo'lishi mumkin emas.")

    path = db_path or get_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            UPDATE students
            SET full_name = ?
            WHERE id = ?
            RETURNING id, full_name, group_name, level, is_active, created_at;
            """,
            (name, student_id),
        )
        row = await cursor.fetchone()
        await db.commit()
        return dict(row) if row else None


async def archive_student(student_id: int, db_path: str | None = None) -> bool:
    """O'quvchini arxivga o'tkazish (soft delete: is_active=0)."""
    path = db_path or get_db_path()
    async with aiosqlite.connect(path) as db:
        cursor = await db.execute("UPDATE students SET is_active = 0 WHERE id = ?;", (student_id,))
        await db.commit()
        return cursor.rowcount > 0


# ==================== ATTENDANCE ====================
async def get_attendance_for_date(date_str: str, db_path: str | None = None) -> dict[int, int]:
    """Berilgan sana uchun davomat holatini olish: {student_id: present_int}."""
    if is_sunday(date_str):
        raise ValueError("Yakshanba dars kuni emas.")

    path = db_path or get_db_path()
    async with aiosqlite.connect(path) as db:
        cursor = await db.execute(
            "SELECT student_id, present FROM attendance WHERE date = ?;", (date_str,)
        )
        rows = await cursor.fetchall()
        return {r[0]: r[1] for r in rows}


async def save_attendance_records(
    date_str: str, items: list[dict[str, Any]], db_path: str | None = None
) -> tuple[int, bool]:
    """
    Davomatni saqlash (upsert).
    Qaytaradi: (saqlanganlar_soni, avval_mavjud_edi).
    """
    if is_sunday(date_str):
        raise ValueError("Yakshanba dars kuni emas.")

    path = db_path or get_db_path()
    async with aiosqlite.connect(path) as db:
        # Avval bu sana uchun yozuv bo'lganligini tekshirish
        cursor = await db.execute("SELECT COUNT(*) FROM attendance WHERE date = ?;", (date_str,))
        existing_count = (await cursor.fetchone())[0]
        was_previously_saved = existing_count > 0

        for item in items:
            student_id = int(item["student_id"])
            present = 1 if bool(item.get("present", 1)) else 0
            await db.execute(
                """
                INSERT INTO attendance (student_id, date, present, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(student_id, date) DO UPDATE SET present = excluded.present;
                """,
                (student_id, date_str, present),
            )
        await db.commit()
        return len(items), was_previously_saved


# ==================== GRADES & FINES ====================
async def get_grades_for_date(
    date_str: str, db_path: str | None = None
) -> dict[int, dict[str, Any]]:
    """Berilgan sana uchun baholar va jarima holatini olish: {student_id: {score, comment, has_fine}}."""
    if is_sunday(date_str):
        raise ValueError("Yakshanba dars kuni emas.")

    path = db_path or get_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        # Baholar
        cursor = await db.execute(
            "SELECT student_id, score, comment FROM grades WHERE date = ?;", (date_str,)
        )
        grade_rows = await cursor.fetchall()
        grades_map = {r["student_id"]: dict(r) for r in grade_rows}

        # Jarimalar
        f_cursor = await db.execute(
            "SELECT student_id, amount FROM fines WHERE date = ?;", (date_str,)
        )
        fine_rows = await f_cursor.fetchall()
        fines_map = {r[0]: r[1] for r in fine_rows}

        # Birlashtirish
        result: dict[int, dict[str, Any]] = {}
        all_ids = set(grades_map.keys()) | set(fines_map.keys())
        for sid in all_ids:
            g = grades_map.get(sid, {})
            result[sid] = {
                "score": g.get("score", 0),
                "comment": g.get("comment", "") or "",
                "has_fine": sid in fines_map,
                "fine_amount": fines_map.get(sid, 0),
            }
        return result


async def save_grade_record(
    student_id: int,
    date_str: str,
    score: int,
    comment: str | None = None,
    no_homework: bool = False,
    fine_amount: int | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """
    Uyga vazifa bahosi va jarimani saqlash:
    - no_homework=True: score=0 qilinadi va fines jadvaliga FINE_AMOUNT qo'shiladi (UNIQUE student_id, date).
    - no_homework=False: fines jadvalidan o'chiriladi.
    """
    if is_sunday(date_str):
        raise ValueError("Yakshanba dars kuni emas.")

    if score < 0 or score > 10:
        raise ValueError("Baho 0 dan 10 gacha bo'lishi kerak.")

    fine_amt = fine_amount if fine_amount is not None else settings.FINE_AMOUNT
    comment_clean = comment.strip() if comment else None

    if no_homework:
        score = 0

    path = db_path or get_db_path()
    async with aiosqlite.connect(path) as db:
        # Bahoni saqlash
        await db.execute(
            """
            INSERT INTO grades (student_id, date, score, comment, created_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(student_id, date) DO UPDATE SET
                score = excluded.score,
                comment = excluded.comment;
            """,
            (student_id, date_str, score, comment_clean),
        )

        # Jarimani boshqarish
        if no_homework:
            await db.execute(
                """
                INSERT INTO fines (student_id, date, amount, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(student_id, date) DO UPDATE SET amount = excluded.amount;
                """,
                (student_id, date_str, fine_amt),
            )
        else:
            await db.execute(
                "DELETE FROM fines WHERE student_id = ? AND date = ?;",
                (student_id, date_str),
            )

        await db.commit()

    return {
        "student_id": student_id,
        "date": date_str,
        "score": score,
        "comment": comment_clean,
        "no_homework": no_homework,
    }


# ==================== DEBTS & PAYMENTS ====================
async def get_student_debt(student_id: int, db_path: str | None = None) -> dict[str, int]:
    """O'quvchining joriy qarzdorlik hisobini olish."""
    path = db_path or get_db_path()
    async with aiosqlite.connect(path) as db:
        f_cur = await db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM fines WHERE student_id = ?;",
            (student_id,),
        )
        total_fines = (await f_cur.fetchone())[0]

        p_cur = await db.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE student_id = ?;",
            (student_id,),
        )
        total_payments = (await p_cur.fetchone())[0]

        debt = max(0, total_fines - total_payments)
        return {
            "total_fines": int(total_fines),
            "total_payments": int(total_payments),
            "debt": int(debt),
        }


async def get_all_debts(db_path: str | None = None) -> list[dict[str, Any]]:
    """Barcha o'quvchilar qarzdorligini olish (qarzdorlar eng yuqorida)."""
    path = db_path or get_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        query = """
            SELECT
                s.id as student_id,
                s.full_name,
                s.group_name,
                COALESCE(f.total_fines, 0) as total_fines,
                COALESCE(p.total_payments, 0) as total_payments,
                (COALESCE(f.total_fines, 0) - COALESCE(p.total_payments, 0)) as debt
            FROM students s
            LEFT JOIN (
                SELECT student_id, SUM(amount) as total_fines
                FROM fines
                GROUP BY student_id
            ) f ON s.id = f.student_id
            LEFT JOIN (
                SELECT student_id, SUM(amount) as total_payments
                FROM payments
                GROUP BY student_id
            ) p ON s.id = p.student_id
            WHERE s.is_active = 1
            ORDER BY debt DESC, s.full_name COLLATE NOCASE ASC;
        """
        cursor = await db.execute(query)
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["total_fines"] = int(d["total_fines"])
            d["total_payments"] = int(d["total_payments"])
            d["debt"] = max(0, int(d["debt"]))
            result.append(d)
        return result


async def get_payment_history(student_id: int, db_path: str | None = None) -> list[dict[str, Any]]:
    """O'quvchi to'lovlar tarixini olish."""
    path = db_path or get_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, student_id, amount, created_at
            FROM payments
            WHERE student_id = ?
            ORDER BY created_at DESC, id DESC;
            """,
            (student_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def record_payment(
    student_id: int, amount: int, db_path: str | None = None
) -> dict[str, Any]:
    """
    To'lovni qabul qilish va saqlash:
    - To'lov summasi musbat bo'lishi shart.
    - To'lov summasi joriy qarzdan oshib ketmasligi shart.
    Qaytaradi: {old_debt, paid, remaining_debt, message}
    """
    if amount <= 0:
        raise ValueError("To'lov summasi musbat butun son bo'lishi kerak.")

    debt_info = await get_student_debt(student_id, db_path=db_path)
    current_debt = debt_info["debt"]

    if current_debt <= 0:
        raise ValueError("Ushbu o'quvchida to'lash uchun qarzdorlik mavjud emas.")

    if amount > current_debt:
        raise ValueError(
            f"To'lov summasi joriy qarzdan ({current_debt:,} so'm) oshib ketmasligi kerak.".replace(
                ",", " "
            )
        )

    path = db_path or get_db_path()
    async with aiosqlite.connect(path) as db:
        await db.execute(
            """
            INSERT INTO payments (student_id, amount, created_at)
            VALUES (?, ?, CURRENT_TIMESTAMP);
            """,
            (student_id, amount),
        )
        await db.commit()

    old_debt = current_debt
    paid = amount
    remaining_debt = old_debt - paid

    old_fmt = f"{old_debt:,}".replace(",", " ")
    paid_fmt = f"{paid:,}".replace(",", " ")
    rem_fmt = f"{remaining_debt:,}".replace(",", " ")
    message_str = f"Qarz {old_fmt} → to'landi {paid_fmt} → qoldi {rem_fmt} so'm"

    return {
        "student_id": student_id,
        "old_debt": old_debt,
        "paid": paid,
        "remaining_debt": remaining_debt,
        "message": message_str,
    }


async def cancel_last_payment(student_id: int, db_path: str | None = None) -> dict[str, Any]:
    """O'quvchining oxirgi to'lovini bekor qilish (o'chirish)."""
    path = db_path or get_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, amount FROM payments
            WHERE student_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1;
            """,
            (student_id,),
        )
        last_payment = await cursor.fetchone()
        if not last_payment:
            raise ValueError("Bekor qilish uchun to'lov topilmadi.")

        payment_id = last_payment["id"]
        deleted_amount = last_payment["amount"]
        await db.execute("DELETE FROM payments WHERE id = ?;", (payment_id,))
        await db.commit()

    debt_info = await get_student_debt(student_id, db_path=db_path)
    return {
        "student_id": student_id,
        "deleted_payment_id": payment_id,
        "refunded_amount": deleted_amount,
        "current_debt": debt_info["debt"],
    }


# ==================== WEEKLY RATING ====================
async def get_weekly_top_rating(
    ref_date_str: str | None = None, db_path: str | None = None
) -> tuple[str, list[dict[str, Any]]]:
    """
    Eng so'nggi yangilangan haftalik ball bo'yicha TOP-4 reytingni olish.
    Hafta: Dushanba dan Shanba gacha.
    Ballar: uyga vazifa baholari yig'indisi.
    Qaytaradi: (formatted_message, top_students_list)
    """
    path = db_path or get_db_path()
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row

        # Agar sana berilmagan bo'lsa, eng so'nggi baho qo'yilgan sanani olamiz
        target_date = None
        if ref_date_str:
            target_date = datetime.strptime(ref_date_str, "%Y-%m-%d").date()
        else:
            cur = await db.execute("SELECT MAX(date) FROM grades WHERE score > 0;")
            max_date_row = await cur.fetchone()
            if max_date_row and max_date_row[0]:
                target_date = datetime.strptime(max_date_row[0], "%Y-%m-%d").date()
            else:
                target_date = get_today_tashkent()

        # Dushanba va Shanba oralig'ini topish
        # weekday: 0=Mon, ..., 5=Sat, 6=Sun
        weekday = target_date.weekday()
        if weekday == 6:
            # Agar Yakshanba bo'lsa, oldingi kun (Shanba) haftasini olamiz
            monday = target_date - timedelta(days=6)
        else:
            monday = target_date - timedelta(days=weekday)
        saturday = monday + timedelta(days=5)

        mon_str = monday.strftime("%Y-%m-%d")
        sat_str = saturday.strftime("%Y-%m-%d")

        query = """
            SELECT
                s.id as student_id,
                s.full_name,
                SUM(g.score) as total_score
            FROM students s
            JOIN grades g ON s.id = g.student_id
            WHERE g.date >= ? AND g.date <= ? AND s.is_active = 1
            GROUP BY s.id, s.full_name
            HAVING total_score > 0
            ORDER BY total_score DESC, s.full_name COLLATE NOCASE ASC
            LIMIT 4;
        """
        cursor = await db.execute(query, (mon_str, sat_str))
        rows = await cursor.fetchall()
        top_students = [dict(r) for r in rows]

        if not top_students:
            return (
                "🏆 **Reyting (haftalik)**\n\nHozircha reyting yo'q.",
                [],
            )

        medals = ["🥇 1.", "🥈 2.", "🥉 3.", "4."]
        lines = ["🏆 **Reyting (haftalik)**\n"]
        for i, st in enumerate(top_students):
            prefix = medals[i]
            lines.append(f"{prefix} {st['full_name']} , {st['total_score']} ball")

        lines.append(
            "\nAgarda farzandingiz bu qatorda bo'lmasa, farzandingiz ustida ko'proq ishlashi kerak!"
        )
        formatted_text = "\n".join(lines)
        return formatted_text, top_students
