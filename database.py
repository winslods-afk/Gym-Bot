"""
Модуль для работы с базой данных SQLite.
Содержит функции для создания таблиц и работы с данными пользователей, программ и результатов.
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Путь к файлу базы данных
DB_PATH = "workout_bot.db"


def get_connection():
    """Создает и возвращает соединение с базой данных."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
    return conn


def init_db():
    """
    Инициализирует базу данных, создавая необходимые таблицы.
    Вызывается при первом запуске бота.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            current_day TEXT
        )
    """)
    
    # Таблица программ тренировок (метаданные)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            program_name TEXT NOT NULL,
            program_type TEXT NOT NULL,
            workout_count INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Таблица программ тренировок (упражнения)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_id INTEGER,
            user_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            exercise TEXT NOT NULL,
            sets INTEGER NOT NULL,
            order_index INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (program_id) REFERENCES workout_programs(id) ON DELETE CASCADE
        )
    """)
    
    # Миграция: добавляем program_id, если его еще нет
    try:
        cursor.execute("ALTER TABLE programs ADD COLUMN program_id INTEGER")
    except sqlite3.OperationalError:
        pass
    
    # Миграция: добавляем order_index, если его еще нет
    try:
        cursor.execute("ALTER TABLE programs ADD COLUMN order_index INTEGER DEFAULT 0")
        cursor.execute("UPDATE programs SET order_index = id WHERE order_index IS NULL")
    except sqlite3.OperationalError:
        pass
    
    # Таблица сессий тренировок (Workout ID)
    # Создается когда пользователь начинает тренировку
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            program_id INTEGER,
            day TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (program_id) REFERENCES workout_programs(id) ON DELETE SET NULL
        )
    """)
    
    # Таблица упражнений в тренировке (Exercise ID)
    # Привязано к workout_session в определенном порядке
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER NOT NULL,
            exercise_template_id INTEGER,
            exercise_name TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            FOREIGN KEY (workout_id) REFERENCES workout_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (exercise_template_id) REFERENCES programs(id) ON DELETE SET NULL
        )
    """)
    
    # Таблица подходов в упражнении (Set ID)
    # Привязано к workout_exercise в определенном порядке
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercise_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_id INTEGER NOT NULL,
            set_number INTEGER NOT NULL,
            order_index INTEGER NOT NULL,
            FOREIGN KEY (exercise_id) REFERENCES workout_exercises(id) ON DELETE CASCADE
        )
    """)
    
    # Таблица весов в подходе (Weight ID)
    # Привязано к exercise_set
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS set_weights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_id INTEGER NOT NULL,
            weight REAL NOT NULL,
            recorded_at TEXT NOT NULL,
            FOREIGN KEY (set_id) REFERENCES exercise_sets(id) ON DELETE CASCADE
        )
    """)
    
    # Старая таблица results (для обратной совместимости, будет удалена позже)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exercise_id INTEGER,
            day TEXT NOT NULL,
            exercise TEXT NOT NULL,
            set_number INTEGER NOT NULL,
            weight REAL,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (exercise_id) REFERENCES programs(id) ON DELETE CASCADE
        )
    """)
    
    # Таблица тренировок по кнопкам
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS button_workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            workout_number INTEGER NOT NULL,
            workout_name TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, workout_number)
        )
    """)
    
    # Таблица упражнений для тренировок по кнопкам
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS button_workout_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            workout_number INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            set_number INTEGER NOT NULL,
            reps INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Таблица результатов для тренировок по кнопкам
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS button_workout_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            workout_number INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            set_number INTEGER NOT NULL,
            weight REAL,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
    conn.close()


def add_user(user_id: int, username: str = None):
    """
    Добавляет пользователя в базу данных, если его еще нет.
    
    Args:
        user_id: ID пользователя в Telegram
        username: Имя пользователя (опционально)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Проверяем, существует ли пользователь
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (id, username) VALUES (?, ?)",
            (user_id, username)
        )
        conn.commit()
    
    conn.close()


