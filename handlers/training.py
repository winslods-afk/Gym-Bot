"""
Обработчик тренировок.
Управляет процессом тренировки с использованием FSM (Finite State Machine).
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import get_program, save_result, get_last_weight, get_program_by_id
from utils.keyboards import get_training_control_keyboard, get_confirm_keyboard
from utils.helpers import format_training_exercises
import database

router = Router()


class TrainingState(StatesGroup):
    """Состояния FSM для процесса тренировки."""
    waiting_for_weight = State()  # Ожидание ввода веса
    confirming_weight = State()   # Подтверждение веса


# Хранилище текущих тренировок пользователей
# Формат: {user_id: {'day': день, 'exercises': [...], 'current_ex': индекс, 'current_set': номер}}
training_sessions = {}


async def start_training_session(message: Message, day: str = None):
    """
    Начинает сессию тренировки для пользователя.
    
    Args:
        message: Сообщение от пользователя
        day: День недели (если None, определяется автоматически)
    """
    from parser import get_current_day
    
    user_id = message.from_user.id
    
    if day is None:
        day = get_current_day()
    
    # Получаем программу на этот день
    program = get_program(user_id, day)
    
    if not program or day not in program:
        await message.answer(
            f"❌ У тебя нет программы на {day}.\n"
            "Сначала отправь программу тренировок."
        )
        return
    
    exercises = program[day]
    
    # Сохраняем сессию тренировки
    training_sessions[user_id] = {
        'day': day,
        'exercises': exercises,
        'current_ex': 0,
        'current_set': 1
    }
    
    # Отправляем список упражнений
    exercises_text = format_training_exercises(day, exercises)
    await message.answer(
        f"{exercises_text}\n"
        "Начинаем тренировку! После каждого подхода отправь вес в кг (например: 60).",
        reply_markup=get_training_control_keyboard()
    )
    
    # Начинаем с первого упражнения и первого подхода
    await ask_for_weight(message, user_id)


async def ask_for_weight(message: Message, user_id: int):
    """
    Запрашивает вес для текущего подхода.
    Если есть предыдущий вес, предлагает его по умолчанию.
    
    Args:
        message: Сообщение для ответа
        user_id: ID пользователя
    """
    session = training_sessions.get(user_id)
    if not session:
        await message.answer("❌ Сессия тренировки не найдена. Начни заново.")
        return
    
    exercise = session['exercises'][session['current_ex']]
    exercise_name = exercise['exercise']
    set_number = session['current_set']
    
    # Проверяем, есть ли предыдущий вес
    last_weight = get_last_weight(user_id, exercise_name, set_number)
    
    if last_weight:
        # Предлагаем предыдущий вес
        await message.answer(
            f"💪 {exercise_name} — подход {set_number}/{exercise['sets']}\n\n"
            f"Последний вес: {last_weight} кг\n"
            "Отправь новый вес или подтверди предыдущий.",
            reply_markup=get_confirm_keyboard()
        )
    else:
        # Просто запрашиваем вес
        await message.answer(
            f"💪 {exercise_name} — подход {set_number}/{exercise['sets']}\n\n"
            "Отправь вес в кг (например: 60):"
        )


@router.callback_query(F.data == "save_program")
async def save_program_callback(callback: CallbackQuery):
    """
    Обработчик кнопки "Сохранить программу".
    Сохраняет распарсенную программу в базу данных.
    """
    user_id = callback.from_user.id
    
    # Получаем временно сохраненную программу
    if not hasattr(database, 'temp_programs') or user_id not in database.temp_programs:
        await callback.answer("❌ Программа не найдена. Отправь программу заново.", show_alert=True)
        return
    
    program = database.temp_programs[user_id]
    
    # Сохраняем в базу
    from database import save_program
    save_program(user_id, program)
    
    # Удаляем из временного хранилища
    del database.temp_programs[user_id]
    
    await callback.answer("✅ Программа сохранена!", show_alert=True)
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ Программа сохранена!",
        reply_markup=None
    )


@router.callback_query(F.data == "end_training")
async def end_training_callback(callback: CallbackQuery):
    """
    Обработчик кнопки "Закончить тренировку".
    Завершает текущую сессию тренировки.
    """
    user_id = callback.from_user.id
    
    # Проверяем, есть ли активная тренировка по кнопкам
    from handlers.button_workouts import button_training_sessions
    if user_id in button_training_sessions:
        # Обрабатывается в button_workouts.py
        return
    
    if user_id in training_sessions:
        del training_sessions[user_id]
    
    await callback.answer("Тренировка завершена!", show_alert=True)
    await callback.message.answer("✅ Тренировка завершена! Отличная работа! 💪")


@router.callback_query(F.data == "confirm_weight")
async def confirm_weight_callback(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Подтвердить" для веса.
    Использует последний сохраненный вес.
    """
    user_id = callback.from_user.id
    
    # Проверяем, есть ли активная тренировка по кнопкам
    from handlers.button_workouts import button_training_sessions
    if user_id in button_training_sessions:
        # Обрабатывается в button_workouts.py
        return
    
    session = training_sessions.get(user_id)
    
    if not session:
        await callback.answer("❌ Сессия не найдена", show_alert=True)
        return
    
    exercise = session['exercises'][session['current_ex']]
    exercise_id = exercise.get('exercise_id')
    exercise_name = exercise['exercise']
    set_number = session['current_set']
    
    if not exercise_id:
        await callback.answer("❌ Ошибка: ID упражнения не найден", show_alert=True)
        return
    
    # Получаем последний вес
    last_weight = get_last_weight(user_id, exercise_name, set_number)
    
    if not last_weight:
        await callback.answer("❌ Предыдущий вес не найден", show_alert=True)
        return
    
    # Сохраняем вес
    save_result(user_id, exercise_id, session['day'], exercise_name, set_number, last_weight)
    
    await callback.answer(f"✅ Сохранено: {last_weight} кг")
    
    # Переходим к следующему подходу
    await move_to_next_set(callback.message, user_id)


