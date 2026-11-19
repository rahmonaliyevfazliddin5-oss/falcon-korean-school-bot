"""
Falcon Kibertexnology School - API Marshrutlari (api/routes.py).
Mini App uchun barcha RESTful API nuqtalari va ruxsatlar boshqaruvi.
"""

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiohttp import web

import db
from api.auth import admin_required, get_authenticated_user
from app.config import settings

logger = logging.getLogger(__name__)


def setup_routes(app: web.Application, bot: Bot) -> None:
    """Barcha API marshrutlarini aiohttp ilovasiga ulash."""
    app["bot"] = bot

    # Autentifikatsiya va profil
    app.router.add_get("/api/me", handle_get_me)

    # O'quvchilar
    app.router.add_get("/api/students", handle_get_students)
    app.router.add_post("/api/students", handle_add_student)
    app.router.add_put("/api/students/{id}", handle_update_student)
    app.router.add_delete("/api/students/{id}", handle_delete_student)

    # Davomat
    app.router.add_get("/api/attendance", handle_get_attendance)
    app.router.add_post("/api/attendance", handle_save_attendance)

    # Baholar va jarimalar
    app.router.add_get("/api/grades", handle_get_grades)
    app.router.add_post("/api/grades", handle_save_grade)

    # Qarz va to'lovlar
    app.router.add_get("/api/debts", handle_get_debts)
    app.router.add_get("/api/payments/{student_id}", handle_get_payments)
    app.router.add_post("/api/payments", handle_record_payment)
    app.router.add_delete("/api/payments/{student_id}/last", handle_cancel_last_payment)

    # Haftalik reyting
    app.router.add_get("/api/rating/weekly", handle_get_weekly_rating)


# ==================== ME ====================
async def handle_get_me(request: web.Request) -> web.Response:
    """Foydalanuvchining login va adminlik holatini tekshirish."""
    is_valid, is_admin, user_dict = get_authenticated_user(request)
    if not is_valid:
        return web.json_response(
            {"authenticated": False, "is_admin": False, "user": None},
            status=200,
        )

    return web.json_response(
        {
            "authenticated": True,
            "is_admin": is_admin,
            "user": user_dict,
        }
    )


# ==================== STUDENTS ====================
@admin_required
async def handle_get_students(request: web.Request) -> web.Response:
    """O'quvchilar ro'yxati (qidiruv va arxiv holati bilan)."""
    search = request.query.get("search", "").strip()
    active_str = request.query.get("active_only", "true").lower()
    active_only = active_str != "false"

    students = await db.get_students(active_only=active_only, search=search)
    return web.json_response({"students": students})


@admin_required
async def handle_add_student(request: web.Request) -> web.Response:
    """Yangi o'quvchi qo'shish."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Noto'g'ri JSON format."}, status=400)

    full_name = data.get("full_name", "").strip()
    if not full_name or len(full_name) < 2:
        return web.json_response(
            {"error": "O'quvchi ism-familiyasi kamida 2 ta belgidan iborat bo'lishi kerak."},
            status=400,
        )

    group_name = data.get("group_name", "Asosiy").strip() or "Asosiy"
    level = data.get("level", "boshlang'ich").strip() or "boshlang'ich"

    try:
        student = await db.add_student(full_name=full_name, group_name=group_name, level=level)
        return web.json_response({"success": True, "student": student}, status=201)
    except Exception as e:
        logger.error(f"O'quvchi qo'shishda xatolik: {e}")
        return web.json_response({"error": str(e)}, status=500)


@admin_required
async def handle_update_student(request: web.Request) -> web.Response:
    """O'quvchi ismini tahrirlash."""
    student_id_raw = request.match_info.get("id")
    try:
        student_id = int(student_id_raw)  # type: ignore
    except (ValueError, TypeError):
        return web.json_response({"error": "Noto'g'ri o'quvchi ID raqami."}, status=400)

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Noto'g'ri JSON format."}, status=400)

    full_name = data.get("full_name", "").strip()
    if not full_name or len(full_name) < 2:
        return web.json_response(
            {"error": "O'quvchi ism-familiyasi kamida 2 ta belgidan iborat bo'lishi kerak."},
            status=400,
        )

    updated = await db.update_student(student_id=student_id, full_name=full_name)
    if not updated:
        return web.json_response({"error": "O'quvchi topilmadi."}, status=404)

    return web.json_response({"success": True, "student": updated})


