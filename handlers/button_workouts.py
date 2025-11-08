"""
Обработчик тренировок по кнопкам.
Управляет созданием и выполнением тренировок через кнопки.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import (
    save_button_workout, get_button_workouts, get_button_workout_exercises,
    save_button_workout_result, get_last_button_workout_weight
)
from utils.keyboards import (
    get_workout_count_keyboard, get_workout_buttons_keyboard,
    get_confirm_workout_keyboard, get_training_control_keyboard, get_confirm_keyboard
)
from parser import parse_exercise_with_reps
import database

router = Router()


class ButtonWorkoutState(StatesGroup):
    """Состояния FSM для создания тренировок по кнопкам."""
    waiting_for_count = State()  # Ожидание количества тренировок
    waiting_for_workout_name = State()  # Ожидание названия тренировки
    waiting_for_exercises = State()  # Ожидание упражнений
    confirming_workout = State()  # Подтверждение тренировки


# Хранилище текущих сессий создания тренировок
# Формат: {user_id: {'workout_number': номер, 'workout_name': название, 'exercises': [...]}}
workout_creation_sessions = {}

# Хранилище текущих тренировок пользователей
# Формат: {user_id: {'workout_number': номер, 'exercises': [...], 'current_ex': индекс, 'current_set': номер}}
button_training_sessions = {}


@router.callback_query(F.data == "mode_button_workouts")
async def start_button_workouts_mode(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора режима тренировок по кнопкам.
    Просит пользователя выбрать количество тренировок в неделю.
    """
    await callback.answer()
    await state.set_state(ButtonWorkoutState.waiting_for_count)
    await callback.message.answer(
        "🔘 Режим тренировок по кнопкам\n\n"
        "Сколько тренировок у тебя в неделю?",
        reply_markup=get_workout_count_keyboard()
    )


