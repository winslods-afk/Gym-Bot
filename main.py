"""
Главный файл для запуска телеграм-бота.
Инициализирует бота, регистрирует обработчики и запускает polling.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем текущую директорию в путь для импортов
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import init_db
from handlers import start, training, stats

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """
    Главная функция для запуска бота.
    """
    # Инициализируем базу данных
    logger.info("Инициализация базы данных...")
    init_db()
    logger.info("База данных инициализирована")
    
    # Создаем бота и диспетчер
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрируем роутеры (обработчики)
    # Важно: training.router должен быть зарегистрирован первым,
    # чтобы перехватывать ввод весов во время тренировки
    dp.include_router(training.router)
    dp.include_router(stats.router)
    dp.include_router(start.router)  # В конце, так как содержит общий обработчик текста
    
    logger.info("Бот запущен и готов к работе!")
    
    # Запускаем polling
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)

