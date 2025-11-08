"""
Главный файл для запуска телеграм-бота.
Инициализирует бота, регистрирует обработчики.
Поддерживает как polling (для локальной разработки), так и webhook (для продакшена).
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
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    from aiohttp import web
    from aiohttp.web import run_app
    from config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PORT, WEBHOOK_PATH
    from database import init_db
    from handlers import start, training, stats
except ImportError as e:
    logger.error(f"Ошибка импорта: {e}")
    logger.error(f"Текущая рабочая директория: {os.getcwd()}")
    logger.error(f"Содержимое текущей директории: {list(current_dir.iterdir())}")
    raise


def main():
    """
    Главная функция для запуска бота.
    Поддерживает как polling (для локальной разработки), так и webhook (для продакшена).
    """
    # Инициализируем базу данных (синхронная операция)
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
    
    # Если указан WEBHOOK_URL, используем webhook (для продакшена)
    if WEBHOOK_URL:
        logger.info("Запуск в режиме webhook...")
        
        # Создаем веб-приложение
        app = web.Application()
        
        # Настраиваем обработчик webhook
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        webhook_requests_handler.register(app, path=WEBHOOK_PATH)
        
        # Настраиваем startup и shutdown для webhook
        async def on_startup():
            webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
            await bot.set_webhook(webhook_url, drop_pending_updates=True)
            logger.info(f"Webhook установлен: {webhook_url}")
        
        async def on_shutdown():
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Webhook удален")
        
        # Регистрируем startup и shutdown handlers
        app.on_startup.append(lambda _: asyncio.create_task(on_startup()))
        app.on_shutdown.append(lambda _: asyncio.create_task(on_shutdown()))
        
        # Настраиваем приложение для работы с aiogram
        setup_application(app, dp, bot=bot)
        
        # Запускаем веб-сервер (синхронная функция)
        logger.info(f"Веб-сервер запущен на порту {WEBHOOK_PORT}")
        run_app(app, host="0.0.0.0", port=WEBHOOK_PORT)
    else:
        # Используем polling (для локальной разработки)
        logger.info("Запуск в режиме polling...")
        logger.info("⚠️  ВНИМАНИЕ: Убедитесь, что бот не запущен в другом месте!")
        logger.info("⚠️  Для продакшена установите переменную WEBHOOK_URL")
        
        async def run_polling():
            try:
                await dp.start_polling(bot, skip_updates=True)
            finally:
                await bot.session.close()
        
        asyncio.run(run_polling())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)

