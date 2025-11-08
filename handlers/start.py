"""
Обработчик команды /start и начальных сообщений.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    add_user, get_user_programs, create_workout_program, 
    save_program_with_id, delete_workout_program, get_program_by_id
)
from utils.keyboards import (
    get_mode_selection_keyboard, get_save_program_keyboard,
    get_workout_count_keyboard_with_cancel, get_program_selection_keyboard,
    get_delete_program_keyboard, get_restart_keyboard, get_main_keyboard
)
from parser import parse_program
import database

router = Router()


class ProgramState(StatesGroup):
    """Состояния FSM для создания программ."""
    waiting_for_program_name_upload = State()  # Ожидание имени для загруженной программы
    waiting_for_program_text = State()  # Ожидание текста программы
    waiting_for_program_name_manual = State()  # Ожидание имени для ручной программы
    waiting_for_workout_count = State()  # Ожидание количества тренировок


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
    
    programs = get_user_programs(user_id)
    has_programs = len(programs) > 0
    
    await message.answer(
        "Привет! Я бот для отслеживания тренировок и рабочих весов.\n\n"
        "Выбери режим работы:",
        reply_markup=get_mode_selection_keyboard()
    )


@router.callback_query(F.data == "mode_upload_program")
async def handle_upload_program_mode(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора режима загрузки программы.
    Просит ввести имя программы.
    """
    await callback.answer()
    await state.set_state(ProgramState.waiting_for_program_name_upload)
    await callback.message.answer(
        "📝 Загрузить программу\n\n"
        "Введи название программы (например: Программа на массу, Сушка):"
    )


@router.message(ProgramState.waiting_for_program_name_upload)
async def process_program_name_upload(message: Message, state: FSMContext):
    """
    Обработчик ввода имени программы для загрузки.
    Просит ввести текст программы.
    """
    program_name = message.text.strip()
    
    if not program_name:
        await message.answer("❌ Название не может быть пустым. Введи название программы:")
        return
    
    await state.update_data(program_name=program_name)
    await state.set_state(ProgramState.waiting_for_program_text)
    
    await message.answer(
        f"✅ Название сохранено: {program_name}\n\n"
        "Теперь отправь программу тренировок в любом формате:\n\n"
        "1️⃣ Классический:\n"
        "ПН: жим лёжа 3x10, присед 4x8; ВТ: подтягивания 3xмакс\n\n"
        "2️⃣ С тире (многострочный):\n"
        "📅 Понедельник:\n"
        "Гакк-присед — 4х10\n"
        "Жим ног — 3х12\n\n"
        "3️⃣ С диапазонами:\n"
        "📅 Понедельник:\n"
        "Гакк-присед — 20-16-14-12\n"
        "Жим ног — 18-10-14"
    )


@router.message(ProgramState.waiting_for_program_text)
async def handle_program_text(message: Message, state: FSMContext):
    """
    Обработчик текстовых сообщений с программой тренировок.
    Парсит программу и предлагает сохранить её.
    """
    user_id = message.from_user.id
    text = message.text.strip()
    
    # Пытаемся распарсить программу
    try:
        program = parse_program(text)
        
        # Форматируем программу для отображения
        from utils.helpers import format_program_text
        program_text = format_program_text(program)
        
        # Сохраняем во временное хранилище
        data = await state.get_data()
        program_name = data.get('program_name')
        
        if not hasattr(database, 'temp_programs'):
            database.temp_programs = {}
        database.temp_programs[user_id] = {
            'program': program,
            'program_name': program_name,
            'program_type': 'uploaded'
        }
        
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
            "📅 Понедельник:\n"
            "Гакк-присед — 4х10\n"
            "Жим ног — 3х12\n\n"
            "3️⃣ С диапазонами повторений:\n"
            "📅 Понедельник:\n"
            "Гакк-присед — 20-16-14-12\n"
            "Жим ног — 18-10-14"
        )


