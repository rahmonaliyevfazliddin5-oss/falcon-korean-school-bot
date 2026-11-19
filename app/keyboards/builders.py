"""
Falcon Kibertexnology School - Klaviaturalar generatori.
Reply va Inline tugmalar toza uslubda va CallbackData orqali yasaladi.
Admin va Foydalanuvchi ko'rinishlari to'liq ajratilgan.
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.database.models import Lesson, Student, TeacherNote
from app.keyboards.callbacks import (
    AttendanceCallback,
    GradeCallback,
    LessonControlCallback,
    NavCallback,
    NoteActionCallback,
    StudentActionCallback,
    UserNavCallback,
    UserStudentCallback,
)


def get_main_menu_keyboard(role: str = "user") -> ReplyKeyboardMarkup:
    """
    Foydalanuvchi roliga (admin yoki oddiy foydalanuvchi) qarab asosiy menyu Reply klaviaturasi.
    """
    if role == "admin":
        keyboard = [
            [
                KeyboardButton(text="👥 O'quvchilar"),
                KeyboardButton(text="⭐ Baholash"),
            ],
            [
                KeyboardButton(text="📋 Davomat"),
                KeyboardButton(text="📝 Izohlar"),
            ],
            [
                KeyboardButton(text="🎥 Video dars"),
                KeyboardButton(text="🏆 Reyting"),
            ],
            [
                KeyboardButton(text="📊 Statistika"),
            ],
        ]
    else:
        keyboard = [
            [
                KeyboardButton(text="👥 O'quvchilar"),
                KeyboardButton(text="🏆 Reyting"),
            ],
            [
                KeyboardButton(text="🎥 Hozirgi dars"),
                KeyboardButton(text="💬 Dars haqida izoh"),
            ],
            [
                KeyboardButton(text="ℹ️ Maktab haqida"),
            ],
        ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Kerakli bo'limni tanlang...",
    )


# ==================== ADMIN KEYBOARDS ====================


def get_students_pagination_keyboard(
    students: list[Student],
    page: int,
    total_count: int,
    page_size: int = 8,
    search: str | None = None,
) -> InlineKeyboardMarkup:
    """Admin uchun o'quvchilar ro'yxati sahifalash bilan (8 tadan)."""
    buttons: list[list[InlineKeyboardButton]] = []

    for st in students:
        btn_text = f"👤 {st.full_name} ({st.group_name})"
        cb = StudentActionCallback(action="view", student_id=st.id).pack()
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=cb)])

    total_pages = max(1, (total_count + page_size - 1) // page_size)
    nav_row: list[InlineKeyboardButton] = []

    if page > 0:
        prev_cb = NavCallback(target="students", page=page - 1, search=search).pack()
        nav_row.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=prev_cb))

    nav_row.append(
        InlineKeyboardButton(
            text=f"📄 {page + 1}/{total_pages}",
            callback_data=NavCallback(target="students_noop", page=page).pack(),
        )
    )

    if (page + 1) * page_size < total_count:
        next_cb = NavCallback(target="students", page=page + 1, search=search).pack()
        nav_row.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=next_cb))

    if nav_row:
        buttons.append(nav_row)

    control_row = [
        InlineKeyboardButton(
            text="➕ O'quvchi qo'shish",
            callback_data=NavCallback(target="add_student", page=0).pack(),
        ),
        InlineKeyboardButton(
            text="🔍 Qidirish",
            callback_data=NavCallback(target="search_student", page=0).pack(),
        ),
    ]
    if search:
        control_row.append(
            InlineKeyboardButton(
                text="❌ Filtrni tozalash",
                callback_data=NavCallback(target="students", page=0).pack(),
            )
        )
    buttons.append(control_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_student_card_keyboard(student_id: int) -> InlineKeyboardMarkup:
    """Admin uchun o'quvchi kartochkasi boshqaruv tugmalari."""
    buttons = [
        [
            InlineKeyboardButton(
                text="⭐ Baholash",
                callback_data=StudentActionCallback(action="grade", student_id=student_id).pack(),
            ),
            InlineKeyboardButton(
                text="📋 Davomat",
                callback_data=StudentActionCallback(action="att", student_id=student_id).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="📝 Izohlar",
                callback_data=StudentActionCallback(action="note", student_id=student_id).pack(),
            ),
            InlineKeyboardButton(
                text="🔗 Ota-ona ID",
                callback_data=StudentActionCallback(
                    action="link_parent", student_id=student_id
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="❌ Chiqarib tashlash",
                callback_data=StudentActionCallback(
                    action="delete_confirm", student_id=student_id
                ).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Ro'yxatga qaytish",
                callback_data=NavCallback(target="students", page=0).pack(),
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_delete_confirm_keyboard(student_id: int) -> InlineKeyboardMarkup:
    """Admin uchun o'quvchini chiqarib tashlashni tasdiqlash."""
    buttons = [
        [
            InlineKeyboardButton(
                text="⚠️ Ha, chiqarib tashlash",
                callback_data=StudentActionCallback(
                    action="delete_do", student_id=student_id
                ).pack(),
            ),
            InlineKeyboardButton(
                text="❌ Yo'q, bekor qilish",
                callback_data=StudentActionCallback(action="view", student_id=student_id).pack(),
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_grading_keyboard(student_id: int) -> InlineKeyboardMarkup:
    """1 dan 5 gacha baho qo'yish inline tugmalari."""
    scores_row = [
        InlineKeyboardButton(
            text=f"⭐️ {score}",
            callback_data=GradeCallback(action="score", student_id=student_id, score=score).pack(),
        )
        for score in range(1, 6)
    ]
    buttons = [
        scores_row,
        [
            InlineKeyboardButton(
                text="Bekor qilish",
                callback_data=StudentActionCallback(action="view", student_id=student_id).pack(),
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_attendance_marking_keyboard(
    lesson_id: int,
    students: list[Student],
    current_statuses: dict[int, str],
) -> InlineKeyboardMarkup:
    """Admin uchun dars davomatini belgilash klaviaturasi."""
    buttons: list[list[InlineKeyboardButton]] = []
    status_icons = {
        "keldi": "✅ Keldi",
        "kelmadi": "❌ Kelmadi",
        "sababli": "📄 Sababli",
    }

    for st in students:
        current_status = current_statuses.get(st.id, "")
        icon = status_icons.get(current_status, "⚪️ Belgilanmagan")
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{st.full_name[:15]}: {icon}",
                    callback_data=AttendanceCallback(
                        action="toggle",
                        lesson_id=lesson_id,
                        student_id=st.id,
                        status=current_status,
                    ).pack(),
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="✅ Hammasi keldi",
                callback_data=AttendanceCallback(action="mark_all", lesson_id=lesson_id).pack(),
            ),
            InlineKeyboardButton(
                text="🏁 Yakunlash",
                callback_data=AttendanceCallback(action="finish", lesson_id=lesson_id).pack(),
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_notes_keyboard(student_id: int, notes: list[TeacherNote]) -> InlineKeyboardMarkup:
    """Admin uchun izohlarni boshqarish."""
    buttons: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="➕ Yangi izoh qo'shish",
                callback_data=NoteActionCallback(action="add", student_id=student_id).pack(),
            )
        ]
    ]

    for n in notes[:5]:
        preview = n.text[:20] + "..." if len(n.text) > 20 else n.text
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"📝 {preview}",
                    callback_data=NoteActionCallback(
                        action="view_single", student_id=student_id, note_id=n.id
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="✏️",
                    callback_data=NoteActionCallback(
                        action="edit", student_id=student_id, note_id=n.id
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="🗑",
                    callback_data=NoteActionCallback(
                        action="delete", student_id=student_id, note_id=n.id
                    ).pack(),
                ),
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="◀️ O'quvchiga qaytish",
                callback_data=StudentActionCallback(action="view", student_id=student_id).pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_lesson_control_keyboard(active_lesson: Lesson | None) -> InlineKeyboardMarkup:
    """Admin uchun video darslarni boshqarish."""
    buttons: list[list[InlineKeyboardButton]] = []
    if active_lesson:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="⏹ Darsni tugatish",
                    callback_data=LessonControlCallback(
                        action="end", lesson_id=active_lesson.id
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="💬 Dars izohlari",
                    callback_data=LessonControlCallback(
                        action="view_comments", lesson_id=active_lesson.id
                    ).pack(),
                ),
            ]
        )
    else:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="➕ Yangi dars yaratish",
                    callback_data=LessonControlCallback(action="create").pack(),
                )
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text="▶️ Darsni boshlash",
                    callback_data=LessonControlCallback(action="start_choose").pack(),
                )
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text="💬 Oxirgi dars izohlari",
                    callback_data=LessonControlCallback(action="view_recent_comments").pack(),
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== ODDIY FOYDALANUVCHI KEYBOARDS ====================


def get_user_students_keyboard(
    students: list[Student],
    page: int,
    total_count: int,
    page_size: int = 8,
    search: str | None = None,
) -> InlineKeyboardMarkup:
    """Foydalanuvchi uchun o'quvchilar ro'yxati (faqat o'qish, shaxsiy ma'lumotlarsiz)."""
    buttons: list[list[InlineKeyboardButton]] = []

    for st in students:
        btn_text = f"👤 {st.full_name} ({st.group_name})"
        cb = UserStudentCallback(action="view", student_id=st.id).pack()
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=cb)])

    total_pages = max(1, (total_count + page_size - 1) // page_size)
    nav_row: list[InlineKeyboardButton] = []

    if page > 0:
        prev_cb = UserNavCallback(target="students", page=page - 1, search=search).pack()
        nav_row.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=prev_cb))

    nav_row.append(
        InlineKeyboardButton(
            text=f"📄 {page + 1}/{total_pages}",
            callback_data=UserNavCallback(target="students_noop", page=page).pack(),
        )
    )

    if (page + 1) * page_size < total_count:
        next_cb = UserNavCallback(target="students", page=page + 1, search=search).pack()
        nav_row.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=next_cb))

    if nav_row:
        buttons.append(nav_row)

    control_row = [
        InlineKeyboardButton(
            text="🔍 Qidirish",
            callback_data=UserNavCallback(target="search_student", page=0).pack(),
        )
    ]
    if search:
        control_row.append(
            InlineKeyboardButton(
                text="❌ Filtrni tozalash",
                callback_data=UserNavCallback(target="students", page=0).pack(),
            )
        )
    buttons.append(control_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_user_student_card_keyboard(student_id: int) -> InlineKeyboardMarkup:
    """Foydalanuvchi uchun o'quvchi kartochkasi tugmalari: faqat Izohlar va Davomat."""
    buttons = [
        [
            InlineKeyboardButton(
                text="📝 Izohlar",
                callback_data=UserStudentCallback(action="notes", student_id=student_id).pack(),
            ),
            InlineKeyboardButton(
                text="📋 Davomat",
                callback_data=UserStudentCallback(
                    action="attendance", student_id=student_id
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="◀️ Ro'yxatga qaytish",
                callback_data=UserNavCallback(target="students", page=0).pack(),
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_user_back_to_student_keyboard(student_id: int) -> InlineKeyboardMarkup:
    """O'quvchi kartochkasiga qaytish tugmasi."""
    buttons = [
        [
            InlineKeyboardButton(
                text="◀️ O'quvchiga qaytish",
                callback_data=UserStudentCallback(action="view", student_id=student_id).pack(),
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_user_rating_keyboard(
    page: int = 0,
    total_count: int = 0,
    page_size: int = 10,
    is_full: bool = False,
) -> InlineKeyboardMarkup:
    """Foydalanuvchi uchun reyting navigatsiyasi (TOP-10 va To'liq ro'yxat)."""
    buttons: list[list[InlineKeyboardButton]] = []

    if not is_full:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="📄 To'liq ro'yxat",
                    callback_data=UserNavCallback(target="rating_full", page=0).pack(),
                )
            ]
        )
    else:
        total_pages = max(1, (total_count + page_size - 1) // page_size)
        nav_row: list[InlineKeyboardButton] = []

        if page > 0:
            prev_cb = UserNavCallback(target="rating_full", page=page - 1).pack()
            nav_row.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=prev_cb))

        nav_row.append(
            InlineKeyboardButton(
                text=f"📄 {page + 1}/{total_pages}",
                callback_data=UserNavCallback(target="rating_noop", page=page).pack(),
            )
        )

        if (page + 1) * page_size < total_count:
            next_cb = UserNavCallback(target="rating_full", page=page + 1).pack()
            nav_row.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=next_cb))

        if nav_row:
            buttons.append(nav_row)

        buttons.append(
            [
                InlineKeyboardButton(
                    text="🏆 TOP-10 ga qaytish",
                    callback_data=UserNavCallback(target="rating_top", page=0).pack(),
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)