@admin_required
async def handle_delete_student(request: web.Request) -> web.Response:
    """O'quvchini arxivga o'tkazish (soft delete: is_active=0)."""
    student_id_raw = request.match_info.get("id")
    try:
        student_id = int(student_id_raw)  # type: ignore
    except (ValueError, TypeError):
        return web.json_response({"error": "Noto'g'ri o'quvchi ID raqami."}, status=400)

    archived = await db.archive_student(student_id=student_id)
    if not archived:
        return web.json_response({"error": "O'quvchi topilmadi."}, status=404)

    return web.json_response({"success": True, "message": "O'quvchi muvaffaqiyatli arxivlandi."})


# ==================== ATTENDANCE ====================
@admin_required
async def handle_get_attendance(request: web.Request) -> web.Response:
    """Tanlangan sana uchun davomat ro'yxatini olish."""
    date_str = request.query.get("date", "").strip()
    if not date_str:
        date_str = db.get_today_tashkent().strftime("%Y-%m-%d")

    try:
        if db.is_sunday(date_str):
            return web.json_response({"error": "Yakshanba dars kuni emas."}, status=400)
    except Exception:
        return web.json_response(
            {"error": "Noto'g'ri sana formati (YYYY-MM-DD talab qilinadi)."}, status=400
        )

    att_map = await db.get_attendance_for_date(date_str)
    return web.json_response({"date": date_str, "attendance": att_map})


