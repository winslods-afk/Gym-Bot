"""
Модуль для парсинга текстовой программы тренировок.
Поддерживает различные форматы ввода:
- ПН: жим лёжа 3x10, присед 4x8
- 🔹 ПТ Ноги\nГакк-присед — 4х10\nЖим ног — 3х12
- Гакк-присед — 20-16-14-12 (увеличивая вес)
"""
import re
from typing import Dict, List, Optional

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


def extract_day_from_text(text: str) -> Optional[str]:
    """
    Извлекает день недели из текста.
    Поддерживает форматы:
    - "ПН:" или "ПН "
    - "🔹 ПТ Ноги"
    - "ПТ Ноги"
    
    Returns:
        Полное название дня недели или None
    """
    # Убираем эмодзи и специальные символы
    text_clean = re.sub(r'[🔹🔸▪️▫️•]', '', text).strip()
    
    # Ищем день недели в начале строки
    # Формат: "ПН:", "ПН ", "ПТ Ноги"
    patterns = [
        r'^([А-ЯЁ]{2,})\s*[:—\-]',  # "ПН:" или "ПН —"
        r'^([А-ЯЁ]{2,})\s+',         # "ПТ Ноги"
        r'^([А-ЯЁ]{2,})$',           # Просто "ПТ"
    ]
    
    for pattern in patterns:
        match = re.match(pattern, text_clean, re.IGNORECASE)
        if match:
            day_short = match.group(1).upper()
            day_full = DAY_MAPPING.get(day_short)
            if day_full:
                return day_full
    
    return None


