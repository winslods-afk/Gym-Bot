"""
Главный файл для запуска телеграм-бота.
Инициализирует бота, регистрирует обработчики и запускает polling.
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

# Добавляем текущую директорию и родительскую в путь для импортов
# Это необходимо для работы на Render.com и других платформах
current_dir = Path(__file__).parent.absolute()
parent_dir = current_dir.parent.absolute()
working_dir = Path(os.getcwd()).absolute()

# Добавляем пути в sys.path (если их там еще нет)
# Порядок важен: сначала текущая директория файла, затем рабочая, затем родительская
for path in [str(current_dir), str(working_dir), str(parent_dir)]:
    if path and path not in sys.path:
        sys.path.insert(0, path)

# Настройка логирования (до импортов, чтобы видеть возможные ошибки)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Логируем пути для отладки
logger.info(f"Текущая директория файла: {current_dir}")
logger.info(f"Рабочая директория: {working_dir}")
logger.info(f"Родительская директория: {parent_dir}")
logger.info(f"Python path (первые 5): {sys.path[:5]}")

try:
    from aiogram import Bot, Dispatcher
    from aiogram.fsm.storage.memory import MemoryStorage
    from config import BOT_TOKEN
    from database import init_db
    from handlers import start, training, stats
except ImportError as e:
    logger.error(f"Ошибка импорта: {e}")
    logger.error(f"Текущая рабочая директория: {os.getcwd()}")
    logger.error(f"Содержимое текущей директории: {list(current_dir.iterdir())}")
    raise


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

