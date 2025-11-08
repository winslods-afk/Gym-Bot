"""
Модуль с клавиатурами для бота.
Содержит Reply и Inline клавиатуры для взаимодействия с пользователем.
"""
from typing import List, Dict
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard(has_programs: bool = False) -> ReplyKeyboardMarkup:
    """
    Создает основную клавиатуру с главными кнопками.
    
    Args:
        has_programs: Есть ли у пользователя программы
    
    Returns:
        ReplyKeyboardMarkup с кнопками "Начать тренировку", "Статистика" и "Перезагрузить бота"
    """
    return get_restart_keyboard(has_programs)


def get_save_program_keyboard() -> InlineKeyboardMarkup:
    """
    Создает inline клавиатуру для сохранения программы.
    
    Returns:
        InlineKeyboardMarkup с кнопкой "Сохранить программу"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Сохранить программу", callback_data="save_program")]
        ]
    )
    return keyboard


def get_training_control_keyboard() -> InlineKeyboardMarkup:
    """
    Создает inline клавиатуру для управления тренировкой.
    
    Returns:
        InlineKeyboardMarkup с кнопками "Закончить тренировку"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Закончить тренировку", callback_data="end_training")]
        ]
    )
    return keyboard


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """
    Создает inline клавиатуру для подтверждения веса.
    
    Returns:
        InlineKeyboardMarkup с кнопками "Подтвердить" и "Изменить"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_weight"),
                InlineKeyboardButton(text="✏️ Изменить", callback_data="change_weight")
            ]
        ]
    )
    return keyboard


def get_mode_selection_keyboard() -> InlineKeyboardMarkup:
    """
    Создает inline клавиатуру для выбора режима загрузки программы.
    
    Returns:
        InlineKeyboardMarkup с кнопками "Загрузить программу" и "Добавить программу вручную"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Загрузить программу", callback_data="mode_upload_program")],
            [InlineKeyboardButton(text="Добавить программу вручную", callback_data="mode_manual_program")]
        ]
    )
    return keyboard


def get_workout_count_keyboard_with_cancel() -> InlineKeyboardMarkup:
    """
    Создает inline клавиатуру для выбора количества тренировок с кнопкой отмены.
    
    Returns:
        InlineKeyboardMarkup с кнопками от 1 до 7 тренировок и кнопкой отмены
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="workout_count_1"),
                InlineKeyboardButton(text="2", callback_data="workout_count_2"),
                InlineKeyboardButton(text="3", callback_data="workout_count_3"),
                InlineKeyboardButton(text="4", callback_data="workout_count_4")
            ],
            [
                InlineKeyboardButton(text="5", callback_data="workout_count_5"),
                InlineKeyboardButton(text="6", callback_data="workout_count_6"),
                InlineKeyboardButton(text="7", callback_data="workout_count_7")
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_manual_program")]
        ]
    )
    return keyboard


def get_program_selection_keyboard(programs: List[Dict], user_id: int = None) -> InlineKeyboardMarkup:
    """
    Создает inline клавиатуру для выбора программы тренировок.
    
    Args:
        programs: Список программ [{'id': 1, 'program_name': '...', 'program_type': '...', 'workout_count': ...}, ...]
        user_id: ID пользователя (опционально, для подсчета дней в uploaded программах)
    
    Returns:
        InlineKeyboardMarkup с кнопками программ
    """
    buttons = []
    for program in programs:
        if program['program_type'] == 'manual':
            text = f"{program['program_name']} - {program['workout_count']} дней"
        else:
            # Для uploaded программ считаем количество дней
            if user_id:
                from database import get_program_by_id
                program_data = get_program_by_id(user_id, program['id'])
                days_count = len(program_data) if program_data else 0
                text = f"{program['program_name']} - {days_count} дней"
            else:
                text = program['program_name']
        
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"select_program_{program['id']}"
        )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_delete_program_keyboard(programs: List[Dict], user_id: int = None) -> InlineKeyboardMarkup:
    """
    Создает inline клавиатуру для выбора программы для удаления.
    
    Args:
        programs: Список программ
        user_id: ID пользователя (опционально, для подсчета дней в uploaded программах)
    
    Returns:
        InlineKeyboardMarkup с кнопками программ для удаления
    """
    buttons = []
    for program in programs:
        if program['program_type'] == 'manual':
            text = f"🗑️ {program['program_name']} - {program['workout_count']} дней"
        else:
            if user_id:
                from database import get_program_by_id
                program_data = get_program_by_id(user_id, program['id'])
                days_count = len(program_data) if program_data else 0
                text = f"🗑️ {program['program_name']} - {days_count} дней"
            else:
                text = f"🗑️ {program['program_name']}"
        
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"delete_program_{program['id']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_restart_keyboard(has_programs: bool = False) -> ReplyKeyboardMarkup:
    """
    Создает клавиатуру для перезапуска бота с опциональной кнопкой удаления программ.
    
    Args:
        has_programs: Есть ли у пользователя программы
    
    Returns:
        ReplyKeyboardMarkup
    """
    keyboard_buttons = [
        [KeyboardButton(text="Начать тренировку")],
        [KeyboardButton(text="Статистика")]
    ]
    
    if has_programs:
        keyboard_buttons.append([KeyboardButton(text="Удалить программу")])
    
    keyboard_buttons.append([KeyboardButton(text="🔄 Перезагрузить бота")])
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True
    )
    return keyboard


def get_workout_count_keyboard() -> InlineKeyboardMarkup:
    """
    Создает inline клавиатуру для выбора количества тренировок в неделю.
    
    Returns:
        InlineKeyboardMarkup с кнопками от 1 до 7 тренировок
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="workout_count_1"),
                InlineKeyboardButton(text="2", callback_data="workout_count_2"),
                InlineKeyboardButton(text="3", callback_data="workout_count_3"),
                InlineKeyboardButton(text="4", callback_data="workout_count_4")
            ],
            [
                InlineKeyboardButton(text="5", callback_data="workout_count_5"),
                InlineKeyboardButton(text="6", callback_data="workout_count_6"),
                InlineKeyboardButton(text="7", callback_data="workout_count_7")
            ]
        ]
    )
    return keyboard


def get_workout_buttons_keyboard(workouts: list) -> InlineKeyboardMarkup:
    """
    Создает inline клавиатуру с кнопками тренировок.
    
    Args:
        workouts: Список тренировок [{'workout_number': 1, 'workout_name': 'Ноги'}, ...]
    
    Returns:
        InlineKeyboardMarkup с кнопками тренировок
    """
    buttons = []
    for workout in workouts:
        text = f"Тренировка {workout['workout_number']} - {workout['workout_name']}"
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"select_workout_{workout['workout_number']}"
        )])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def get_confirm_workout_keyboard() -> InlineKeyboardMarkup:
    """
    Создает inline клавиатуру для подтверждения тренировки.
    
    Returns:
        InlineKeyboardMarkup с кнопками "✅ Верно" и "❌ Неверно"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Верно", callback_data="confirm_workout"),
                InlineKeyboardButton(text="❌ Неверно", callback_data="reject_workout")
            ]
        ]
    )
    return keyboard

