# ================================
# WB_DevSoulBot Dockerfile
# ================================

# Базовый образ Python 3.11 (стабильная версия для aiogram)
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Создаём рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Указываем токен как переменную окружения
# (Railway/Render подставит через ENV)
ENV BOT_TOKEN=${BOT_TOKEN}
ENV ADMIN_ID=${ADMIN_ID}
ENV CHAT_ID=${CHAT_ID}

# Команда запуска
CMD ["python", "bot.py"]
