"""Получение цены предмета из Steam Community Market.

Используется открытый адрес обзора цены priceoverview.
В запрос передаётся номер игры (730 — Counter-Strike 2),
код валюты (5 — рубль) и имя предмета на рынке.
"""

import aiohttp

from logic import parse_price

STEAM_URL = "https://steamcommunity.com/market/priceoverview/"
APP_ID = 730       # Counter-Strike 2
CURRENCY = 5       # российский рубль

# Steam часто отклоняет запросы без заголовка User-Agent,
# поэтому представляемся как обычный браузер.
HEADERS = {"User-Agent": "Mozilla/5.0 (price-bot)"}


async def get_price(market_hash_name):
    """Запрашивает цену предмета у Steam.

    Возвращает словарь с ценой и числом предложений
    или None, если данные получить не удалось.
    """
    params = {
        "appid": APP_ID,
        "currency": CURRENCY,
        "market_hash_name": market_hash_name,
    }
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(STEAM_URL, params=params, timeout=10) as resp:
                if resp.status == 429:
                    # Слишком много запросов — Steam просит подождать.
                    # Пропускаем эту проверку, попробуем в следующий раз.
                    return None
                if resp.status != 200:
                    return None
                data = await resp.json()
    except Exception:
        # Сеть недоступна или ответ некорректный — не падаем, а сообщаем об ошибке.
        return None

    if not data or not data.get("success"):
        return None

    return {
        "price_text": data.get("lowest_price"),
        "price": parse_price(data.get("lowest_price")),
        "volume": data.get("volume"),
    }