@admin_required
async def handle_save_attendance(request: web.Request) -> web.Response:
    """
    Davomatni saqlash va bot orqali obunachilarga xabar yuborish.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Noto'g'ri JSON format."}, status=400)

    date_str = data.get("date", "").strip()
    items = data.get("items", [])
    send_broadcast = bool(data.get("send_broadcast", False))

    if not date_str:
        return web.json_response({"error": "Sana ko'rsatilishi shart."}, status=400)

    try:
        if db.is_sunday(date_str):
            return web.json_response({"error": "Yakshanba dars kuni emas."}, status=400)
    except Exception:
        return web.json_response({"error": "Noto'g'ri sana formati (YYYY-MM-DD)."}, status=400)

    if not isinstance(items, list):
        return web.json_response(
            {"error": "Davomat ro'yxati ro'yxat ko'rinishida bo'lishi kerak."}, status=400
        )

    count, was_updated = await db.save_attendance_records(date_str, items)

    # Agar xabar yuborish so'ralgan bo'lsa, fonda xabarnoma tarqatish
    if send_broadcast:
        bot: Bot = request.app["bot"]
        user_info = request.get("telegram_user", {})
        admin_id = int(user_info.get("id", 0)) if user_info.get("id") else None
        asyncio.create_task(
            broadcast_attendance_message(
                bot=bot,
                date_str=date_str,
                was_updated=was_updated,
                admin_telegram_id=admin_id,
            )
        )

    return web.json_response(
        {
            "success": True,
            "saved_count": count,
            "was_updated": was_updated,
            "broadcast_queued": send_broadcast,
            "message": "Davomat saqlandi"
            + (" va xabarnoma yuborilmoqda." if send_broadcast else "."),
        }
    )


async def broadcast_attendance_message(
    bot: Bot,
    date_str: str,
    was_updated: bool,
    admin_telegram_id: int | None = None,
) -> None:
    """
    Barcha faol foydalanuvchilarga davomat xabarini fonda yuborish.
    DIQQAT: Xabarda qarz yoki jarima haqida hech qanday ma'lumot bo'lmaydi!
    """
    try:
        date_formatted = db.format_date_uz(date_str)
        students = await db.get_students(active_only=True)
        att_map = await db.get_attendance_for_date(date_str)

        title = "📅 Davomat (Yangilandi)" if was_updated else "📅 Davomat"
        lines = [title, date_formatted, ""]

        for s in students:
            # Standart: 1 (keldi)
            present_val = att_map.get(s["id"], 1)
            icon = "✅" if present_val == 1 else "❌"
            lines.append(f"{icon} {s['full_name']}")

        text = "\n".join(lines)

        # Bazadagi barcha faol foydalanuvchilar (users jadvali)
        import aiosqlite

        async with aiosqlite.connect(db.get_db_path()) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT telegram_id FROM users WHERE is_active = 1;")
            users = await cursor.fetchall()

        sent_count = 0
        error_count = 0

        for u in users:
            tg_id = u["telegram_id"]
            try:
                await bot.send_message(chat_id=tg_id, text=text, protect_content=True)
                sent_count += 1
                await asyncio.sleep(0.05)
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                try:
                    await bot.send_message(chat_id=tg_id, text=text, protect_content=True)
                    sent_count += 1
                except Exception:
                    error_count += 1
            except TelegramForbiddenError:
                # Bot bloklangan bo'lsa, is_active=0 qilamiz
                async with aiosqlite.connect(db.get_db_path()) as conn2:
                    await conn2.execute(
                        "UPDATE users SET is_active = 0 WHERE telegram_id = ?;", (tg_id,)
                    )
                    await conn2.commit()
                error_count += 1
            except Exception as e:
                logger.warning(f"Davomat xabari yuborilmadi ({tg_id}): {e}")
                error_count += 1

        # Adminga qisqa hisobot
        if admin_telegram_id:
            try:
                report = (
                    f"📊 **Davomat xabarnomasi yuborildi:**\n"
                    f"📅 Sana: **{date_formatted}**\n\n"
                    f"✅ Yuborildi: **{sent_count} ta**\n"
                    f"❌ Xatolik / Bloklangan: **{error_count} ta**"
                )
                await bot.send_message(chat_id=admin_telegram_id, text=report, protect_content=True)
            except Exception as e:
                logger.warning(f"Adminga hisobot yuborishda xatolik: {e}")

    except Exception as exc:
        logger.error(f"Davomat xabarnomasi tarqatishda jiddiy xatolik: {exc}")


# ==================== GRADES & FINES ====================
@admin_required
async def handle_get_grades(request: web.Request) -> web.Response:
    """Tanlangan sana uchun baholar va jarimalar holatini olish."""
    date_str = request.query.get("date", "").strip()
    if not date_str:
        date_str = db.get_today_tashkent().strftime("%Y-%m-%d")

    try:
        if db.is_sunday(date_str):
            return web.json_response({"error": "Yakshanba dars kuni emas."}, status=400)
    except Exception:
        return web.json_response({"error": "Noto'g'ri sana formati (YYYY-MM-DD)."}, status=400)

    grades_map = await db.get_grades_for_date(date_str)
    return web.json_response({"date": date_str, "grades": grades_map})


@admin_required
async def handle_save_grade(request: web.Request) -> web.Response:
    """
    O'quvchiga baho qo'yish yoki 'Vazifa qilmadi' jarimasini belgilash/bekor qilish.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Noto'g'ri JSON format."}, status=400)

    student_id = data.get("student_id")
    date_str = data.get("date", "").strip()
    score_raw = data.get("score", 0)
    comment = data.get("comment")
    no_homework = bool(data.get("no_homework", False))

    if not student_id or not date_str:
        return web.json_response({"error": "O'quvchi va sana ko'rsatilishi shart."}, status=400)

    try:
        student_id = int(student_id)
        score = int(score_raw)
    except (ValueError, TypeError):
        return web.json_response(
            {"error": "O'quvchi ID va baho butun son bo'lishi kerak."}, status=400
        )

    try:
        if db.is_sunday(date_str):
            return web.json_response({"error": "Yakshanba dars kuni emas."}, status=400)
    except Exception:
        return web.json_response({"error": "Noto'g'ri sana formati (YYYY-MM-DD)."}, status=400)

    if score < 0 or score > 10:
        return web.json_response(
            {"error": "Baho 0 dan 10 gacha oraliqda bo'lishi kerak."}, status=400
        )

    try:
        result = await db.save_grade_record(
            student_id=student_id,
            date_str=date_str,
            score=score,
            comment=comment,
            no_homework=no_homework,
            fine_amount=settings.FINE_AMOUNT,
        )
        return web.json_response({"success": True, "grade": result})
    except Exception as e:
        logger.error(f"Bahoni saqlashda xatolik: {e}")
        return web.json_response({"error": str(e)}, status=400)