@router.callback_query(F.data.startswith("workout_count_"))
async def process_workout_count(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора количества тренировок.
    Создает кнопки для каждой тренировки.
    """
    await callback.answer()
    count = int(callback.data.split("_")[-1])
    
    user_id = callback.from_user.id
    
    # Сохраняем количество тренировок
    await state.update_data(workout_count=count)
    
    # Создаем кнопки для каждой тренировки
    buttons = []
    for i in range(1, count + 1):
        buttons.append([InlineKeyboardButton(
            text=f"Тренировка {i}",
            callback_data=f"create_workout_{i}"
        )])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.answer(
        f"✅ Создано {count} тренировок.\n\n"
        "Нажми на кнопку тренировки, чтобы начать её настройку:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("create_workout_"))
async def start_workout_creation(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик начала создания тренировки.
    Просит ввести название тренировки.
    """
    await callback.answer()
    workout_number = int(callback.data.split("_")[-1])
    
    await state.set_state(ButtonWorkoutState.waiting_for_workout_name)
    await state.update_data(workout_number=workout_number)
    
    await callback.message.answer(
        f"🏋️ Настройка тренировки {workout_number}\n\n"
        "Введи название тренировки (например: Ноги, Спина, Грудь):"
    )


@router.message(ButtonWorkoutState.waiting_for_workout_name)
async def process_workout_name(message: Message, state: FSMContext):
    """
    Обработчик ввода названия тренировки.
    Просит ввести упражнения.
    """
    workout_name = message.text.strip()
    data = await state.get_data()
    workout_number = data.get('workout_number')
    
    await state.update_data(workout_name=workout_name)
    await state.set_state(ButtonWorkoutState.waiting_for_exercises)
    
    await message.answer(
        f"✅ Название сохранено: {workout_name}\n\n"
        "Теперь отправь упражнения в формате:\n\n"
        "Гакк-присед — 20-16-14-12 (увеличивая вес)\n"
        "Жим ног по одной — 18-10-14\n"
        "Разгибания ног — 25-16-20\n\n"
        "Или:\n"
        "Гакк-присед — 4х10\n"
        "Жим ног — 3х12"
    )


@router.message(ButtonWorkoutState.waiting_for_exercises)
async def process_exercises(message: Message, state: FSMContext):
    """
    Обработчик ввода упражнений.
    Парсит упражнения и показывает их для подтверждения.
    """
    text = message.text.strip()
    data = await state.get_data()
    workout_number = data.get('workout_number')
    workout_name = data.get('workout_name')
    
    user_id = message.from_user.id
    
    # Парсим упражнения
    lines = text.split('\n')
    exercises = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Пропускаем строки с днями недели
        if any(day in line.upper() for day in ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']):
            continue
        
        exercise_data = parse_exercise_with_reps(line)
        if exercise_data:
            exercises.append(exercise_data)
    
    if not exercises:
        await message.answer(
            "❌ Не удалось распарсить упражнения.\n\n"
            "Попробуй еще раз в формате:\n"
            "Гакк-присед — 20-16-14-12\n"
            "Жим ног — 3х12"
        )
        return
    
    # Сохраняем во временное хранилище
    workout_creation_sessions[user_id] = {
        'workout_number': workout_number,
        'workout_name': workout_name,
        'exercises': exercises
    }
    
    # Форматируем для показа
    workout_text = format_button_workout_preview(workout_name, exercises)
    
    await state.set_state(ButtonWorkoutState.confirming_workout)
    await message.answer(
        workout_text,
        reply_markup=get_confirm_workout_keyboard()
    )


def format_button_workout_preview(workout_name: str, exercises: list) -> str:
    """
    Форматирует тренировку для предпросмотра.
    
    Args:
        workout_name: Название тренировки
        exercises: Список упражнений с подходами
    
    Returns:
        Отформатированная строка
    """
    text = f"Ваша тренировка - {workout_name}\n\n"
    
    for exercise in exercises:
        exercise_name = exercise['exercise']
        sets = exercise['sets']
        
        text += f"{exercise_name}\n"
        
        for set_data in sets:
            set_num = set_data['set_number']
            reps = set_data['reps']
            if reps:
                text += f"{set_num} подход {reps} раз\n"
            else:
                text += f"{set_num} подход\n"
        
        text += "\n"
    
    return text


@router.callback_query(F.data == "confirm_workout")
async def confirm_workout(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик подтверждения тренировки.
    Сохраняет тренировку в базу данных.
    """
    await callback.answer()
    user_id = callback.from_user.id
    
    if user_id not in workout_creation_sessions:
        await callback.message.answer("❌ Сессия создания тренировки не найдена")
        return
    
    session = workout_creation_sessions[user_id]
    
    # Сохраняем в базу
    save_button_workout(
        user_id,
        session['workout_number'],
        session['workout_name'],
        session['exercises']
    )
    
    await callback.message.answer(
        f"✅ Тренировка {session['workout_number']} - {session['workout_name']} сохранена!"
    )
    
    # Удаляем из временного хранилища
    del workout_creation_sessions[user_id]
    await state.clear()
    
    # Показываем меню тренировок
    workouts = get_button_workouts(user_id)
    if workouts:
        from utils.keyboards import get_workout_buttons_keyboard
        await callback.message.answer(
            "Выбери тренировку для выполнения:",
            reply_markup=get_workout_buttons_keyboard(workouts)
        )


@router.callback_query(F.data == "reject_workout")
async def reject_workout(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик отклонения тренировки.
    Просит ввести упражнения заново.
    """
    await callback.answer()
    await state.set_state(ButtonWorkoutState.waiting_for_exercises)
    await callback.message.answer(
        "Введи упражнения заново в правильном формате:\n\n"
        "Гакк-присед — 20-16-14-12\n"
        "Жим ног — 3х12"
    )


@router.callback_query(F.data.startswith("select_workout_"))
async def select_workout(callback: CallbackQuery):
    """
    Обработчик выбора тренировки для выполнения.
    Начинает тренировку.
    """
    await callback.answer()
    workout_number = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    
    # Получаем упражнения тренировки
    exercises = get_button_workout_exercises(user_id, workout_number)
    
    if not exercises:
        await callback.message.answer("❌ Тренировка не найдена")
        return
    
    # Получаем название тренировки
    workouts = get_button_workouts(user_id)
    workout_name = next((w['workout_name'] for w in workouts if w['workout_number'] == workout_number), f"Тренировка {workout_number}")
    
    # Сохраняем сессию тренировки
    button_training_sessions[user_id] = {
        'workout_number': workout_number,
        'workout_name': workout_name,
        'exercises': exercises,
        'current_ex': 0,
        'current_set': 0
    }
    
    # Форматируем список упражнений
    exercises_text = f"🏋️ {workout_name}:\n\n"
    for i, ex in enumerate(exercises, 1):
        sets_count = len(ex['sets'])
        exercises_text += f"{i}. {ex['exercise']} — {sets_count} подходов\n"
    
    await callback.message.answer(
        f"{exercises_text}\n"
        "Начинаем тренировку! После каждого подхода отправь вес в кг.",
        reply_markup=get_training_control_keyboard()
    )
    
    # Начинаем с первого упражнения и первого подхода
    await ask_for_button_workout_weight(callback.message, user_id)


async def ask_for_button_workout_weight(message: Message, user_id: int):
    """
    Запрашивает вес для текущего подхода в тренировке по кнопкам.
    """
    session = button_training_sessions.get(user_id)
    if not session:
        await message.answer("❌ Сессия тренировки не найдена. Начни заново.")
        return
    
    exercise = session['exercises'][session['current_ex']]
    exercise_name = exercise['exercise']
    sets = exercise['sets']
    
    if session['current_set'] >= len(sets):
        # Переходим к следующему упражнению
        session['current_ex'] += 1
        session['current_set'] = 0
        
        if session['current_ex'] >= len(session['exercises']):
            # Все упражнения завершены
            del button_training_sessions[user_id]
            await message.answer(
                "🎉 Тренировка завершена! Отличная работа! 💪\n\n"
                "Все результаты сохранены."
            )
            return
        else:
            exercise = session['exercises'][session['current_ex']]
            exercise_name = exercise['exercise']
            sets = exercise['sets']
    
    current_set_data = sets[session['current_set']]
    set_number = current_set_data['set_number']
    reps = current_set_data['reps']
    
    # Проверяем, есть ли предыдущий вес
    last_weight = get_last_button_workout_weight(
        user_id, session['workout_number'], exercise_name, set_number
    )
    
    reps_text = f" {reps} раз" if reps else ""
    
    if last_weight:
        await message.answer(
            f"💪 {exercise_name} — подход {set_number}{reps_text}\n\n"
            f"Последний вес: {last_weight} кг\n"
            "Отправь новый вес или подтверди предыдущий.",
            reply_markup=get_confirm_keyboard()
        )
    else:
        await message.answer(
            f"💪 {exercise_name} — подход {set_number}{reps_text}\n\n"
            "Отправь вес в кг (например: 60):"
        )


@router.message(F.text.regexp(r'^\d+([.,]\d+)?$'))
async def process_button_workout_weight(message: Message, state: FSMContext):
    """
    Обработчик ввода веса для тренировки по кнопкам.
    """
    user_id = message.from_user.id
    session = button_training_sessions.get(user_id)
    
    if not session:
        return
    
    # Парсим вес
    try:
        weight = float(message.text.replace(',', '.'))
        if weight <= 0:
            return
    except ValueError:
        return
    
    exercise = session['exercises'][session['current_ex']]
    exercise_name = exercise['exercise']
    sets = exercise['sets']
    current_set_data = sets[session['current_set']]
    set_number = current_set_data['set_number']
    
    # Сохраняем вес
    save_button_workout_result(
        user_id, session['workout_number'], exercise_name, set_number, weight
    )
    
    await message.answer(f"✅ Сохранено: {weight} кг")
    
    # Переходим к следующему подходу
    session['current_set'] += 1
    await ask_for_button_workout_weight(message, user_id)


@router.callback_query(F.data == "confirm_weight")
async def confirm_button_workout_weight(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик подтверждения веса для тренировки по кнопкам.
    """
    user_id = callback.from_user.id
    session = button_training_sessions.get(user_id)
    
    if not session:
        # Если нет сессии по кнопкам, пропускаем (обработается в training.py)
        return
    
    exercise = session['exercises'][session['current_ex']]
    exercise_name = exercise['exercise']
    sets = exercise['sets']
    current_set_data = sets[session['current_set']]
    set_number = current_set_data['set_number']
    
    # Получаем последний вес
    last_weight = get_last_button_workout_weight(
        user_id, session['workout_number'], exercise_name, set_number
    )
    
    if not last_weight:
        await callback.answer("❌ Предыдущий вес не найден", show_alert=True)
        return
    
    # Сохраняем вес
    save_button_workout_result(
        user_id, session['workout_number'], exercise_name, set_number, last_weight
    )
    
    await callback.answer(f"✅ Сохранено: {last_weight} кг")
    
    # Переходим к следующему подходу
    session['current_set'] += 1
    await ask_for_button_workout_weight(callback.message, user_id)


@router.callback_query(F.data == "end_training")
async def end_button_workout_callback(callback: CallbackQuery):
    """
    Обработчик кнопки "Закончить тренировку" для тренировок по кнопкам.
    Завершает текущую сессию тренировки.
    """
    user_id = callback.from_user.id
    
    if user_id in button_training_sessions:
        del button_training_sessions[user_id]
        await callback.answer("Тренировка завершена!", show_alert=True)
        await callback.message.answer("✅ Тренировка завершена! Отличная работа! 💪")

