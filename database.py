import sqlite3
from datetime import datetime
from typing import List, Tuple
import hashlib
import os

DB_FILE = "weather.db"


# ===========================
# Password Hash
# ===========================
def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ===========================
# Initialize DB
# ===========================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # ----- Favorites -----
    c.execute("""
    CREATE TABLE IF NOT EXISTS favorites (
        city TEXT PRIMARY KEY,
        last_temp INTEGER,
        condition TEXT,
        date_added TEXT
    )
    """)

    # ----- Users -----
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )
    """)

    # Default admin account
    c.execute("SELECT * FROM users WHERE role='admin'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", hash_pw("admin123"), "admin")
        )

    # ----- Recents -----
    c.execute("""
    CREATE TABLE IF NOT EXISTS recents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT,
        last_temp INTEGER,
        time_searched TEXT
    )
    """)

    # ----- Search Logs (correct table name) -----
    c.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        timestamp TEXT,
        city TEXT,
        temp INTEGER,
        timestamp TEXT
    )
    """)

    conn.commit()
    conn.close()

    # Settings table must exist too
    create_settings_table()


# ===========================
# Favorites
# ===========================
def add_favorite(city: str, last_temp: int, condition: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("""
    INSERT OR REPLACE INTO favorites (city, last_temp, condition, date_added)
    VALUES (?, ?, ?, ?)
    """, (city, last_temp, condition, now))
    conn.commit()
    conn.close()


def remove_favorite(city: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM favorites WHERE city = ?", (city,))
    conn.commit()
    conn.close()


def get_favorites() -> List[Tuple[str, int, str, str]]:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT city, last_temp, condition, date_added FROM favorites ORDER BY date_added DESC")
    rows = c.fetchall()
    conn.close()
    return rows


# ===========================
# Recents
# ===========================
def add_recent(city: str, last_temp: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute("INSERT INTO recents (city, last_temp, time_searched) VALUES (?, ?, ?)",
              (city, last_temp, now))
    conn.commit()

    # Keep only last 20 entries
    c.execute("SELECT id FROM recents ORDER BY id DESC LIMIT -1 OFFSET 20")
    excess = c.fetchall()
    if excess:
        ids = [(row[0],) for row in excess]
        c.executemany("DELETE FROM recents WHERE id = ?", ids)
        conn.commit()

    conn.close()


def get_recents(limit: int = 20) -> List[Tuple[int, str, int, str]]:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, city, last_temp, time_searched FROM recents ORDER BY id DESC LIMIT ?",
              (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def clear_recents():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM recents")
    conn.commit()
    conn.close()


# ===========================
# Settings
# ===========================
def create_settings_table():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY,
        unit TEXT,
        dynamic_bg INTEGER
    )
    """)

    # Create if none exists
    if c.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
        c.execute("INSERT INTO settings (unit, dynamic_bg) VALUES (?, ?)", ("C", 1))

    conn.commit()
    conn.close()


def get_settings():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT unit, dynamic_bg FROM settings WHERE id = 1")
    row = c.fetchone()
    conn.close()
    if row:
        return {"unit": row[0], "dynamic_bg": bool(row[1])}
    return {"unit": "C", "dynamic_bg": True}


def save_settings(unit, dynamic_bg):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE settings SET unit=?, dynamic_bg=? WHERE id=1",
              (unit, 1 if dynamic_bg else 0))
    conn.commit()
    conn.close()


# ===========================
# User Management
# ===========================
def add_user(username, password_hash, role="user"):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
        INSERT INTO users (username, password, role)
        VALUES (?, ?, ?)
        """, (username, password_hash, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def verify_user(username, password_hash):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE username=? AND password=?", (username, password_hash))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username, role FROM users")
    rows = c.fetchall()
    conn.close()
    return rows


def get_user_count():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    conn.close()
    return total


def delete_user(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()
    conn.close()


def get_user_info(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username, role FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    return {"username": row[0], "role": row[1]} if row else {}


# ===========================
# SEARCH LOGGING (correct version)
# ===========================
def log_user_search(username, city, temp):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    c.execute("""
        INSERT INTO logs (username, timestamp, city, temp)
        VALUES (?, ?, ?, ?)
    """, (username, timestamp, city, temp))

    conn.commit()
    conn.close()


def get_logs_for_user(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    if username:
        c.execute("""
            SELECT timestamp, city, temp
            FROM logs
            WHERE username = ?
            ORDER BY timestamp DESC
        """, (username,))
    else:
        c.execute("SELECT timestamp, city, temp FROM logs ORDER BY timestamp DESC")

    rows = c.fetchall()
    conn.close()
    return rows
print("USING DATABASE AT:", os.path.abspath(DB_FILE))