@router.callback_query(F.data == "change_weight")
async def change_weight_callback(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик кнопки "Изменить" для веса.
    Переводит в состояние ожидания нового веса.
    """
    await state.set_state(TrainingState.waiting_for_weight)
    await callback.answer("Введи новый вес в кг")
    await callback.message.answer("Введи новый вес в кг (например: 65):")


@router.message(TrainingState.waiting_for_weight)
async def process_weight_input(message: Message, state: FSMContext):
    """
    Обработчик ввода веса пользователем.
    """
    user_id = message.from_user.id
    session = training_sessions.get(user_id)
    
    if not session:
        await message.answer("❌ Сессия тренировки не найдена. Начни заново.")
        await state.clear()
        return
    
    # Парсим вес из сообщения
    try:
        weight = float(message.text.replace(',', '.'))
        if weight <= 0:
            raise ValueError("Вес должен быть положительным числом")
    except ValueError:
        await message.answer("❌ Неверный формат. Отправь число (например: 60 или 60.5)")
        return
    
    exercise = session['exercises'][session['current_ex']]
    exercise_id = exercise.get('exercise_id')
    exercise_name = exercise['exercise']
    set_number = session['current_set']
    
    if not exercise_id:
        await message.answer("❌ Ошибка: ID упражнения не найден")
        return
    
    # Сохраняем вес
    save_result(user_id, exercise_id, session['day'], exercise_name, set_number, weight)
    
    await message.answer(f"✅ Сохранено: {weight} кг")
    
    # Переходим к следующему подходу
    await move_to_next_set(message, user_id)
    await state.clear()


@router.message(F.text.regexp(r'^\d+([.,]\d+)?$') & ~F.text.startswith('/'))
async def process_weight_direct(message: Message, state: FSMContext):
    """
    Обработчик прямого ввода веса (без состояния FSM).
    Обрабатывает сообщения, которые выглядят как числа.
    Работает только если есть активная сессия тренировки.
    """
    user_id = message.from_user.id
    
    # Проверяем, есть ли активная тренировка по кнопкам
    from handlers.button_workouts import button_training_sessions
    if user_id in button_training_sessions:
        # Вес обработается в button_workouts.py
        return
    
    session = training_sessions.get(user_id)
    
    # Если нет активной сессии, игнорируем
    if not session:
        return
    
    # Пропускаем, если пользователь в состоянии ожидания веса (чтобы не дублировать)
    current_state = await state.get_state()
    if current_state == TrainingState.waiting_for_weight:
        return
    
    # Парсим вес
    try:
        weight = float(message.text.replace(',', '.'))
        if weight <= 0:
            return
    except ValueError:
        return
    
    exercise = session['exercises'][session['current_ex']]
    exercise_id = exercise.get('exercise_id')
    exercise_name = exercise['exercise']
    set_number = session['current_set']
    
    if not exercise_id:
        await message.answer("❌ Ошибка: ID упражнения не найден")
        return
    
    # Сохраняем вес
    save_result(user_id, exercise_id, session['day'], exercise_name, set_number, weight)
    
    await message.answer(f"✅ Сохранено: {weight} кг")
    
    # Переходим к следующему подходу
    await move_to_next_set(message, user_id)


async def move_to_next_set(message: Message, user_id: int):
    """
    Переходит к следующему подходу или упражнению.
    Если все подходы и упражнения завершены, завершает тренировку.
    
    Args:
        message: Сообщение для ответа
        user_id: ID пользователя
    """
    session = training_sessions.get(user_id)
    if not session:
        return
    
    exercise = session['exercises'][session['current_ex']]
    total_sets = exercise['sets']
    current_set = session['current_set']
    
    # Переходим к следующему подходу
    if current_set < total_sets:
        session['current_set'] += 1
        await ask_for_weight(message, user_id)
    else:
        # Переходим к следующему упражнению
        session['current_ex'] += 1
        session['current_set'] = 1
        
        if session['current_ex'] < len(session['exercises']):
            # Есть еще упражнения
            await message.answer("✅ Упражнение завершено! Переходим к следующему.")
            await ask_for_weight(message, user_id)
        else:
            # Все упражнения завершены
            del training_sessions[user_id]
            await message.answer(
                "🎉 Тренировка завершена! Отличная работа! 💪\n\n"
                "Все результаты сохранены. Используй /stats для просмотра статистики."
            )


async def start_training_session_with_program(message: Message, program_id: int):
    """
    Начинает сессию тренировки для загруженной программы.
    
    Args:
        message: Сообщение от пользователя
        program_id: ID программы
    """
    from parser import get_current_day
    
    user_id = message.from_user.id
    
    # Определяем текущий день
    day = get_current_day()
    
    # Получаем программу по ID для конкретного дня
    program = get_program_by_id(user_id, program_id, day=day)
    
    if not program:
        # Если программа не найдена для этого дня, получаем все дни для показа списка
        all_program = get_program_by_id(user_id, program_id)
        if not all_program:
            await message.answer("❌ Программа не найдена.")
            return
        
        # Показываем список доступных дней
        days_list = "\n".join([f"• {d}" for d in all_program.keys()])
        await message.answer(
            f"❌ У тебя нет программы на {day}.\n\n"
            f"Доступные дни:\n{days_list}\n\n"
            "Выбери день из списка или дождись нужного дня недели."
        )
        return
    
    # Получаем упражнения для текущего дня
    exercises = program.get(day, [])
    
    if not exercises:
        # Если упражнения не найдены, показываем список доступных дней
        all_program = get_program_by_id(user_id, program_id)
        if all_program:
            days_list = "\n".join([f"• {d}" for d in all_program.keys()])
            await message.answer(
                f"❌ У тебя нет программы на {day}.\n\n"
                f"Доступные дни:\n{days_list}\n\n"
                "Выбери день из списка или дождись нужного дня недели."
            )
            return
        await message.answer("❌ Программа не найдена.")
        return
    
    # Сохраняем сессию тренировки
    training_sessions[user_id] = {
        'day': day,
        'exercises': exercises,
        'current_ex': 0,
        'current_set': 1,
        'program_id': program_id
    }
    
    # Отправляем список упражнений
    exercises_text = format_training_exercises(day, exercises)
    await message.answer(
        f"{exercises_text}\n"
        "Начинаем тренировку! После каждого подхода отправь вес в кг (например: 60).",
        reply_markup=get_training_control_keyboard()
    )
    
    # Начинаем с первого упражнения и первого подхода
    await ask_for_weight(message, user_id)

