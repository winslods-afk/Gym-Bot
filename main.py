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
    from handlers import start, training, stats, button_workouts
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
    dp.include_router(button_workouts.router)  # Тренировки по кнопкам
    dp.include_router(training.router)
    dp.include_router(stats.router)
    dp.include_router(start.router)  # В конце, так как содержит общий обработчик текста
    
    # Если указан WEBHOOK_URL, используем webhook (для продакшена)
    if WEBHOOK_URL:
        logger.info("Запуск в режиме webhook...")
        logger.info(f"WEBHOOK_URL: {WEBHOOK_URL}")
        logger.info(f"WEBHOOK_PATH: {WEBHOOK_PATH}")
        logger.info(f"WEBHOOK_PORT: {WEBHOOK_PORT}")
        
        # Создаем веб-приложение
        app = web.Application()
        
        # Настраиваем обработчик webhook
        # Убираем лишние слеши из пути
        webhook_path_clean = WEBHOOK_PATH.strip('/')
        if not webhook_path_clean:
            webhook_path_clean = "webhook"
        webhook_path_final = f"/{webhook_path_clean}"
        
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        webhook_requests_handler.register(app, path=webhook_path_final)
        logger.info(f"Webhook handler зарегистрирован на пути: {webhook_path_final}")
        
        # Настраиваем startup и shutdown для webhook
        async def on_startup(app):
            # Убираем лишние слеши из URL
            webhook_base = WEBHOOK_URL.rstrip('/')
            webhook_path_clean = WEBHOOK_PATH.strip('/')
            if not webhook_path_clean:
                webhook_path_clean = "webhook"
            webhook_url = f"{webhook_base}/{webhook_path_clean}"
            logger.info(f"Устанавливаем webhook: {webhook_url}")
            try:
                await bot.set_webhook(webhook_url, drop_pending_updates=True)
                logger.info(f"✅ Webhook успешно установлен: {webhook_url}")
                
                # Проверяем установленный webhook
                webhook_info = await bot.get_webhook_info()
                logger.info(f"Webhook info: URL={webhook_info.url}, pending={webhook_info.pending_update_count}, last_error={webhook_info.last_error_message}")
            except Exception as e:
                logger.error(f"❌ Ошибка при установке webhook: {e}", exc_info=True)
                raise  # Пробрасываем ошибку, чтобы сервер не запустился с неработающим webhook
        
        async def on_shutdown(app):
            logger.info("Shutdown handler вызван (webhook остается активным)...")
            # НЕ удаляем webhook при shutdown, чтобы он оставался активным при перезапуске
            # Это важно для Render.com, где сервис может перезапускаться
        
        # Cleanup context для правильного закрытия соединений
        async def cleanup_context(app):
            # При запуске ничего не делаем, соединения создаются автоматически
            yield
            # При завершении закрываем соединения
            logger.info("Закрываем соединения...")
            try:
                if bot.session:
                    await bot.session.close()
                logger.info("✅ Соединения закрыты")
            except Exception as e:
                logger.error(f"Ошибка при закрытии соединений: {e}", exc_info=True)
        
        app.cleanup_ctx.append(cleanup_context)
        
        # Регистрируем startup и shutdown handlers
        app.on_startup.append(on_startup)
        app.on_shutdown.append(on_shutdown)
        
        # Добавляем простой обработчик для корневого пути (чтобы не было 404)
        async def root_handler(request):
            return web.Response(text="Bot is running! Webhook path: " + WEBHOOK_PATH, status=200)
        
        app.router.add_get("/", root_handler)
        
        # Добавляем обработчик для проверки статуса webhook
        async def status_handler(request):
            try:
                webhook_info = await bot.get_webhook_info()
                status_text = f"Bot Status:\nWebhook URL: {webhook_info.url}\nPending updates: {webhook_info.pending_update_count}\nLast error: {webhook_info.last_error_message}"
                return web.Response(text=status_text, status=200)
            except Exception as e:
                return web.Response(text=f"Error getting webhook info: {e}", status=500)
        
        app.router.add_get("/status", status_handler)
        
        # Настраиваем приложение для работы с aiogram
        setup_application(app, dp, bot=bot)
        
        # Запускаем веб-сервер (синхронная функция, блокирующая)
        # Соединения будут закрыты автоматически через cleanup_context
        webhook_base = WEBHOOK_URL.rstrip('/')
        webhook_path = WEBHOOK_PATH.lstrip('/')
        final_webhook_url = f"{webhook_base}/{webhook_path}"
        logger.info(f"Веб-сервер запущен на порту {WEBHOOK_PORT}")
        logger.info(f"Ожидаем обновления на: {final_webhook_url}")
        logger.info(f"Webhook handler зарегистрирован на пути: /{webhook_path}")
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