@router.callback_query(F.data == "mode_manual_program")
async def handle_manual_program_mode(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора режима добавления программы вручную.
    Просит ввести имя программы.
    """
    await callback.answer()
    await state.set_state(ProgramState.waiting_for_program_name_manual)
    await callback.message.answer(
        "🔘 Добавить программу вручную\n\n"
        "Введи название программы (например: Программа на массу, Сушка):"
    )


@router.message(ProgramState.waiting_for_program_name_manual)
async def process_program_name_manual(message: Message, state: FSMContext):
    """
    Обработчик ввода имени программы для ручного режима.
    Просит выбрать количество тренировок.
    """
    program_name = message.text.strip()
    
    if not program_name:
        await message.answer("❌ Название не может быть пустым. Введи название программы:")
        return
    
    await state.update_data(program_name=program_name)
    await state.set_state(ProgramState.waiting_for_workout_count)
    
    await message.answer(
        f"✅ Название сохранено: {program_name}\n\n"
        "Сколько тренировок в неделю?",
        reply_markup=get_workout_count_keyboard_with_cancel()
    )


@router.callback_query(F.data == "cancel_manual_program")
async def cancel_manual_program(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик отмены создания ручной программы.
    """
    await callback.answer()
    await state.clear()
    await callback.message.answer(
        "❌ Создание программы отменено.\n\n"
        "Выбери режим работы:",
        reply_markup=get_mode_selection_keyboard()
    )


@router.callback_query(F.data.startswith("workout_count_"))
async def process_workout_count(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора количества тренировок для ручной программы.
    Создает программу и переходит к созданию тренировок.
    """
    await callback.answer()
    count = int(callback.data.split("_")[-1])
    
    user_id = callback.from_user.id
    data = await state.get_data()
    program_name = data.get('program_name')
    
    # Создаем программу в базе
    program_id = create_workout_program(
        user_id, program_name, 'manual', workout_count=count
    )
    
    await state.clear()
    
    # Переходим к созданию тренировок через button_workouts
    from handlers.button_workouts import start_manual_program_creation
    await start_manual_program_creation(callback.message, program_id, count)


@router.callback_query(F.data == "save_program")
async def save_program_callback(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Сохранить программу".
    Сохраняет распарсенную программу в базу данных.
    """
    user_id = callback.from_user.id
    
    # Получаем временно сохраненную программу
    if not hasattr(database, 'temp_programs') or user_id not in database.temp_programs:
        await callback.answer("❌ Программа не найдена. Отправь программу заново.", show_alert=True)
        return
    
    temp_data = database.temp_programs[user_id]
    program = temp_data['program']
    program_name = temp_data['program_name']
    
    # Создаем программу в базе
    program_id = create_workout_program(
        user_id, program_name, 'uploaded'
    )
    
    # Сохраняем программу
    save_program_with_id(user_id, program_id, program)
    
    # Удаляем из временного хранилища
    del database.temp_programs[user_id]
    await state.clear()
    
    await callback.answer("✅ Программа сохранена!", show_alert=True)
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ Программа сохранена!",
        reply_markup=None
    )
    
    # Показываем главное меню
    programs = get_user_programs(user_id)
    has_programs = len(programs) > 0
    await callback.message.answer(
        "Выбери режим работы:",
        reply_markup=get_mode_selection_keyboard()
    )


@router.message(F.text == "Начать тренировку")
async def start_training_button(message: Message):
    """
    Обработчик кнопки "Начать тренировку".
    Показывает список программ для выбора.
    """
    user_id = message.from_user.id
    
    # Получаем все программы пользователя
    programs = get_user_programs(user_id)
    
    if not programs:
        await message.answer(
            "❌ У тебя нет программ тренировок.\n\n"
            "Создай программу через /start"
        )
        return
    
    await message.answer(
        "Выбери программу для тренировки:",
        reply_markup=get_program_selection_keyboard(programs, user_id)
    )


@router.callback_query(F.data.startswith("select_program_"))
async def select_program(callback: CallbackQuery):
    """
    Обработчик выбора программы для тренировки.
    """
    await callback.answer()
    program_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    
    # Получаем программу
    program = get_program_by_id(user_id, program_id)
    
    if not program:
        await callback.message.answer("❌ Программа не найдена")
        return
    
    # Определяем тип программы
    programs = get_user_programs(user_id)
    program_info = next((p for p in programs if p['id'] == program_id), None)
    
    if not program_info:
        await callback.message.answer("❌ Программа не найдена")
        return
    
    if program_info['program_type'] == 'manual':
        # Для ручных программ используем button_workouts
        from handlers.button_workouts import start_manual_program_training
        await start_manual_program_training(callback.message, program_id)
    else:
        # Для загруженных программ используем training
        from handlers.training import start_training_session_with_program
        await start_training_session_with_program(callback.message, program_id)


@router.message(F.text == "Статистика")
async def stats_button(message: Message):
    """
    Обработчик кнопки "Статистика".
    Перенаправляет в модуль статистики.
    """
    from handlers.stats import cmd_stats
    await cmd_stats(message)


@router.message(F.text == "🔄 Перезагрузить бота")
async def restart_bot(message: Message, state: FSMContext):
    """
    Обработчик кнопки "Перезагрузить бота".
    Очищает все состояния и возвращает в начало.
    """
    user_id = message.from_user.id
    
    # Очищаем состояние FSM
    await state.clear()
    
    # Очищаем временные хранилища из других модулей
    import handlers.button_workouts as button_workouts_module
    if user_id in button_workouts_module.workout_creation_sessions:
        del button_workouts_module.workout_creation_sessions[user_id]
    if user_id in button_workouts_module.button_training_sessions:
        del button_workouts_module.button_training_sessions[user_id]
    
    # Очищаем временные программы
    if hasattr(database, 'temp_programs') and user_id in database.temp_programs:
        del database.temp_programs[user_id]
    
    # Очищаем сессии тренировок из training.py
    try:
        import handlers.training as training_module
        if hasattr(training_module, 'training_sessions') and user_id in training_module.training_sessions:
            del training_module.training_sessions[user_id]
    except:
        pass
    
    # Проверяем наличие программ
    programs = get_user_programs(user_id)
    has_programs = len(programs) > 0
    
    await message.answer(
        "🔄 Бот перезагружен!\n\n"
        "Привет! Я бот для отслеживания тренировок и рабочих весов.\n\n"
        "Выбери режим работы:",
        reply_markup=get_restart_keyboard(has_programs)
    )


@router.message(F.text == "Удалить программу")
async def delete_program_button(message: Message):
    """
    Обработчик кнопки "Удалить программу".
    Показывает список программ для удаления.
    """
    user_id = message.from_user.id
    
    programs = get_user_programs(user_id)
    
    if not programs:
        await message.answer("❌ У тебя нет программ для удаления.")
        return
    
    await message.answer(
        "Выбери программу для удаления:",
        reply_markup=get_delete_program_keyboard(programs, user_id)
    )


@router.callback_query(F.data.startswith("delete_program_"))
async def delete_program_callback(callback: CallbackQuery):
    """
    Обработчик удаления программы.
    """
    await callback.answer()
    program_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    
    # Удаляем программу
    delete_workout_program(user_id, program_id)
    
    await callback.message.answer("✅ Программа удалена!")
    
    # Обновляем список программ
    programs = get_user_programs(user_id)
    has_programs = len(programs) > 0
    
    await callback.message.answer(
        "Выбери режим работы:",
        reply_markup=get_mode_selection_keyboard()
    )


@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    """
    Обработчик отмены удаления программы.
    """
    await callback.answer()
    await callback.message.answer("❌ Удаление отменено.")
