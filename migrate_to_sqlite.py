import asyncio
import json
import sqlite3
import os
from pathlib import Path

DATA_DIR = Path("data")

def create_tables(cursor):
    # Пользователи
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        last_seen TEXT,
        message_count INTEGER DEFAULT 0,
        blocked_messages INTEGER DEFAULT 0,
        had_access BOOLEAN DEFAULT 1
    )
    """)
    
    # Доверие
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trust (
        user_id INTEGER PRIMARY KEY,
        trust_level REAL DEFAULT 0.0,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)
    
    # Настроение
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS moods (
        user_id INTEGER PRIMARY KEY,
        mood TEXT DEFAULT 'обычное',
        timestamp TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)

    # Донаты
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS donations (
        transaction_id TEXT PRIMARY KEY,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        stars INTEGER,
        date TEXT,
        refunded BOOLEAN DEFAULT 0,
        refund_date TEXT,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)
    
    # Балансы
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS balances (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
    """)

async def migrate():
    print("Начинаем миграцию на SQLite...")
    conn = sqlite3.connect("mahiro.db")
    cursor = conn.cursor()
    
    create_tables(cursor)
    
    # Миграция пользователей
    if (DATA_DIR / "users.json").exists():
        with open(DATA_DIR / "users.json", "r", encoding="utf-8") as f:
            users = json.load(f)
            for user in users:
                cursor.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, last_seen, message_count, blocked_messages, had_access)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user.get("user_id"),
                    user.get("username"),
                    user.get("first_name"),
                    user.get("last_name"),
                    user.get("last_seen"),
                    user.get("message_count", 0),
                    user.get("blocked_messages", 0),
                    user.get("had_access", True)
                ))
        print("✅ Пользователи мигрированы")

    # Миграция доверия
    if (DATA_DIR / "trust_levels.json").exists():
        with open(DATA_DIR / "trust_levels.json", "r", encoding="utf-8") as f:
            trust_levels = json.load(f)
            for uid, data in trust_levels.items():
                cursor.execute("INSERT OR REPLACE INTO trust (user_id, trust_level) VALUES (?, ?)", 
                              (int(uid), data.get("level", 0.0)))
        print("✅ Доверие мигрировано")

    # Миграция настроения
    if (DATA_DIR / "moods.json").exists():
        with open(DATA_DIR / "moods.json", "r", encoding="utf-8") as f:
            moods = json.load(f)
            for uid, data in moods.items():
                cursor.execute("INSERT OR REPLACE INTO moods (user_id, mood, timestamp) VALUES (?, ?, ?)", 
                              (int(uid), data.get("mood", "обычное"), data.get("timestamp")))
        print("✅ Настроения мигрированы")
        
    # Миграция донатов
    if (DATA_DIR / "donations.json").exists():
        with open(DATA_DIR / "donations.json", "r", encoding="utf-8") as f:
            donations = json.load(f)
            for d in donations:
                cursor.execute("""
                INSERT OR REPLACE INTO donations 
                (transaction_id, user_id, username, first_name, stars, date, refunded, refund_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    d.get("transaction_id"),
                    d.get("user_id"),
                    d.get("username"),
                    d.get("first_name"),
                    d.get("stars"),
                    d.get("date"),
                    d.get("refunded", False),
                    d.get("refund_date")
                ))
        print("✅ Донаты мигрированы")
        
    # Миграция балансов
    if (DATA_DIR / "star_balances.json").exists():
        with open(DATA_DIR / "star_balances.json", "r", encoding="utf-8") as f:
            balances = json.load(f)
            for uid, balance in balances.items():
                cursor.execute("INSERT OR REPLACE INTO balances (user_id, balance) VALUES (?, ?)", 
                              (int(uid), balance))
        print("✅ Балансы мигрированы")

    conn.commit()
    conn.close()
    print("🎉 Миграция успешно завершена! Создана база данных mahiro.db")

if __name__ == "__main__":
    asyncio.run(migrate())
