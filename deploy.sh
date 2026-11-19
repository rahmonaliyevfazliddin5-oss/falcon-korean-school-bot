#!/usr/bin/env bash
# Falcon Kibertexnology School - Avtomatlashtirilgan o'rnatish skripti (Ubuntu / Debian VPS)

set -e

echo "=========================================================="
echo "🦅 Falcon Kibertexnology School Bot - Serverga o'rnatish"
echo "=========================================================="

# 1. Tizim paketlarini yangilash
echo "[1/6] Tizim paketlari yangilanmoqda..."
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git curl

# 2. Virtual muhit yaratish
echo "[2/6] Python virtual muhiti (venv) yaratilmoqda..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 3. Bog'liqliklarni o'rnatish
echo "[3/6] Bog'liqliklar o'rnatilmoqda..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. .env fayli tekshiruvi
echo "[4/6] .env fayli tekshirilmoqda..."
if [ ! -f ".env" ]; then
    echo "⚠️ .env fayli topilmadi. .env.example dan nusxa olinmoqda..."
    cp .env.example .env
    echo "❗ Iltimos, .env faylini ochib, BOT_TOKEN va ADMIN_IDS ni to'ldiring: nano .env"
fi

# 5. O'quvchilarni bazaga kiritish
echo "[5/6] O'quvchilar ma'lumotlar bazasiga kiritilmoqda..."
python3 seed_students.py

# 6. Systemd xizmatini sozlash
echo "[6/6] Systemd xizmati sozlanmoqda..."
CURRENT_DIR=$(pwd)
SERVICE_PATH="/etc/systemd/system/falcon_bot.service"

cat > $SERVICE_PATH <<EOF
[Unit]
Description=Falcon Kibertexnology School Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$CURRENT_DIR
EnvironmentFile=$CURRENT_DIR/.env
ExecStart=$CURRENT_DIR/venv/bin/python -m app.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable falcon_bot
systemctl restart falcon_bot

echo "=========================================================="
echo "✅ Bot muvaffaqiyatli ishga tushirildi!"
echo "Holatni tekshirish uchun: systemctl status falcon_bot"
echo "Loglarni ko'rish uchun: journalctl -u falcon_bot -f"
echo "=========================================================="
