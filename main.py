"""Точка входа: запуск бота и фоновой проверки цен."""

import asyncio

from aiogram import Bot, Dispatcher

import storage
import handlers
import scheduler
from config import BOT_TOKEN, DB_PATH


async def main():
    if not BOT_TOKEN:
        raise SystemExit("Не задан BOT_TOKEN. Укажите его в файле .env")

    storage.init_db(DB_PATH)

    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(handlers.router)

    # Запускаем фоновую проверку цен параллельно с приёмом сообщений.
    asyncio.create_task(scheduler.check_prices(bot))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
