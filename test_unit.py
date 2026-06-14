"""Модульные (юнит) тесты.

Здесь проверяются отдельные чистые функции из модуля logic — разбор
строки цены и проверка условия подписки. Эти функции не обращаются ни к
базе данных, ни к сети, поэтому тесты выполняются быстро и независимо.

Запуск:  python -m unittest test_unit.py
"""

import unittest

from logic import parse_price, condition_met, build_market_hash_name


class TestParsePrice(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(parse_price("59,99 руб."), 59.99)

    def test_thousands(self):
        self.assertEqual(parse_price("1 234,56 руб."), 1234.56)

    def test_big_number(self):
        self.assertEqual(parse_price("12 477,33 pуб."), 12477.33)

    def test_no_decimals(self):
        self.assertEqual(parse_price("100 руб."), 100.0)

    def test_empty(self):
        self.assertIsNone(parse_price(""))

    def test_none(self):
        self.assertIsNone(parse_price(None))


class TestCondition(unittest.TestCase):
    def test_down_triggers_below(self):
        self.assertTrue(condition_met("down", 1500, 1490))

    def test_down_triggers_equal(self):
        self.assertTrue(condition_met("down", 1500, 1500))

    def test_down_not_triggered(self):
        self.assertFalse(condition_met("down", 1500, 1600))

    def test_up_triggers_above(self):
        self.assertTrue(condition_met("up", 2000, 2100))

    def test_up_not_triggered(self):
        self.assertFalse(condition_met("up", 2000, 1900))

    def test_none_price(self):
        self.assertFalse(condition_met("down", 1500, None))


class TestBuildName(unittest.TestCase):
    def test_weapon_with_exterior(self):
        self.assertEqual(
            build_market_hash_name("AK-47 | Redline", "3"),
            "AK-47 | Redline (Field-Tested)")

    def test_weapon_factory_new(self):
        self.assertEqual(
            build_market_hash_name("AWP | Asiimov", "1"),
            "AWP | Asiimov (Factory New)")

    def test_stattrak(self):
        self.assertEqual(
            build_market_hash_name("AK-47 | Redline", "3", True),
            "StatTrak™ AK-47 | Redline (Field-Tested)")

    def test_no_exterior_keeps_name(self):
        self.assertEqual(
            build_market_hash_name("Sticker | Titan | Katowice 2014", None),
            "Sticker | Titan | Katowice 2014")

    def test_strips_spaces(self):
        self.assertEqual(
            build_market_hash_name("  P250 | Hive  ", "1"),
            "P250 | Hive (Factory New)")


if __name__ == "__main__":
    unittest.main()
