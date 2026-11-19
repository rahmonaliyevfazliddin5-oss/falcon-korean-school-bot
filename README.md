# 🦅 Falcon Kibertexnology School — Telegram Bot & O'quv Markaz Mini App

Ushbu loyiha **"Falcon Kibertexnology School"** o'quv markazining koreys tili kurslari uchun ishlab chiqilgan zamonaviy, xavfsiz va to'liq avtomatlashtirilgan Telegram bot hamda **Telegram Mini App (WebApp)** boshqaruv tizimi hisoblanadi.

---

## 🚀 Asosiy Imkoniyatlar

### 1. 📱 O'qituvchi Boshqaruv Mini App'i (Faqat Admin uchun)
- **Haftalik jadval:** Dushanba dan Shanbagacha (6 kun). Yakshanba tanlab bo'lmaydi.
- **Kunlik davomat:** Katta toggle tugmalari (✅ Keldi / ❌ Kelmadi). "Saqlash va yuborish" orqali barcha faol obunachilarga chiroyli formatda avtomatik xabarnoma boradi.
- **Uyga vazifa bahosi:** 0 dan 10 gacha ball tezkor tugmalari va izoh.
- **"Vazifa qilmadi" tugmasi:** Bir bosishda bahoni 0 qilib, +10 000 so'm (`FINE_AMOUNT`) jarima yozadi. Qayta bosilsa jarimani bekor qiladi.
- **Qarz va to'lovlar:** Joriy qarzlar ro'yxati (qarzdorlar eng yuqorida). "To'lov qabul qilish" tugmasi: `"Qarz 100 000 → to'landi 10 000 → qoldi 90 000 so'm"`. To'lovlar tarixi va oxirgi to'lovni bekor qilish imkoni.
- **Xavfsizlik:** Serverda har bir so'rov Telegram `initData` orqali HMAC-SHA256 bilan tekshiriladi (24 soatdan eski so'rovlar rad etiladi). Begona foydalanuvchilar (ota-onalar) Mini App'ni ochsa, faqat markaziy logo ko'rinadi.

### 2. 🏆 Haftalik Reyting (Botda)
- Botdagi doimiy **"🏆 Reyting"** reply-tugmasi.
- Eng so'nggi haftaning uyga vazifa baholari bo'yicha **TOP-4** reytingni ko'rsatadi:
  ```text
  🏆 Reyting (haftalik)
  🥇 1. Ism Familiya , 48 ball
  🥈 2. Ism Familiya , 45 ball
  🥉 3. Ism Familiya , 41 ball
  4. Ism Familiya , 39 ball

  Agarda farzandingiz bu qatorda bo'lmasa, farzandingiz ustida ko'proq ishlashi kerak!
  ```
- Reyting xabarida qarz, jarima yoki davomat ma'lumotlari mutlaqo bo'lmaydi.

### 3. 🎥 Video Dars va Guruh Nazorati
- Video dars boshlanganda barcha obunachilarga taklif havolasi tarqatiladi.
- Kontent himoyasi (anti-screenshot, anti-forwarding).

---

## 🛠 Texnik Stek
- **Python:** 3.11+
- **Telegram Bot:** `aiogram 3.x`
- **Mini App & Web Server:** `aiohttp` (HTML5, CSS3, Vanilla JS, Telegram WebApp SDK)
- **Ma'lumotlar bazasi:** `aiosqlite` + `SQLAlchemy 2.0 (async)`
- **Vazifalar rejalashtiruvchisi:** `APScheduler`
- **Sifat nazorati & Testlar:** `pytest`, `pytest-asyncio`, `ruff`

---

## 📁 Loyiha Tuzilmasi

```text
falcon_bot/
├── api/                         # Mini App REST API
│   ├── auth.py                  # HMAC-SHA256 initData tekshiruvi va admin himoyasi
│   └── routes.py                # O'quvchilar, davomat, baho, qarz va to'lov yo'llari
├── app/
│   ├── main.py                  # Bot va aiohttp serverini birgalikda ishga tushirish
│   ├── config.py                # Pydantic-settings konfiguratsiyasi
│   ├── database/                # Baza modellari va omborlari
│   ├── handlers/                # Admin, foydalanuvchi va reyting handlerlari
│   ├── keyboards/               # Tugmalar va WebAppInfo
│   ├── middlewares/             # Throttling va autentifikatsiya
│   └── utils/                   # Scheduler, xavfsizlik va zaxiralash
├── static/                      # Mini App frontend fayllari
│   ├── index.html               # Asosiy HTML (Telegram WebApp)
│   ├── app.js                   # Frontend mantiq va API integratsiyasi
│   ├── styles.css               # Telegram mavzusiga moslashuvchan dizayn
│   └── logo.png                 # O'quv markaz logotipi
├── tests/                       # 55 ta to'liq avtomatlashtirilgan testlar
├── db.py                        # Mini App uchun aiosqlite ma'lumotlar bazasi boshqaruvi
├── config.py                    # Root sozlamalar eksporti
├── deploy.sh                    # VPS serverga avtomat o'rnatish skripti
├── requirements.txt             # Barcha bog'liqliklar
├── .env.example                 # Muhit o'zgaruvchilari andozasi
└── README.md                    # Loyiha qo'llanmasi
```

