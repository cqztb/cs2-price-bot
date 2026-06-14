"""Периодическая проверка цен.

Фоновая задача через равные промежутки времени проверяет все активные
подписки: запрашивает цену, сохраняет её в историю и, если условие
выполнено, отправляет уведомление.

Один проход проверки вынесен в функцию run_once. Она получает функцию
получения цены и функцию отправки уведомления как параметры. Это позволяет
тестировать проход без обращения к сети — в тесте вместо настоящего Steam и
Telegram передаются заглушки.
"""

import asyncio

import storage
from logic import condition_met
from config import CHECK_INTERVAL


async def run_once(get_price, send):
    """Один проход по всем активным подпискам."""
    for sub in storage.get_active_subscriptions():
        info = await get_price(sub["market_hash_name"])
        if info is None or info["price"] is None:
            # Цену получить не удалось — пропускаем предмет до следующей проверки.
            continue
        price = info["price"]
        storage.add_history(sub["item_id"], price)
        storage.update_item_price(sub["item_id"], price)
        if condition_met(sub["direction"], sub["threshold"], price):
            await send(sub["user_id"], sub["market_hash_name"],
                       info["price_text"], sub["direction"])
            # Чтобы не повторять уведомление, после срабатывания подписку отключаем.
            storage.delete_subscription(sub["user_id"], sub["sub_id"])


async def check_prices(bot):
    """Бесконечный цикл проверки цен (запускается в фоне)."""
    import steam_client
    import notifier

    async def send(user_id, name, price_text, direction):
        await notifier.notify(bot, user_id, name, price_text, direction)

    while True:
        await run_once(steam_client.get_price, send)
        await asyncio.sleep(CHECK_INTERVAL)