def save_program(user_id: int, program_data: Dict[str, List[Dict]]):
    """
    Сохраняет программу тренировок пользователя.
    Сначала удаляет старую программу, затем сохраняет новую.
    
    Args:
        user_id: ID пользователя
        program_data: Словарь с данными программы {день: [упражнения]}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Удаляем старую программу пользователя
    cursor.execute("DELETE FROM programs WHERE user_id = ?", (user_id,))
    
    # Сохраняем новую программу с сохранением порядка
    for day, exercises in program_data.items():
        for order_index, exercise_data in enumerate(exercises):
            cursor.execute(
                "INSERT INTO programs (user_id, day, exercise, sets, order_index) VALUES (?, ?, ?, ?, ?)",
                (user_id, day, exercise_data['exercise'], exercise_data['sets'], order_index)
            )
    
    conn.commit()
    conn.close()


def get_program(user_id: int, day: str = None) -> Dict[str, List[Dict]]:
    """
    Получает программу тренировок пользователя.
    
    Args:
        user_id: ID пользователя
        day: День недели (опционально, если None - возвращает всю программу)
    
    Returns:
        Словарь с программой {день: [упражнения]} в правильном порядке
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if day:
        cursor.execute(
            "SELECT day, exercise, sets, order_index FROM programs WHERE user_id = ? AND day = ? ORDER BY order_index",
            (user_id, day)
        )
    else:
        cursor.execute(
            "SELECT day, exercise, sets, order_index FROM programs WHERE user_id = ? ORDER BY day, order_index",
            (user_id,)
        )
    
    rows = cursor.fetchall()
    conn.close()
    
    program = {}
    for row in rows:
        day_name = row['day']
        if day_name not in program:
            program[day_name] = []
        program[day_name].append({
            'exercise': row['exercise'],
            'sets': row['sets']
        })
    
    return program


def save_result(user_id: int, exercise_id: int, day: str, exercise: str, set_number: int, weight: float):
    """
    Сохраняет результат выполнения подхода.
    
    Args:
        user_id: ID пользователя
        exercise_id: ID упражнения из таблицы programs
        day: День недели
        exercise: Название упражнения (для обратной совместимости)
        set_number: Номер подхода
        weight: Вес в кг
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute(
        """INSERT INTO results (user_id, exercise_id, day, exercise, set_number, weight, date)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (user_id, exercise_id, day, exercise, set_number, weight, date)
    )
    
    conn.commit()
    conn.close()


def get_last_weight(user_id: int, exercise: str, set_number: int) -> Optional[float]:
    """
    Получает последний сохраненный вес для упражнения и подхода.
    
    Args:
        user_id: ID пользователя
        exercise: Название упражнения
        set_number: Номер подхода
    
    Returns:
        Последний вес или None, если записей нет
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT weight FROM results 
           WHERE user_id = ? AND exercise = ? AND set_number = ?
           ORDER BY date DESC LIMIT 1""",
        (user_id, exercise, set_number)
    )
    
    row = cursor.fetchone()
    conn.close()
    
    return row['weight'] if row else None


