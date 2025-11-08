"""
Вспомогательные функции для бота.
"""
from typing import Dict, List


def format_program_text(program: Dict[str, List[Dict]]) -> str:
    """
    Форматирует программу тренировок в читаемый текст.
    
    Args:
        program: Словарь с программой {день: [упражнения]}
    
    Returns:
        Отформатированная строка с программой
    """
    if not program:
        return "Программа не найдена."
    
    lines = []
    for day, exercises in program.items():
        lines.append(f"\n📅 {day}:")
        for ex in exercises:
            lines.append(f"  • {ex['exercise']} — {ex['sets']} подходов")
    
    return "\n".join(lines)


def format_training_exercises(day: str, exercises: List[Dict]) -> str:
    """
    Форматирует список упражнений для текущей тренировки.
    
    Args:
        day: День недели
        exercises: Список упражнений
    
    Returns:
        Отформатированная строка
    """
    text = f"🏋️ Тренировка на {day}:\n\n"
    for i, ex in enumerate(exercises, 1):
        text += f"{i}. {ex['exercise']} — {ex['sets']} подходов\n"
    
    return text