---

## ⚙️ O'rnatish va Sozlash

### 1. Virtual muhit yaratish va faollashtirish
```bash
python -m venv venv

# Linux / MacOS:
source venv/bin/activate

# Windows:
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
Fayl ichidagi qiymatlarni to'ldiring:
```env
BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
ADMIN_IDS=12345678,87654321
DATABASE_URL=sqlite+aiosqlite:///./falcon_school.db
LESSON_GROUP_ID=
LOG_LEVEL=INFO
PORT=8080
FINE_AMOUNT=10000
WEBAPP_URL=https://your-domain.com
```

### 4. Bot va Mini App'ni ishga tushirish
```bash
python -m app.main
```
Bu buyruq:
- Telegram botni tinglash rejimiga tushiradi (`polling`).
- Mini App API va statik web serverini `http://0.0.0.0:8080` manzilida ishga tushiradi.
- Fon vazifalari (Scheduler) ni yoqadi.

---

## 🎨 O'quv Markaz Logotipini Almashtirish

Mini App yuqori qismida va obunachilar oynasida ko'rinadigan logotipni o'zingizning haqiqiy logotipingizga almashtirish juda oson:

1. O'zingizning logotip rasmingizni tayyorlang (format: `.png`, shaffof fonli bo'lishi tavsiya etiladi).
2. Uni `static/logo.png` nomi bilan saqlab, loyihaning `static/` papkasidagi mavjud `logo.png` ustiga yozing:
   ```bash
   cp /path/to/your_logo.png static/logo.png
   ```
3. Mini App'ni yangilaganingizda yangi logotip markazda toza va chiroyli bo'lib chiqadi.

---

## 🧪 Qo'lda Sinash Bosqichlari (Manual Testing)

Loyiha to'liq tayyor bo'lgach, uni quyidagi ketma-ketlikda qo'lda sinab ko'rishingiz mumkin:

1. **Botda ro'yxatdan o'tish:**
   - Botga kiring va `/start` bosing.
   - Menyuda "🏆 Reyting" tugmasi chiqadi.
2. **Admin sifatida kirish:**
   - `/admin` buyrug'ini yuboring va `07070707` parolini kiriting.
   - Admin menyusi ochiladi.
3. **Mini App ni brauzerda yoki Telegramda ochish:**
   - Brauzerda: `http://localhost:8080` manziliga kiring (agar admin bo'lmagan foydalanuvchi kabi kirilsa, faqat logo chiqadi).
   - Telegramda: Admin menyusidagi "📱 Mini App" tugmasi orqali kiring.
4. **Davomat belgilash:**
   - Dushanbadan Shanbagacha istalgan kunni tanlang.
   - O'quvchilar qarshisidagi "✅ Keldi / ❌ Kelmadi" tugmalarini bosing.
   - "Saqlash va yuborish" ni bosing. Bot barcha foydalanuvchilarga davomat jadvalini yuboradi.
5. **Uyga vazifa baholash va Jarima:**
   - "Baho" tabiga o'ting.
   - 0 dan 10 gacha ball bering.
   - Biror o'quvchida "Vazifa qilmadi" tugmasini bosing: ball 0 bo'lib, +10 000 so'm jarima qo'shiladi.
6. **Qarz va to'lovlarni tekshirish:**
   - "Qarz" tabiga o'ting. Jarimasi bor o'quvchilar yuqorida chiqadi.
   - "To'lov" tugmasini bosib, to'langan summani kiriting (masalan, 10 000).
   - "Qarz 100 000 → to'landi 10 000 → qoldi 90 000 so'm" xabarnomasi chiqadi va qarz kamayadi.
7. **Reytingni tekshirish:**
   - Botda "🏆 Reyting" tugmasini bosing. O'sha haftada eng ko'p ball to'plagan TOP-4 o'quvchi emojilar bilan chiqadi.
