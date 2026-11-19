# Falcon Kibertexnology School - Telegram Bot Dockerfile
FROM python:3.11-slim

# Muhit o'zgaruvchilari
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Tizim paketlarini yangilash va kerakli kutubxonalar
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Bog'liqliklarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Xavfsizlik: Non-root foydalanuvchi yaratish
RUN useradd -m -u 1000 falconuser && \
    mkdir -p /app/data /app/backups /app/logs /app/exports && \
    chown -R falconuser:falconuser /app

# Loyiha kodlarini ko'chirish
COPY --chown=falconuser:falconuser . .

# Non-root foydalanuvchiga o'tish
USER falconuser

# Ma'lumotlar va zaxiralar uchun hajmlar (Volumes)
VOLUME ["/app/data", "/app/backups", "/app/logs"]

# Botni ishga tushirish
CMD ["python", "-m", "app.main"]
