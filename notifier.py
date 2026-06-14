"""Отправка уведомлений пользователю в Telegram."""


async def notify(bot, user_id, title, price_text, direction):
    """Отправляет сообщение о том, что цена достигла нужного значения."""
    if direction == "down":
        reason = "опустилась до"
    else:
        reason = "поднялась до"
    text = (
        f"🔔 Цена на предмет «{title}» {reason} {price_text}.\n"
        f"Условие вашей подписки выполнено."
    )
    await bot.send_message(user_id, text)
