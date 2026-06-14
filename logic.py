"""Чистые функции логики: разбор цены, проверка условия подписки и сборка
точного имени предмета для Steam.

Вынесены в отдельный файл без сетевых зависимостей, чтобы их было удобно
тестировать.
"""

import re

# Износы (качества) оружия. Код, который вводит пользователь, -> (русское
# название для подсказки, английское название для имени в Steam).
# Steam в market_hash_name использует именно английские названия износа.
EXTERIORS = {
    "1": ("Прямо с завода", "Factory New"),
    "2": ("Немного поношенное", "Minimal Wear"),
    "3": ("После полевых испытаний", "Field-Tested"),
    "4": ("Поношенное", "Well-Worn"),
    "5": ("Закалённое в боях", "Battle-Scarred"),
}


def parse_price(text):
    """Превращает строку вида '1 234,56 руб.' в число 1234.56.

    Если разобрать не получилось — возвращает None.
    """
    if not text:
        return None
    # Заменяем неразрывные пробелы обычными.
    text = text.replace("\xa0", " ")
    # Находим само число: цифры (возможно с пробелами-разделителями тысяч)
    # и необязательную дробную часть после запятой. Текст валюты ("руб.")
    # и точка из сокращения в число не попадают.
    match = re.search(r"\d[\d\s]*(?:,\d+)?", text)
    if not match:
        return None
    number = match.group(0).replace(" ", "").replace(",", ".")
    try:
        return float(number)
    except ValueError:
        return None


def condition_met(direction, threshold, price):
    """Проверяет, выполнено ли условие подписки.

    direction == 'down' — подписка на снижение: срабатывает,
        когда цена опустилась до порога или ниже.
    direction == 'up'   — подписка на рост: срабатывает,
        когда цена поднялась до порога или выше.
    """
    if price is None:
        return False
    if direction == "down":
        return price <= threshold
    if direction == "up":
        return price >= threshold
    return False


def build_market_hash_name(base_name, exterior_code=None, stattrak=False):
    """Собирает точное имя предмета для Steam (market_hash_name).

    base_name     — базовое название без износа, как на площадке
                    (например, 'AK-47 | Redline').
    exterior_code — код износа '1'..'5' или None (для наклеек, агентов,
                    кейсов и прочих предметов без износа).
    stattrak      — True, если предмет StatTrak™.

    Для оружия и ножей Steam требует указывать износ в скобках на английском,
    например 'AK-47 | Redline (Field-Tested)'. У StatTrak™ перед именем
    добавляется 'StatTrak™ '. У предметов без износа имя не меняется.
    """
    name = base_name.strip()
    if exterior_code in EXTERIORS:
        exterior_en = EXTERIORS[exterior_code][1]
        prefix = "StatTrak™ " if stattrak else ""
        name = f"{prefix}{name} ({exterior_en})"
    return name
