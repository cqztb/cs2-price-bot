"""Обработчики команд бота и диалоги поиска и подписки.

Диалоги построены на конечном автомате (FSM) библиотеки aiogram. Так как для
оружия в Steam цена зависит от износа (качества), бот после ввода названия
спрашивает износ и StatTrak, а затем собирает точное имя предмета.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import steam_client
import storage
from logic import build_market_hash_name, EXTERIORS

router = Router()

# Подсказка о том, в каком виде писать название предмета.
NAME_HINT = (
    "Введите название предмета так, как оно написано на площадке Steam, "
    "без указания износа.\n"
    "Примеры:\n"
    "• Оружие: AK-47 | Redline\n"
    "• Нож или перчатки: ★ Karambit | Doppler\n"
    "• Наклейка: Sticker | Titan | Katowice 2014\n"
    "• Агент: Sir Bloody Miami Darryl | The Professionals\n"
    "Износ и StatTrak я спрошу отдельно."
)

# Меню выбора износа (качества).
QUALITY_MENU = (
    "Выберите качество (износ). Для оружия и ножей выберите 1–5; для наклеек, "
    "агентов, кейсов и прочих предметов без износа выберите 0.\n"
    "1 — Прямо с завода (Factory New)\n"
    "2 — Немного поношенное (Minimal Wear)\n"
    "3 — После полевых испытаний (Field-Tested)\n"
    "4 — Поношенное (Well-Worn)\n"
    "5 — Закалённое в боях (Battle-Scarred)\n"
    "0 — без износа (другой тип предмета)"
)


class Flow(StatesGroup):
    """Состояния диалога. Используются и для поиска, и для подписки;
    что именно делать в конце, хранится в данных как mode."""
    waiting_name = State()
    waiting_quality = State()
    waiting_stattrak = State()
    waiting_direction = State()
    waiting_price = State()


# -------------------- команды --------------------

@router.message(Command("start"))
async def cmd_start(message):
    storage.add_user(message.chat.id, message.from_user.username)
    await message.answer(
        "Привет! Я слежу за ценами на предметы Counter-Strike 2 в Steam.\n"
        "Команды:\n"
        "/search — узнать цену предмета\n"
        "/track — создать подписку на цену\n"
        "/list — мои подписки\n"
        "/delete <номер> — удалить подписку\n"
        "/history — история цен по моим подпискам"
    )


@router.message(Command("search"))
async def cmd_search(message, state: FSMContext):
    await state.clear()
    await state.update_data(mode="search")
    await state.set_state(Flow.waiting_name)
    await message.answer(NAME_HINT)


@router.message(Command("track"))
async def cmd_track(message, state: FSMContext):
    await state.clear()
    await state.update_data(mode="track")
    await state.set_state(Flow.waiting_name)
    await message.answer(NAME_HINT)


@router.message(Command("list"))
async def cmd_list(message):
    subs = storage.get_user_subscriptions(message.chat.id)
    if not subs:
        await message.answer("У вас пока нет подписок.")
        return
    lines = []
    for s in subs:
        arrow = "снижение до" if s["direction"] == "down" else "рост до"
        lines.append(f"№{s['sub_id']}: {s['title']} — {arrow} {s['threshold']}")
    await message.answer("Ваши подписки:\n" + "\n".join(lines))


@router.message(Command("delete"))
async def cmd_delete(message):
    arg = message.text.replace("/delete", "", 1).strip()
    if not arg.isdigit():
        await message.answer("Укажите номер подписки, например: /delete 3")
        return
    storage.delete_subscription(message.chat.id, int(arg))
    await message.answer("Подписка удалена.")


@router.message(Command("history"))
async def cmd_history(message):
    subs = storage.get_user_subscriptions(message.chat.id)
    if not subs:
        await message.answer(
            "У вас нет подписок, поэтому история ещё не собирается. "
            "Создайте подписку командой /track."
        )
        return
    lines = []
    for s in subs:
        item_id = storage.get_or_create_item(s["market_hash_name"])
        rows = storage.get_history(item_id, limit=3)
        if rows:
            prices = ", ".join(str(r["price"]) for r in rows)
            lines.append(f"{s['title']}: {prices}")
        else:
            lines.append(f"{s['title']}: записей пока нет")
    await message.answer("История последних цен:\n" + "\n".join(lines))


# -------------------- шаги диалога --------------------

@router.message(Flow.waiting_name)
async def step_name(message, state: FSMContext):
    await state.update_data(base=message.text.strip())
    await state.set_state(Flow.waiting_quality)
    await message.answer(QUALITY_MENU)


@router.message(Flow.waiting_quality)
async def step_quality(message, state: FSMContext):
    choice = message.text.strip()
    if choice == "0":
        await state.update_data(exterior=None, stattrak=False)
        await finish_item(message, state)
        return
    if choice in EXTERIORS:
        await state.update_data(exterior=choice)
        await state.set_state(Flow.waiting_stattrak)
        await message.answer("Это StatTrak™? Напишите да или нет.")
        return
    await message.answer("Введите число от 0 до 5.")


@router.message(Flow.waiting_stattrak)
async def step_stattrak(message, state: FSMContext):
    answer = message.text.strip().lower()
    if answer not in ("да", "нет"):
        await message.answer("Напишите да или нет.")
        return
    await state.update_data(stattrak=(answer == "да"))
    await finish_item(message, state)


async def finish_item(message, state: FSMContext):
    """Собирает точное имя предмета и продолжает в зависимости от режима."""
    data = await state.get_data()
    name = build_market_hash_name(data["base"], data.get("exterior"),
                                  data.get("stattrak", False))
    await state.update_data(name=name)
    if data["mode"] == "search":
        info = await steam_client.get_price(name)
        await state.clear()
        if info is None or info["price"] is None:
            await message.answer(
                f"Не удалось найти цену для «{name}».\n"
                "Проверьте название и износ (для оружия износ обязателен) "
                "или попробуйте позже."
            )
            return
        await message.answer(
            f"Предмет: {name}\n"
            f"Цена: {info['price_text']}\n"
            f"Предложений: {info['volume']}"
        )
    else:  # mode == "track"
        await state.set_state(Flow.waiting_direction)
        await message.answer(
            "Когда уведомить? Напишите:\n"
            "down — когда цена снизится до порога\n"
            "up — когда цена вырастет до порога"
        )


@router.message(Flow.waiting_direction)
async def step_direction(message, state: FSMContext):
    direction = message.text.strip().lower()
    if direction not in ("down", "up"):
        await message.answer("Напишите down или up.")
        return
    await state.update_data(direction=direction)
    await state.set_state(Flow.waiting_price)
    await message.answer("Введите пороговую цену, например 1500:")


@router.message(Flow.waiting_price)
async def step_price(message, state: FSMContext):
    try:
        threshold = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Цену нужно ввести числом, например 1500. Попробуйте ещё раз:")
        return
    if threshold < 0:
        await message.answer("Цена не может быть отрицательной. Попробуйте ещё раз:")
        return
    data = await state.get_data()
    storage.add_subscription(message.chat.id, data["name"], data["direction"], threshold)
    await state.clear()
    await message.answer(
        f"Подписка на «{data['name']}» создана. "
        f"Я сообщу, когда цена достигнет {threshold}."
    )
