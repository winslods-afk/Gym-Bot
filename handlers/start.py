"""
Обработчик команды /start и начальных сообщений.
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database import add_user, get_program
from utils.keyboards import get_main_keyboard, get_save_program_keyboard
from parser import parse_program, get_current_day
import database

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Обработчик команды /start.
    Приветствует пользователя и предлагает выбрать режим работы.
    """
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Добавляем пользователя в базу
    add_user(user_id, username)
    
    from utils.keyboards import get_mode_selection_keyboard
    
    await message.answer(
        "👋 Привет! Я бот для отслеживания тренировок и рабочих весов.\n\n"
        "Выбери режим работы:",
        reply_markup=get_mode_selection_keyboard()
    )


@router.message(F.text == "Начать тренировку")
async def start_training_button(message: Message):
    """
    Обработчик кнопки "Начать тренировку".
    Предлагает выбрать между программой по дням и тренировками по кнопкам.
    """
    user_id = message.from_user.id
    
    # Проверяем, есть ли тренировки по кнопкам
    from database import get_button_workouts
    button_workouts_list = get_button_workouts(user_id)
    
    # Проверяем, есть ли программа по дням
    current_day = get_current_day()
    program = get_program(user_id, current_day)
    
    if button_workouts_list:
        # Есть тренировки по кнопкам - предлагаем выбрать
        from utils.keyboards import get_workout_buttons_keyboard
        await message.answer(
            "Выбери тренировку:",
            reply_markup=get_workout_buttons_keyboard(button_workouts_list)
        )
    elif program and current_day in program:
        # Есть программа на сегодня - начинаем тренировку
        from handlers.training import start_training_session
        await start_training_session(message, current_day)
    else:
        # Нет ни программы, ни тренировок
        await message.answer(
            f"❌ У тебя нет программы на сегодня ({current_day}) и нет тренировок по кнопкам.\n\n"
            "📝 Создай программу через /start"
        )


@router.message(F.text == "Статистика")
async def stats_button(message: Message):
    """
    Обработчик кнопки "Статистика".
    Перенаправляет в модуль статистики.
    """
    from handlers.stats import cmd_stats
    await cmd_stats(message)


@router.callback_query(F.data == "mode_full_program")
async def handle_full_program_mode(callback: CallbackQuery):
    """
    Обработчик выбора режима программы целиком.
    Объясняет формат и ждет ввода программы.
    """
    await callback.answer()
    await callback.message.answer(
        "📝 Режим программы целиком\n\n"
        "Отправь мне свою программу тренировок в любом формате:\n\n"
        "1️⃣ Классический:\n"
        "ПН: жим лёжа 3x10, присед 4x8; ВТ: подтягивания 3xмакс\n\n"
        "2️⃣ С тире (многострочный):\n"
        "🔹 ПТ Ноги\n"
        "Гакк-присед — 4х10\n"
        "Жим ног — 3х12\n\n"
        "3️⃣ С диапазонами:\n"
        "ПТ Ноги\n"
        "Гакк-присед — 20-16-14-12\n"
        "Жим ног — 18-10-14",
        reply_markup=get_main_keyboard()
    )


@router.message(F.text & ~F.text.in_(["Начать тренировку", "Статистика"]))
async def handle_program_text(message: Message):
    """
    Обработчик текстовых сообщений с программой тренировок.
    Парсит программу и предлагает сохранить её.
    Игнорирует команды и кнопки.
    """
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Пропускаем, если это команда
    if text.startswith('/'):
        return
    
    # Пытаемся распарсить программу
    try:
        program = parse_program(text)
        
        # Форматируем программу для отображения
        from utils.helpers import format_program_text
        program_text = format_program_text(program)
        
        # Сохраняем программу во временное хранилище
        if not hasattr(database, 'temp_programs'):
            database.temp_programs = {}
        database.temp_programs[user_id] = program
        
        await message.answer(
            f"✅ Программа распознана:\n{program_text}\n\n"
            "Нажми кнопку ниже, чтобы сохранить программу.",
            reply_markup=get_save_program_keyboard()
        )
        
    except ValueError as e:
        await message.answer(
            f"❌ Ошибка при разборе программы: {str(e)}\n\n"
            "📝 Поддерживаемые форматы:\n\n"
            "1️⃣ Классический:\n"
            "ПН: жим лёжа 3x10, присед 4x8; ВТ: подтягивания 3xмакс\n\n"
            "2️⃣ С тире (многострочный):\n"
            "🔹 ПТ Ноги\n"
            "Гакк-присед — 4х10\n"
            "Жим ног — 3х12\n\n"
            "3️⃣ С диапазонами повторений:\n"
            "ПТ Ноги\n"
            "Гакк-присед — 20-16-14-12\n"
            "Жим ног — 18-10-14"
        )

