"""
Обработчик команды /stats для просмотра статистики тренировок.
"""
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database import get_stats

router = Router()


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """
    Обработчик команды /stats.
    Показывает последние результаты пользователя по каждому упражнению.
    """
    user_id = message.from_user.id
    
    # Получаем статистику
    stats = get_stats(user_id)
    
    if not stats:
        await message.answer(
            "📊 У тебя пока нет сохраненных результатов.\n"
            "Начни тренировку, чтобы отслеживать свои веса!"
        )
        return
    
    # Форматируем статистику
    stats_text = "📊 Твоя статистика:\n\n"
    for exercise, max_weight in sorted(stats.items()):
        stats_text += f"💪 {exercise} — {max_weight} кг\n"
    
    await message.answer(stats_text)

