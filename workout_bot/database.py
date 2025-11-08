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
    
    # Таблица программ тренировок
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            exercise TEXT NOT NULL,
            sets INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Таблица результатов тренировок
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            exercise TEXT NOT NULL,
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
    
    # Сохраняем новую программу
    for day, exercises in program_data.items():
        for exercise_data in exercises:
            cursor.execute(
                "INSERT INTO programs (user_id, day, exercise, sets) VALUES (?, ?, ?, ?)",
                (user_id, day, exercise_data['exercise'], exercise_data['sets'])
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
        Словарь с программой {день: [упражнения]}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if day:
        cursor.execute(
            "SELECT day, exercise, sets FROM programs WHERE user_id = ? AND day = ?",
            (user_id, day)
        )
    else:
        cursor.execute(
            "SELECT day, exercise, sets FROM programs WHERE user_id = ?",
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


def save_result(user_id: int, day: str, exercise: str, set_number: int, weight: float):
    """
    Сохраняет результат выполнения подхода.
    
    Args:
        user_id: ID пользователя
        day: День недели
        exercise: Название упражнения
        set_number: Номер подхода
        weight: Вес в кг
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute(
        """INSERT INTO results (user_id, day, exercise, set_number, weight, date)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, day, exercise, set_number, weight, date)
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

