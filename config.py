"""Загрузка настроек бота из файла .env.

В .env хранятся секретные данные, которые нельзя писать прямо в коде:
    BOT_TOKEN=токен_бота_из_BotFather
    DB_PATH=price_bot.db
    CHECK_INTERVAL=600
"""

import os


def load_env(path=".env"):
    """Читает файл .env и кладёт значения в переменные окружения."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()


load_env()

# Токен бота берём из окружения. Если его нет — программа не запустится.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Путь к файлу базы данных.
DB_PATH = os.environ.get("DB_PATH", "price_bot.db")

# Как часто (в секундах) проверять цены. По умолчанию раз в 10 минут.
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "600"))
