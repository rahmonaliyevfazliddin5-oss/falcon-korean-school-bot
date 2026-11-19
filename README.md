# 🦅 Falcon Kibertexnology School — Koreys tili darslari Telegram Boti

Ushbu loyiha **"Falcon Kibertexnology School"** o'quv markazining koreys tili kurslari uchun ishlab chiqilgan zamonaviy, xavfsiz va to'liq avtomatlashtirilgan Telegram bot hisoblanadi.

Loyiha toza arxitektura (**Handler -> Service -> Repository -> Database**) tamoyillari asosida qurilgan bo'lib, o'quvchilar, ota-onalar va o'qituvchilar (adminlar) o'rtasidagi ta'lim jarayonini osonlashtiradi.

---

## 🛠 Texnik Stek
- **Dasturlash tili:** Python 3.11+
- **Asinxron Telegram freymvorki:** `aiogram 3.x`
- **ORM va Ma'lumotlar bazasi:** `SQLAlchemy 2.0 (async)` + `aiosqlite` (PostgreSQL ga osongina ko'chirish mumkin)
- **Konfiguratsiya va Validatsiya:** `pydantic-settings`, `python-dotenv`
- **Rejalashtiruvchi (Scheduler):** `APScheduler` (15 daqiqa oldin dars eslatmalari va kunlik zaxira nusxalar)
- **Eksport va Hisobot:** `openpyxl` (Excel .xlsx formatida eksport)
- **Testlash va Sifat nazorati:** `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy`

---

## 📁 Loyiha Tuzilmasi

```text
falcon_bot/
├── app/
│   ├── main.py                  # Botni ishga tushirish, xatoliklar boshqaruvi va fon jarayonlari
│   ├── config.py                # Pydantic sozlamalari (.env o'qish)
│   ├── database/
│   │   ├── models.py            # SQLAlchemy 2.0 async modellari (User, Student, Grade, Attendance...)
│   │   ├── session.py           # Engine, Sessionmaker va init_db()
│   │   └── repositories/        # CRUD operatsiyalari (Repository pattern)
│   ├── handlers/
│   │   ├── common.py            # /start, /admin, /export, /checkgroup
│   │   ├── admin/               # O'quvchilar, baholash, davomat, izohlar, video darslar, statistika
│   │   └── parent/              # Farzandim, baholar, davomat, izohlar, reyting, dars
│   ├── keyboards/               # Inline va Reply klaviaturalar (CallbackData fabriklari)
│   ├── middlewares/             # Autentifikatsiya va 1 soniyalik Throttling (Anti-flood)
│   ├── services/                # Biznes mantiq (Grading, Attendance, Rating, Lessons)
│   ├── states/                  # FSM holatlari
│   └── utils/                   # Xavfsizlik nazorati, Excel eksport, Backup va Scheduler
├── tests/                       # To'liq avtomatlashtirilgan testlar to'plami
├── docker-compose.yml           # Docker orqali bir buyruq bilan ko'tarish
├── Dockerfile                   # Xavfsiz non-root foydalanuvchili konteyner
├── requirements.txt             # Barcha bog'liqliklar
├── .env.example                 # Muhit o'zgaruvchilari andozasi
└── README.md                    # Loyiha qo'llanmasi
```

---

## ⚙️ O'rnatish va Sozlash

### 1. Repozitoriyni yuklab olish va virtual muhitni yoqish
```bash
cd falcon_bot
python -m venv venv

# Linux / MacOS:
source venv/bin/activate

# Windows (PowerShell):
venv\Scripts\Activate.ps1
```

### 2. Bog'liqliklarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. `.env` faylini sozlash
`.env.example` dan nusxa olib `.env` faylini yarating:
```bash
cp .env.example .env
```
Fayl ichidagi o'zgaruvchilarni to'ldiring:
```env
BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
ADMIN_IDS=12345678,87654321
DATABASE_URL=sqlite+aiosqlite:///./falcon_school.db
LESSON_GROUP_ID=-1001234567890
LOG_LEVEL=INFO
```
> **Muhim:** Bot tokeni va admin ID lari kodga hech qachon yozilmaydi, faqat `.env` orqali uzatiladi.

### 4. Botni ishga tushirish
```bash
python -m app.main
```