def get_stats(user_id: int) -> Dict[str, float]:
    """
    Получает статистику по последним весам для каждого упражнения.
    
    Args:
        user_id: ID пользователя
    
    Returns:
        Словарь {упражнение: максимальный вес}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Получаем последний вес для каждого упражнения (максимальный из последних подходов)
    cursor.execute("""
        SELECT exercise, MAX(weight) as max_weight
        FROM results
        WHERE user_id = ?
        GROUP BY exercise
    """, (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    stats = {}
    for row in rows:
        stats[row['exercise']] = row['max_weight']
    
    return stats


def save_button_workout(user_id: int, workout_number: int, workout_name: str, exercises: List[Dict]):
    """
    Сохраняет тренировку по кнопкам.
    
    Args:
        user_id: ID пользователя
        workout_number: Номер тренировки (1, 2, 3, ...)
        workout_name: Название тренировки
        exercises: Список упражнений [{'exercise': название, 'sets': [{set_number: 1, reps: 20}, ...]}]
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Сохраняем или обновляем тренировку
    cursor.execute("""
        INSERT OR REPLACE INTO button_workouts (user_id, workout_number, workout_name)
        VALUES (?, ?, ?)
    """, (user_id, workout_number, workout_name))
    
    # Удаляем старые упражнения для этой тренировки
    cursor.execute("""
        DELETE FROM button_workout_exercises 
        WHERE user_id = ? AND workout_number = ?
    """, (user_id, workout_number))
    
    # Сохраняем упражнения
    for exercise in exercises:
        exercise_name = exercise['exercise']
        for set_data in exercise['sets']:
            cursor.execute("""
                INSERT INTO button_workout_exercises 
                (user_id, workout_number, exercise_name, set_number, reps)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, workout_number, exercise_name, set_data['set_number'], set_data['reps']))
    
    conn.commit()
    conn.close()


def get_button_workouts(user_id: int) -> List[Dict]:
    """
    Получает список всех тренировок по кнопкам пользователя.
    
    Args:
        user_id: ID пользователя
    
    Returns:
        Список тренировок [{'workout_number': 1, 'workout_name': 'Ноги'}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT workout_number, workout_name 
        FROM button_workouts 
        WHERE user_id = ? 
        ORDER BY workout_number
    """, (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [{'workout_number': row['workout_number'], 'workout_name': row['workout_name']} 
            for row in rows]


def get_button_workout_exercises(user_id: int, workout_number: int) -> List[Dict]:
    """
    Получает упражнения для тренировки по кнопкам.
    
    Args:
        user_id: ID пользователя
        workout_number: Номер тренировки
    
    Returns:
        Список упражнений с подходами
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT exercise_name, set_number, reps
        FROM button_workout_exercises
        WHERE user_id = ? AND workout_number = ?
        ORDER BY exercise_name, set_number
    """, (user_id, workout_number))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Группируем по упражнениям
    exercises = {}
    for row in rows:
        ex_name = row['exercise_name']
        if ex_name not in exercises:
            exercises[ex_name] = []
        exercises[ex_name].append({
            'set_number': row['set_number'],
            'reps': row['reps']
        })
    
    result = []
    for ex_name, sets in exercises.items():
        result.append({
            'exercise': ex_name,
            'sets': sets
        })
    
    return result


def save_button_workout_result(user_id: int, workout_number: int, exercise_name: str, 
                                set_number: int, weight: float):
    """
    Сохраняет результат выполнения подхода для тренировки по кнопкам.
    
    Args:
        user_id: ID пользователя
        workout_number: Номер тренировки
        exercise_name: Название упражнения
        set_number: Номер подхода
        weight: Вес в кг
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO button_workout_results 
        (user_id, workout_number, exercise_name, set_number, weight, date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, workout_number, exercise_name, set_number, weight, date))
    
    conn.commit()
    conn.close()


def get_last_button_workout_weight(user_id: int, workout_number: int, exercise_name: str, 
                                   set_number: int) -> Optional[float]:
    """
    Получает последний сохраненный вес для упражнения и подхода в тренировке по кнопкам.
    
    Args:
        user_id: ID пользователя
        workout_number: Номер тренировки
        exercise_name: Название упражнения
        set_number: Номер подхода
    
    Returns:
        Последний вес или None
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT weight FROM button_workout_results 
        WHERE user_id = ? AND workout_number = ? AND exercise_name = ? AND set_number = ?
        ORDER BY date DESC LIMIT 1
    """, (user_id, workout_number, exercise_name, set_number))
    
    row = cursor.fetchone()
    conn.close()
    
    return row['weight'] if row else None


# ========== Функции для работы с программами тренировок ==========

def create_workout_program(user_id: int, program_name: str, program_type: str, workout_count: int = None) -> int:
    """
    Создает новую программу тренировок.
    
    Args:
        user_id: ID пользователя
        program_name: Название программы
        program_type: Тип программы ('uploaded' или 'manual')
        workout_count: Количество тренировок (для manual программ)
    
    Returns:
        ID созданной программы
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO workout_programs (user_id, program_name, program_type, workout_count, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, program_name, program_type, workout_count, created_at))
    
    program_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return program_id


def save_program_with_id(user_id: int, program_id: int, program_data: Dict[str, List[Dict]]):
    """
    Сохраняет программу тренировок с указанным ID.
    
    Args:
        user_id: ID пользователя
        program_id: ID программы
        program_data: Словарь с данными программы {день: [упражнения]}
    """
    from collections import OrderedDict
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Удаляем старые упражнения для этой программы
    cursor.execute("DELETE FROM programs WHERE program_id = ? AND user_id = ?", (program_id, user_id))
    
    # Преобразуем в OrderedDict для гарантии сохранения порядка
    if not isinstance(program_data, OrderedDict):
        ordered_program = OrderedDict(program_data)
    else:
        ordered_program = program_data
    
    # Сохраняем новую программу с сохранением порядка
    for day, exercises in ordered_program.items():
        # Убеждаемся, что exercises - это список, сохраняющий порядок
        if not isinstance(exercises, list):
            exercises = list(exercises)
        
        for order_index, exercise_data in enumerate(exercises):
            cursor.execute(
                "INSERT INTO programs (program_id, user_id, day, exercise, sets, order_index) VALUES (?, ?, ?, ?, ?, ?)",
                (program_id, user_id, day, exercise_data['exercise'], exercise_data['sets'], order_index)
            )
    
    conn.commit()
    conn.close()


def get_user_programs(user_id: int) -> List[Dict]:
    """
    Получает список всех программ пользователя.
    
    Args:
        user_id: ID пользователя
    
    Returns:
        Список программ [{'id': 1, 'program_name': '...', 'program_type': '...', 'workout_count': ...}, ...]
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, program_name, program_type, workout_count
        FROM workout_programs
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            'id': row['id'],
            'program_name': row['program_name'],
            'program_type': row['program_type'],
            'workout_count': row['workout_count']
        }
        for row in rows
    ]


