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

