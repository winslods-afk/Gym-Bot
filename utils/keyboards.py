"""
Модуль с клавиатурами для бота.
Содержит Reply и Inline клавиатуры для взаимодействия с пользователем.
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает основную клавиатуру с главными кнопками.
    
    Returns:
        ReplyKeyboardMarkup с кнопками "Начать тренировку" и "Статистика"
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Начать тренировку")],
            [KeyboardButton(text="Статистика")]
        ],
        resize_keyboard=True
    )
    return keyboard


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
        InlineKeyboardMarkup с кнопками "Программа целиком" и "Тренировки по кнопкам"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Программа целиком", callback_data="mode_full_program")],
            [InlineKeyboardButton(text="🔘 Тренировки по кнопкам", callback_data="mode_button_workouts")]
        ]
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