def parse_sets_from_exercise(exercise_text: str) -> int:
    """
    Извлекает количество подходов из описания упражнения.
    Поддерживает форматы:
    - "4х10" или "4x10" -> 4 подхода
    - "3х12" -> 3 подхода
    - "20-16-14-12" -> 4 подхода (по количеству чисел)
    - "18-10-14" -> 3 подхода
    - "25-16-20" -> 3 подхода
    - "16-20-25-30" -> 4 подхода
    
    Args:
        exercise_text: Текст с описанием подходов
    
    Returns:
        Количество подходов
    """
    # Убираем комментарии в скобках
    exercise_text = re.sub(r'\([^)]*\)', '', exercise_text).strip()
    
    # Формат "4х10" или "4x10" (подходы x повторения)
    match = re.search(r'(\d+)\s*[хx]\s*\d+', exercise_text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    # Формат "20-16-14-12" (диапазоны повторений)
    # Считаем количество чисел, разделенных дефисами
    ranges = re.findall(r'\d+', exercise_text)
    if ranges and len(ranges) >= 2:
        # Если есть несколько чисел через дефис, это количество подходов
        dash_separated = re.findall(r'\d+-\d+', exercise_text)
        if dash_separated:
            # Считаем все числа в диапазонах
            all_numbers = re.findall(r'\d+', exercise_text)
            return len(all_numbers)
    
    # Если ничего не найдено, возвращаем 1 подход по умолчанию
    return 1


def parse_exercise_line(line: str) -> Optional[Dict]:
    """
    Парсит строку с упражнением.
    Поддерживает форматы:
    - "Гакк-присед — 4х10"
    - "Жим ног — 3х12"
    - "Разгибания ног — 25-16-20"
    - "Икры стоя — 16-20-25-30"
    
    Args:
        line: Строка с упражнением
    
    Returns:
        Словарь {'exercise': название, 'sets': количество} или None
    """
    line = line.strip()
    if not line:
        return None
    
    # Убираем эмодзи и специальные символы в начале
    line = re.sub(r'^[🔹🔸▪️▫️•\-\s]+', '', line).strip()
    
    # Разделяем название упражнения и описание подходов
    # Ищем разделители: "—", "-", "–" или просто пробел перед числами
    separators = ['—', '–', '-']
    exercise_name = line
    sets_description = ""
    
    for sep in separators:
        if sep in line:
            parts = line.split(sep, 1)
            if len(parts) == 2:
                exercise_name = parts[0].strip()
                sets_description = parts[1].strip()
                break
    
    # Если разделитель не найден, ищем паттерн с числами
    if not sets_description:
        # Ищем паттерн: название упражнения, затем числа
        match = re.match(r'^(.+?)\s+(\d+[хx]\d+|\d+-\d+.*|\d+)', line)
        if match:
            exercise_name = match.group(1).strip()
            sets_description = match.group(2).strip()
    
    # Если все еще нет описания, пробуем найти числа в конце строки
    if not sets_description:
        match = re.search(r'(\d+[хx]\d+|\d+-\d+.*|\d+)\s*$', line)
        if match:
            # Находим начало чисел
            num_start = match.start()
            exercise_name = line[:num_start].strip()
            sets_description = match.group(1).strip()
    
    # Если название пустое, возвращаем None
    if not exercise_name:
        return None
    
    # Извлекаем количество подходов
    sets = parse_sets_from_exercise(sets_description if sets_description else line)
    
    return {
        'exercise': exercise_name,
        'sets': sets
    }


def parse_program(text: str) -> Dict[str, List[Dict]]:
    """
    Парсит текстовую программу тренировок.
    Поддерживает различные форматы ввода.
    
    Форматы ввода:
    1. "ПН: жим лёжа 3x10, присед 4x8; ВТ: подтягивания 3xмакс"
    2. "🔹 ПТ Ноги\nГакк-присед — 4х10\nЖим ног — 3х12"
    3. "ПТ Ноги\nГакк-присед — 20-16-14-12\nЖим ног — 18-10-14"
    
    Args:
        text: Текст программы тренировок
    
    Returns:
        Словарь вида {день: [{'exercise': название, 'sets': количество подходов}]}
    
    Raises:
        ValueError: Если формат программы некорректный
    """
    program = {}
    
    # Разделяем текст на строки
    lines = text.split('\n')
    
    current_day = None
    current_exercises = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Пытаемся определить день недели
        day = extract_day_from_text(line)
        if day:
            # Сохраняем предыдущий день, если есть
            if current_day and current_exercises:
                program[current_day] = current_exercises
            
            # Начинаем новый день
            current_day = day
            current_exercises = []
            continue
        
        # Если день еще не определен, пытаемся найти его в начале текста
        if not current_day:
            # Пробуем найти день в текущей строке
            day = extract_day_from_text(line)
            if day:
                current_day = day
                current_exercises = []
                continue
            
            # Если это первая строка и день не найден, пробуем старый формат
            # "ПН: упражнение1, упражнение2"
            day_match = re.match(r'^([А-ЯЁ]+)\s*[:—\-]', line, re.IGNORECASE)
            if day_match:
                day_short = day_match.group(1).upper()
                day_full = DAY_MAPPING.get(day_short)
                if day_full:
                    current_day = day_full
                    # Извлекаем упражнения из этой строки
                    exercises_text = line[len(day_match.group(0)):].strip()
                    # Разделяем по запятой
                    exercise_parts = [ex.strip() for ex in exercises_text.split(',') if ex.strip()]
                    for ex_part in exercise_parts:
                        exercise = parse_exercise_line(ex_part)
                        if exercise:
                            current_exercises.append(exercise)
                    continue
        
        # Парсим строку как упражнение
        exercise = parse_exercise_line(line)
        if exercise:
            if not current_day:
                # Если день не определен, используем текущий день недели
                current_day = get_current_day()
            current_exercises.append(exercise)
    
    # Сохраняем последний день
    if current_day and current_exercises:
        program[current_day] = current_exercises
    
    # Если программа пустая, пробуем старый формат (разделение по ;)
    if not program:
        day_blocks = re.split(r'[;]', text)
        
        for block in day_blocks:
            block = block.strip()
            if not block:
                continue
            
            # Ищем день недели в начале блока
            day_match = re.match(r'^([А-ЯЁ]+)\s*[:—\-]', block, re.IGNORECASE)
            if not day_match:
                continue
            
            day_short = day_match.group(1).upper()
            day_full = DAY_MAPPING.get(day_short)
            
            if not day_full:
                continue
            
            # Извлекаем упражнения из блока
            exercises_text = block[len(day_match.group(0)):].strip()
            
            # Разделяем упражнения по запятой
            exercises = [ex.strip() for ex in exercises_text.split(',') if ex.strip()]
            
            program[day_full] = []
            
            for exercise_text in exercises:
                exercise = parse_exercise_line(exercise_text)
                if exercise:
                    program[day_full].append(exercise)
    
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
