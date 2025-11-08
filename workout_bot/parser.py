"""
Модуль для парсинга текстовой программы тренировок.
Разбирает текст вида "ПН: жим лёжа 3x10, присед 4x8; ВТ: подтягивания 3xмакс"
на структурированные данные.
"""
import re
from typing import Dict, List

# Маппинг дней недели (русские сокращения -> полные названия)
DAY_MAPPING = {
    'ПН': 'Понедельник',
    'ВТ': 'Вторник',
    'СР': 'Среда',
    'ЧТ': 'Четверг',
    'ПТ': 'Пятница',
    'СБ': 'Суббота',
    'ВС': 'Воскресенье',
    'ПОНЕДЕЛЬНИК': 'Понедельник',
    'ВТОРНИК': 'Вторник',
    'СРЕДА': 'Среда',
    'ЧЕТВЕРГ': 'Четверг',
    'ПЯТНИЦА': 'Пятница',
    'СУББОТА': 'Суббота',
    'ВОСКРЕСЕНЬЕ': 'Воскресенье'
}


def parse_program(text: str) -> Dict[str, List[Dict]]:
    """
    Парсит текстовую программу тренировок.
    
    Формат ввода:
    "ПН: жим лёжа 3x10, присед 4x8; ВТ: подтягивания 3xмакс, тяга 4x10"
    
    Args:
        text: Текст программы тренировок
    
    Returns:
        Словарь вида {день: [{'exercise': название, 'sets': количество подходов}]}
    
    Raises:
        ValueError: Если формат программы некорректный
    """
    program = {}
    
    # Разделяем по дням (разделитель - точка с запятой или перенос строки)
    day_blocks = re.split(r'[;\n]', text)
    
    for block in day_blocks:
        block = block.strip()
        if not block:
            continue
        
        # Ищем день недели в начале блока
        day_match = re.match(r'^([А-ЯЁ]+):', block, re.IGNORECASE)
        if not day_match:
            raise ValueError(f"Не удалось определить день недели в блоке: {block}")
        
        day_short = day_match.group(1).upper()
        day_full = DAY_MAPPING.get(day_short)
        
        if not day_full:
            raise ValueError(f"Неизвестный день недели: {day_short}")
        
        # Извлекаем упражнения из блока
        exercises_text = block[len(day_match.group(0)):].strip()
        
        # Разделяем упражнения по запятой
        exercises = [ex.strip() for ex in exercises_text.split(',') if ex.strip()]
        
        program[day_full] = []
        
        for exercise_text in exercises:
            # Парсим формат: "название упражнения количество_подходовxповторения"
            # Примеры: "жим лёжа 3x10", "присед 4x8", "подтягивания 3xмакс"
            match = re.match(r'^(.+?)\s+(\d+)x(\d+|макс|МАКС|max|MAX)$', exercise_text)
            
            if not match:
                # Пробуем альтернативный формат: "название количество_подходов"
                match = re.match(r'^(.+?)\s+(\d+)$', exercise_text)
                if match:
                    exercise_name = match.group(1).strip()
                    sets = int(match.group(2))
                else:
                    raise ValueError(f"Не удалось распарсить упражнение: {exercise_text}")
            else:
                exercise_name = match.group(1).strip()
                sets = int(match.group(2))
            
            program[day_full].append({
                'exercise': exercise_name,
                'sets': sets
            })
    
    if not program:
        raise ValueError("Не удалось распарсить программу. Проверьте формат.")
    
    return program


def get_current_day() -> str:
    """
    Определяет текущий день недели на русском языке.
    
    Returns:
        Название дня недели (например, "Понедельник")
    """
    from datetime import datetime
    
    days = [
        'Понедельник', 'Вторник', 'Среда', 'Четверг',
        'Пятница', 'Суббота', 'Воскресенье'
    ]
    
    today = datetime.now().weekday()  # 0 = понедельник, 6 = воскресенье
    return days[today]

