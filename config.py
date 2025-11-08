"""
Конфигурация бота.
Загружает токен из переменных окружения.
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения. Создайте .env файл с BOT_TOKEN=your_token")

# URL для webhook (если используется webhook вместо polling)
# На Render.com это будет что-то вроде: https://your-bot-name.onrender.com/webhook
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Порт для веб-сервера (по умолчанию 8000, Render.com автоматически определяет порт)
WEBHOOK_PORT = int(os.getenv("PORT", os.getenv("WEBHOOK_PORT", "8000")))

# Путь для webhook (по умолчанию /webhook)
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")

