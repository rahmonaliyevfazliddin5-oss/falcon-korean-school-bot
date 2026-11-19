"""
Falcon Kibertexnology School - O'quvchilarni bazaga kiritish skripti (Seed data).
Serverda bazani boshlang'ich 42 nafar o'quvchi bilan to'ldirish uchun ishlatiladi.
"""

import asyncio
import sys
from pathlib import Path

# Loyiha papkasini importlar uchun qo'shish
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.database.session import async_session_maker, init_db
from app.database.models import Student

STUDENTS_DATA = [
    {"full_name": "Odiljonov Biloliddin", "group_name": "9-sinf", "level": "o'rta"},
    {"full_name": "Maxmudov Faxriddin", "group_name": "8-sinf", "level": "boshlang'ich"},
    {"full_name": "Ibrohimov Dovutbek", "group_name": "10-sinf", "level": "yuqori"},
    {"full_name": "Egamberdiyev Inomjon", "group_name": "8-sinf", "level": "boshlang'ich"},
    {"full_name": "Komiljonov Ravshanbek", "group_name": "9-sinf", "level": "o'rta"},
    {"full_name": "Umaraliyev Umar Ali", "group_name": "10-sinf", "level": "yuqori"},
    {"full_name": "Xakimov Bexruzbek", "group_name": "9-sinf", "level": "o'rta"},
    {"full_name": "Irisov Javohir", "group_name": "10-sinf", "level": "yuqori"},
    {"full_name": "Nematjonov Xasanxon", "group_name": "9-sinf", "level": "o'rta"},
    {"full_name": "Yo‘ldashev Sarvarbek", "group_name": "10-sinf", "level": "yuqori"},
    {"full_name": "Abdurazzoqov Islombek", "group_name": "9-sinf", "level": "o'rta"},
    {"full_name": "Ortiqaliyev Raxmatillo", "group_name": "8-sinf", "level": "boshlang'ich"},
    {"full_name": "Abdunabiyev Boburjon", "group_name": "8-sinf", "level": "boshlang'ich"},
    {"full_name": "Alimov Axrorbek", "group_name": "10-sinf", "level": "yuqori"},
    {"full_name": "Aminov Olimjon", "group_name": "7-sinf", "level": "boshlang'ich"},
    {"full_name": "Ko‘charov Yashinbek", "group_name": "8-sinf", "level": "boshlang'ich"},
    {"full_name": "Ergashev Nuriddin", "group_name": "10-sinf", "level": "yuqori"},
    {"full_name": "Muxammadsodiq", "group_name": "10-sinf", "level": "yuqori"},
    {"full_name": "Raxmatullayev Fazliddin", "group_name": "11-sinf", "level": "yuqori"},
    {"full_name": "Muxammadiyev Muxammadjon", "group_name": "7-sinf", "level": "boshlang'ich"},
    {"full_name": "Mo‘minov Suxrobbek", "group_name": "10-sinf", "level": "yuqori"},
    {"full_name": "Shahobiddinova Farangiz", "group_name": "7-sinf", "level": "boshlang'ich"},
    {"full_name": "Mo‘ydinova Farzona", "group_name": "7-sinf", "level": "boshlang'ich"},
    {"full_name": "Abdumalikov Ilmiddin", "group_name": "7-sinf", "level": "boshlang'ich"},
    {"full_name": "Shavkatov Raxmatillo", "group_name": "Guruhsiz", "level": "o'rta"},
    {"full_name": "Karimov Bexruzbek", "group_name": "Guruhsiz", "level": "o'rta"},
    {"full_name": "Zuhriddinov Azizbek", "group_name": "8-sinf", "level": "boshlang'ich"},
    {"full_name": "Sardor", "group_name": "Guruhsiz", "level": "o'rta"},
    {"full_name": "Abdullayev Nurmuxammad", "group_name": "10-sinf", "level": "yuqori"},
    {"full_name": "Xamidullayev Akbarshox", "group_name": "10-sinf", "level": "yuqori"},
    {"full_name": "To‘lqinov Alisherbek", "group_name": "7-sinf", "level": "boshlang'ich"},
    {"full_name": "Jumanazarov Shoxruxbek", "group_name": "9-sinf", "level": "o'rta"},
    {"full_name": "Yo‘ldashev Muxammadrizo", "group_name": "9-sinf", "level": "o'rta"},
    {"full_name": "Tojiboev Islombek", "group_name": "10-sinf", "level": "yuqori"},
    {"full_name": "Xudoynazarov Baxtiyorjon", "group_name": "10-sinf", "level": "yuqori"},
    {"full_name": "Mo‘minjonov Jumanazar", "group_name": "Guruhsiz", "level": "o'rta"},
    {"full_name": "Maxmudov Azamatjon", "group_name": "10-sinf", "level": "yuqori"},
    {"full_name": "Abduqaxxorova Sanobarxon", "group_name": "9-sinf", "level": "o'rta"},
    {"full_name": "Mo‘ydinov Saydillo", "group_name": "Guruhsiz", "level": "o'rta"},
    {"full_name": "Inomova Umidaxon", "group_name": "10-sinf", "level": "yuqori"},
    {"full_name": "Soibjonova Ruqiyaxon", "group_name": "9-sinf", "level": "o'rta"},
    {"full_name": "Tilaganboyev Og‘abek", "group_name": "Guruhsiz", "level": "o'rta"},
]


async def seed_students() -> None:
    """O'quvchilarni bazaga qo'shish."""
    print("Baza jadvallari tekshirilmoqda...")
    await init_db()

    async with async_session_maker() as session:
        added_count = 0
        for item in STUDENTS_DATA:
            stmt = select(Student).where(Student.full_name == item["full_name"])
            existing = (await session.execute(stmt)).scalar_one_or_none()

            if not existing:
                student = Student(
                    full_name=item["full_name"],
                    group_name=item["group_name"],
                    level=item["level"],
                    parent_telegram_id=None,
                    user_telegram_id=None,
                    is_active=True,
                )
                session.add(student)
                added_count += 1

        await session.commit()
        print(f"Muvaffaqiyatli yakunlandi! Qo'shilgan yangi o'quvchilar: {added_count} ta.")


if __name__ == "__main__":
    asyncio.run(seed_students())