# ==================== DEBTS & PAYMENTS ====================
@admin_required
async def handle_get_debts(request: web.Request) -> web.Response:
    """Barcha o'quvchilarning qarz hisobotini olish (qarzdorlar yuqorida)."""
    debts = await db.get_all_debts()
    return web.json_response({"debts": debts})


@admin_required
async def handle_get_payments(request: web.Request) -> web.Response:
    """O'quvchining to'lovlar tarixini olish."""
    student_id_raw = request.match_info.get("student_id")
    try:
        student_id = int(student_id_raw)  # type: ignore
    except (ValueError, TypeError):
        return web.json_response({"error": "Noto'g'ri o'quvchi ID raqami."}, status=400)

    history = await db.get_payment_history(student_id)
    debt_info = await db.get_student_debt(student_id)
    return web.json_response({"student_id": student_id, "debt": debt_info, "payments": history})


@admin_required
async def handle_record_payment(request: web.Request) -> web.Response:
    """
    To'lov qabul qilish.
    Qoidalar:
    - Summa musbat butun son bo'lishi kerak.
    - Summa joriy qarzdan oshib ketmasligi kerak.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Noto'g'ri JSON format."}, status=400)

    student_id = data.get("student_id")
    amount = data.get("amount")

    if not student_id or amount is None:
        return web.json_response({"error": "O'quvchi va summa ko'rsatilishi shart."}, status=400)

    try:
        student_id = int(student_id)
        amount = int(amount)
    except (ValueError, TypeError):
        return web.json_response(
            {"error": "O'quvchi ID va summa butun son bo'lishi kerak."}, status=400
        )

    try:
        result = await db.record_payment(student_id=student_id, amount=amount)
        return web.json_response({"success": True, **result})
    except ValueError as val_err:
        return web.json_response({"error": str(val_err)}, status=400)
    except Exception as e:
        logger.error(f"To'lovni qayd etishda xatolik: {e}")
        return web.json_response({"error": str(e)}, status=500)


@admin_required
async def handle_cancel_last_payment(request: web.Request) -> web.Response:
    """Oxirgi to'lovni bekor qilish."""
    student_id_raw = request.match_info.get("student_id")
    try:
        student_id = int(student_id_raw)  # type: ignore
    except (ValueError, TypeError):
        return web.json_response({"error": "Noto'g'ri o'quvchi ID raqami."}, status=400)

    try:
        result = await db.cancel_last_payment(student_id=student_id)
        return web.json_response({"success": True, **result})
    except ValueError as val_err:
        return web.json_response({"error": str(val_err)}, status=400)
    except Exception as e:
        logger.error(f"To'lovni bekor qilishda xatolik: {e}")
        return web.json_response({"error": str(e)}, status=500)


# ==================== WEEKLY RATING ====================
async def handle_get_weekly_rating(request: web.Request) -> web.Response:
    """Haftalik reyting ma'lumotini olish."""
    date_str = request.query.get("date")
    text, top_students = await db.get_weekly_top_rating(ref_date_str=date_str)
    return web.json_response({"formatted_text": text, "top_students": top_students})
