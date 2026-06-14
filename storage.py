"""Работа с базой данных SQLite.

Здесь собраны все функции для сохранения и чтения данных:
пользователи, предметы, подписки и история цен.
"""

import sqlite3
from datetime import datetime

# Одно соединение с базой на всю программу.
_conn = None


def init_db(path):
    """Создаёт таблицы (если их ещё нет) и открывает соединение."""
    global _conn
    _conn = sqlite3.connect(path)
    _conn.row_factory = sqlite3.Row
    _conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            created_at TEXT);

        CREATE TABLE IF NOT EXISTS items(
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            market_hash_name TEXT UNIQUE,
            title TEXT,
            last_price REAL,
            updated_at TEXT);

        CREATE TABLE IF NOT EXISTS subscriptions(
            sub_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_id INTEGER,
            direction TEXT,
            threshold REAL,
            is_active INTEGER DEFAULT 1);

        CREATE TABLE IF NOT EXISTS price_history(
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            price REAL,
            checked_at TEXT);
        """
    )
    _conn.commit()
    return _conn


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_user(user_id, username):
    """Сохраняет нового пользователя. Если он уже есть — ничего не меняет."""
    _conn.execute(
        "INSERT OR IGNORE INTO users(user_id, username, created_at) VALUES(?, ?, ?)",
        (user_id, username, _now()),
    )
    _conn.commit()


def get_or_create_item(market_hash_name, title=None):
    """Возвращает id предмета. Если предмета ещё нет — создаёт его."""
    row = _conn.execute(
        "SELECT item_id FROM items WHERE market_hash_name = ?", (market_hash_name,)
    ).fetchone()
    if row:
        return row["item_id"]
    cur = _conn.execute(
        "INSERT INTO items(market_hash_name, title) VALUES(?, ?)",
        (market_hash_name, title or market_hash_name),
    )
    _conn.commit()
    return cur.lastrowid


def update_item_price(item_id, price):
    """Запоминает последнюю цену предмета."""
    _conn.execute(
        "UPDATE items SET last_price = ?, updated_at = ? WHERE item_id = ?",
        (price, _now(), item_id),
    )
    _conn.commit()


def add_subscription(user_id, market_hash_name, direction, threshold):
    """Создаёт подписку пользователя на цену предмета."""
    item_id = get_or_create_item(market_hash_name)
    _conn.execute(
        "INSERT INTO subscriptions(user_id, item_id, direction, threshold, is_active) "
        "VALUES(?, ?, ?, ?, 1)",
        (user_id, item_id, direction, threshold),
    )
    _conn.commit()


def get_user_subscriptions(user_id):
    """Список активных подписок пользователя."""
    return _conn.execute(
        "SELECT s.sub_id, i.title, i.market_hash_name, s.direction, s.threshold "
        "FROM subscriptions s JOIN items i ON i.item_id = s.item_id "
        "WHERE s.user_id = ? AND s.is_active = 1",
        (user_id,),
    ).fetchall()


def get_active_subscriptions():
    """Все активные подписки (нужны планировщику для проверки цен)."""
    return _conn.execute(
        "SELECT s.sub_id, s.user_id, s.item_id, i.market_hash_name, "
        "s.direction, s.threshold "
        "FROM subscriptions s JOIN items i ON i.item_id = s.item_id "
        "WHERE s.is_active = 1"
    ).fetchall()


def delete_subscription(user_id, sub_id):
    """Удаляет подписку (помечает её неактивной)."""
    _conn.execute(
        "UPDATE subscriptions SET is_active = 0 WHERE sub_id = ? AND user_id = ?",
        (sub_id, user_id),
    )
    _conn.commit()


def add_history(item_id, price):
    """Сохраняет замер цены в историю."""
    _conn.execute(
        "INSERT INTO price_history(item_id, price, checked_at) VALUES(?, ?, ?)",
        (item_id, price, _now()),
    )
    _conn.commit()


def get_history(item_id, limit=5):
    """Несколько последних замеров цены по предмету."""
    return _conn.execute(
        "SELECT price, checked_at FROM price_history "
        "WHERE item_id = ? ORDER BY record_id DESC LIMIT ?",
        (item_id, limit),
    ).fetchall()