def get_program_by_id(user_id: int, program_id: int, day: str = None) -> Dict[str, List[Dict]]:
    """
    Получает программу тренировок по ID.
    
    Args:
        user_id: ID пользователя
        program_id: ID программы
        day: День недели (опционально)
    
    Returns:
        Словарь с программой {день: [упражнения]} в правильном порядке
        Каждое упражнение содержит: exercise_id, exercise, sets
    """
    from collections import OrderedDict
    
    conn = get_connection()
    cursor = conn.cursor()
    
    if day:
        cursor.execute("""
            SELECT id, day, exercise, sets, order_index 
            FROM programs 
            WHERE user_id = ? AND program_id = ? AND day = ? 
            ORDER BY order_index
        """, (user_id, program_id, day))
    else:
        cursor.execute("""
            SELECT id, day, exercise, sets, order_index 
            FROM programs 
            WHERE user_id = ? AND program_id = ? 
            ORDER BY day, order_index
        """, (user_id, program_id))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Используем OrderedDict для гарантии сохранения порядка
    program = OrderedDict()
    for row in rows:
        day_name = row['day']
        if day_name not in program:
            program[day_name] = []
        program[day_name].append({
            'exercise_id': row['id'],  # ID упражнения из таблицы programs
            'exercise': row['exercise'],
            'sets': row['sets']
        })
    
    return program


def delete_workout_program(user_id: int, program_id: int):
    """
    Удаляет программу тренировок (каскадное удаление через FOREIGN KEY).
    
    Args:
        user_id: ID пользователя
        program_id: ID программы
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Удаляем программу (упражнения удалятся автоматически через CASCADE)
    cursor.execute("""
        DELETE FROM workout_programs 
        WHERE id = ? AND user_id = ?
    """, (program_id, user_id))
    
    conn.commit()
    conn.close()


# ========== Функции для работы с новой структурой тренировок ==========

def create_workout_session(user_id: int, program_id: int = None, day: str = None) -> int:
    """
    Создает новую сессию тренировки (Workout ID).
    
    Args:
        user_id: ID пользователя
        program_id: ID программы (опционально)
        day: День недели (опционально)
    
    Returns:
        ID созданной сессии тренировки (Workout ID)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO workout_sessions (user_id, program_id, day, started_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, program_id, day, started_at))
    
    workout_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return workout_id


def add_workout_exercise(workout_id: int, exercise_template_id: int = None, exercise_name: str = None, order_index: int = None) -> int:
    """
    Добавляет упражнение в тренировку (Exercise ID).
    
    Args:
        workout_id: ID сессии тренировки
        exercise_template_id: ID упражнения из шаблона (опционально)
        exercise_name: Название упражнения
        order_index: Порядковый номер упражнения в тренировке
    
    Returns:
        ID созданного упражнения (Exercise ID)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Если order_index не указан, определяем автоматически
    if order_index is None:
        cursor.execute("""
            SELECT COALESCE(MAX(order_index), -1) + 1 
            FROM workout_exercises 
            WHERE workout_id = ?
        """, (workout_id,))
        order_index = cursor.fetchone()[0]
    
    cursor.execute("""
        INSERT INTO workout_exercises (workout_id, exercise_template_id, exercise_name, order_index)
        VALUES (?, ?, ?, ?)
    """, (workout_id, exercise_template_id, exercise_name, order_index))
    
    exercise_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return exercise_id


def add_exercise_set(exercise_id: int, set_number: int, order_index: int = None) -> int:
    """
    Добавляет подход к упражнению (Set ID).
    
    Args:
        exercise_id: ID упражнения
        set_number: Номер подхода (1, 2, 3, ...)
        order_index: Порядковый номер подхода (опционально)
    
    Returns:
        ID созданного подхода (Set ID)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Если order_index не указан, определяем автоматически
    if order_index is None:
        cursor.execute("""
            SELECT COALESCE(MAX(order_index), -1) + 1 
            FROM exercise_sets 
            WHERE exercise_id = ?
        """, (exercise_id,))
        order_index = cursor.fetchone()[0]
    
    cursor.execute("""
        INSERT INTO exercise_sets (exercise_id, set_number, order_index)
        VALUES (?, ?, ?)
    """, (exercise_id, set_number, order_index))
    
    set_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return set_id


