"""Интеграционные тесты.

Здесь проверяется работа модулей вместе с внешними частями:
- класс TestStorage обращается к настоящей базе данных SQLite;
- класс TestSchedulerFlow проверяет полный проход проверки цен
  (scheduler + storage + logic). Вместо настоящего Steam и Telegram
  передаются заглушки, поэтому тест не требует сети и токена бота.

Запуск:  python -m unittest test_integration.py
"""

import os
import tempfile
import unittest

import storage
import scheduler


class TestStorage(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        storage.init_db(self.path)

    def tearDown(self):
        storage._conn.close()
        os.remove(self.path)

    def test_add_user_once(self):
        storage.add_user(111, "arslan")
        storage.add_user(111, "arslan")  # повторно — дубликата быть не должно
        rows = storage._conn.execute("SELECT * FROM users").fetchall()
        self.assertEqual(len(rows), 1)

    def test_subscription_and_list(self):
        storage.add_user(111, "arslan")
        storage.add_subscription(111, "AK-47 | Redline", "down", 1500)
        subs = storage.get_user_subscriptions(111)
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0]["direction"], "down")
        self.assertEqual(subs[0]["threshold"], 1500)

    def test_item_not_duplicated(self):
        storage.add_user(111, "arslan")
        storage.add_subscription(111, "AK-47 | Redline", "down", 1500)
        storage.add_subscription(111, "AK-47 | Redline", "up", 3000)
        items = storage._conn.execute("SELECT * FROM items").fetchall()
        self.assertEqual(len(items), 1)  # один и тот же предмет хранится один раз

    def test_delete_subscription(self):
        storage.add_user(111, "arslan")
        storage.add_subscription(111, "Glock-18 | Fade", "down", 5000)
        sub_id = storage.get_user_subscriptions(111)[0]["sub_id"]
        storage.delete_subscription(111, sub_id)
        self.assertEqual(len(storage.get_user_subscriptions(111)), 0)

    def test_history(self):
        item_id = storage.get_or_create_item("Desert Eagle | Blaze")
        storage.add_history(item_id, 7000)
        storage.add_history(item_id, 6800)
        rows = storage.get_history(item_id)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["price"], 6800)  # последний замер идёт первым


class TestSchedulerFlow(unittest.IsolatedAsyncioTestCase):
    """Проверка полного прохода проверки цен с заглушками вместо сети."""

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        storage.init_db(self.path)
        storage.add_user(111, "arslan")
        self.sent = []  # сюда заглушка-отправитель складывает уведомления

    def tearDown(self):
        storage._conn.close()
        os.remove(self.path)

    async def fake_send(self, user_id, name, price_text, direction):
        self.sent.append((user_id, name, direction))

    def make_price(self, value):
        async def fake_get_price(name):
            return {"price": value, "price_text": f"{value} руб.", "volume": "10"}
        return fake_get_price

    async def test_notify_when_price_reached(self):
        # Подписка на снижение до 1500, текущая цена 1490 — должно сработать.
        storage.add_subscription(111, "AK-47 | Redline", "down", 1500)
        await scheduler.run_once(self.make_price(1490), self.fake_send)
        self.assertEqual(len(self.sent), 1)
        # После срабатывания подписка отключается.
        self.assertEqual(len(storage.get_user_subscriptions(111)), 0)

    async def test_no_notify_when_price_high(self):
        # Цена 1600 выше порога 1500 — уведомления быть не должно.
        storage.add_subscription(111, "AK-47 | Redline", "down", 1500)
        await scheduler.run_once(self.make_price(1600), self.fake_send)
        self.assertEqual(len(self.sent), 0)
        self.assertEqual(len(storage.get_user_subscriptions(111)), 1)

    async def test_history_is_written(self):
        # Даже без срабатывания замер цены должен попасть в историю.
        storage.add_subscription(111, "AWP | Asiimov", "down", 100)
        await scheduler.run_once(self.make_price(5000), self.fake_send)
        item_id = storage.get_or_create_item("AWP | Asiimov")
        self.assertEqual(len(storage.get_history(item_id)), 1)

    async def test_network_error_skipped(self):
        # Если источник вернул None (сеть недоступна), проход не падает.
        storage.add_subscription(111, "AK-47 | Redline", "down", 1500)

        async def broken_get_price(name):
            return None

        await scheduler.run_once(broken_get_price, self.fake_send)
        self.assertEqual(len(self.sent), 0)
        self.assertEqual(len(storage.get_user_subscriptions(111)), 1)


if __name__ == "__main__":
    unittest.main()