---

## 🎥 Video Dars Guruhi va Kontent Himoyasi (Anti-Screenshot/Recording)

Telegram Bot API xavfsizlik cheklovlari tufayli bot bevosita video chatni boshlay olmaydi. Shu sababli quyidagi qulay tizim joriy qilingan:

1. **Guruh yaratish:** Darslar uchun yopiq Telegram guruhi yarating.
2. **Botni guruhga qo'shish va Admin qilish:**
   - Botni guruhga a'zo qilib qo'shing.
   - Guruh boshqaruviga o'tib, botga **Administrator** huquqlarini bering (Ayniqsa: *Guruhga taklif havolalarini yaratish* huquqi zarur).
3. **Kontentni saqlash va ekran yozib olishdan himoya:**
   - Telegram guruh sozlamalarini oching: **Guruh turi (Group Type)** -> **Yopiq guruh (Private Group)**.
   - Pastdagi **"Kontentni saqlashni cheklash" (Restrict saving content)** bandini **YOQING**.
   - Ushbu sozlama o'quvchilarga video darslarni va materiallarni skrinshot qilish, saqlab olish yoki boshqalarga forward qilishni taqiqlaydi.
4. **Xavfsizlikni tekshirish:**
   - Botda admin sifatida `/checkgroup` buyrug'ini yuboring.
   - Bot guruhda adminligi va kontent cheklovi yoqilganligini avtomatik tekshirib xabar beradi.

---

## 🔒 Xavfsizlik Mexanizmlari (Security Architecture)

1. **2 Bosqichli Admin Kirishi:**
   - `/admin` buyrug'i bosilganda bot shaxsiy ID ni so'raydi.
   - Kiritilgan ID ham `ADMIN_IDS` ro'yxatida bo'lishi, ham xabarni yuborgan foydalanuvchining haqiqiy `message.from_user.id` siga teng bo'lishi shart!
   - 3 marta noto'g'ri urinish amalga oshirilsa, foydalanuvchi **10 daqiqaga to'liq bloklanadi** va xavfsizlik logi yoziladi.
2. **IDOR (Insecure Direct Object Reference) Himoyasi:**
   - Ota-ona yoki o'quvchi faqat va faqat ma'muriyat tomonidan o'ziga biriktirilgan farzand ma'lumotlarini (baho, davomat, o'qituvchi izohi) ko'ra oladi.
3. **Protect Content:**
   - Barcha bot xabarlari `protect_content=True` bilan jo'natiladi (forward qilish va saqlash bloklangan).
4. **Throttling (Anti-flood):**
   - 1 soniyada 1 tadan ortiq so'rov yuborish avtomatik to'xtatiladi.
5. **SQL Injection himoyasi:**
   - Barcha so'rovlar faqat SQLAlchemy 2.0 ORM orqali parametrlangan holda bajariladi.

---

## 🚀 Serverga Joylash (Deployment)

### Usul 1: Docker va Docker Compose (Tavsiya etiladi)

Loyiha non-root foydalanuvchisi (`falconuser`) bilan xavfsiz konteynerlashtirilgan.

```bash
# Konteynerni fonda ishga tushirish
docker-compose up -d --build

# Loglarni jonli kuzatish
docker-compose logs -f

# To'xtatish
docker-compose down
```

### Usul 2: Linux Systemd Xizmati sifatida

`/etc/systemd/system/falcon_bot.service` faylini yarating:

```ini
[Unit]
Description=Falcon Kibertexnology School Telegram Bot
After=network.target

[Service]
Type=simple
User=falconuser
WorkingDirectory=/opt/falcon_bot
ExecStart=/opt/falcon_bot/venv/bin/python -m app.main
Restart=always
RestartSec=5
EnvironmentFile=/opt/falcon_bot/.env

[Install]
WantedBy=multi-user.target
```

Xizmatni faollashtirish:
```bash
sudo systemctl daemon-reload
sudo systemctl enable falcon_bot
sudo systemctl start falcon_bot
sudo systemctl status falcon_bot
```

---

## 🧪 Testlarni Ishga Tushirish

Barcha funksional, xavfsizlik va integratsion testlarni ishga tushirish uchun:

```bash
pytest -v --cov=app
```