def save_set_weight(set_id: int, weight: float) -> int:
    """
    Сохраняет вес для подхода (Weight ID).
    
    Args:
        set_id: ID подхода
        weight: Вес в кг
    
    Returns:
        ID созданной записи веса (Weight ID)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    recorded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO set_weights (set_id, weight, recorded_at)
        VALUES (?, ?, ?)
    """, (set_id, weight, recorded_at))
    
    weight_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return weight_id


def get_workout_exercises(workout_id: int) -> List[Dict]:
    """
    Получает все упражнения тренировки в правильном порядке.
    
    Args:
        workout_id: ID сессии тренировки
    
    Returns:
        Список упражнений с их подходами в правильном порядке
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, exercise_template_id, exercise_name, order_index
        FROM workout_exercises
        WHERE workout_id = ?
        ORDER BY order_index
    """, (workout_id,))
    
    exercises = []
    for row in cursor.fetchall():
        exercise_id = row['id']
        
        # Получаем подходы для этого упражнения
        cursor.execute("""
            SELECT id, set_number, order_index
            FROM exercise_sets
            WHERE exercise_id = ?
            ORDER BY order_index
        """, (exercise_id,))
        
        sets = []
        for set_row in cursor.fetchall():
            set_id = set_row['id']
            
            # Получаем вес для этого подхода (последний)
            cursor.execute("""
                SELECT weight, recorded_at
                FROM set_weights
                WHERE set_id = ?
                ORDER BY recorded_at DESC
                LIMIT 1
            """, (set_id,))
            
            weight_row = cursor.fetchone()
            weight = weight_row['weight'] if weight_row else None
            
            sets.append({
                'set_id': set_id,
                'set_number': set_row['set_number'],
                'weight': weight
            })
        
        exercises.append({
            'exercise_id': exercise_id,
            'exercise_template_id': row['exercise_template_id'],
            'exercise_name': row['exercise_name'],
            'sets': sets
        })
    
    conn.close()
    return exercises


def get_current_set_id(workout_id: int, exercise_order: int, set_number: int) -> Optional[int]:
    """
    Получает ID текущего подхода.
    
    Args:
        workout_id: ID сессии тренировки
        exercise_order: Порядковый номер упражнения (0-based)
        set_number: Номер подхода
    
    Returns:
        ID подхода или None
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Получаем exercise_id по порядковому номеру
    cursor.execute("""
        SELECT id FROM workout_exercises
        WHERE workout_id = ?
        ORDER BY order_index
        LIMIT 1 OFFSET ?
    """, (workout_id, exercise_order))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    exercise_id = row['id']
    
    # Получаем set_id по номеру подхода
    cursor.execute("""
        SELECT id FROM exercise_sets
        WHERE exercise_id = ? AND set_number = ?
        ORDER BY order_index
        LIMIT 1
    """, (exercise_id, set_number))
    
    row = cursor.fetchone()
    conn.close()
    
    return row['id'] if row else None


def save_manual_program_workout(user_id: int, program_id: int, workout_number: int, exercises: List[Dict]):
    """
    Сохраняет тренировку ручной программы в таблицу programs.
    
    Args:
        user_id: ID пользователя
        program_id: ID программы
        workout_number: Номер тренировки (1, 2, 3, ...)
        exercises: Список упражнений [{'exercise': название, 'sets': [{set_number: 1, reps: 20}, ...]}]
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Используем "Тренировка N" как день недели
    day = f"Тренировка {workout_number}"
    
    # Удаляем старые упражнения для этой тренировки
    cursor.execute("""
        DELETE FROM programs 
        WHERE program_id = ? AND user_id = ? AND day = ?
    """, (program_id, user_id, day))
    
    # Сохраняем упражнения
    for order_index, exercise in enumerate(exercises):
        exercise_name = exercise['exercise']
        sets_count = len(exercise['sets'])
        
        cursor.execute("""
            INSERT INTO programs (program_id, user_id, day, exercise, sets, order_index)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (program_id, user_id, day, exercise_name, sets_count, order_index))
    
    conn.commit()
    conn.close()
