from django.test import TestCase
from datetime import date, datetime
from kernel.jinja2.filters import dmy, dmyt, zfill, get_filters


class JinjaFiltersTestCase(TestCase):
    def test_dmy_with_date(self):
        """Проверка преобразования date в строку 'dd.mm.YYYY'"""
        test_date = date(2025, 2, 25)
        self.assertEqual(dmy(test_date), "25.02.2025")

    def test_dmy_with_datetime(self):
        """Проверка преобразования datetime в строку 'dd.mm.YYYY'"""
        test_datetime = datetime(2025, 2, 25, 14, 30, 45)
        self.assertEqual(dmy(test_datetime), "25.02.2025")

    def test_dmy_with_string(self):
        """Проверка, что строка остается неизменной"""
        self.assertEqual(dmy("some string"), "some string")

    def test_dmyt_with_datetime(self):
        """Проверка преобразования datetime в строку 'dd.mm.YYYY HH:MM:SS'"""
        test_datetime = datetime(2025, 2, 25, 14, 30, 45)
        self.assertEqual(dmyt(test_datetime), "25.02.2025 14:30:45")

    def test_dmyt_with_date(self):
        """Проверка, что date без времени форматируется правильно"""
        test_date = date(2025, 2, 25)
        self.assertEqual(dmyt(test_date), "25.02.2025 00:00:00")

    def test_dmyt_with_string(self):
        """Проверка, что строка остается неизменной"""
        self.assertEqual(dmyt("some string"), "some string")

    def test_zfill(self):
        """Проверка дополнения нулями"""
        self.assertEqual(zfill(42, 5), "00042")
        self.assertEqual(zfill("7", 3), "007")
        self.assertEqual(zfill("12345", 3), "12345")  # Длина уже больше, не должно изменяться

    def test_get_filters(self):
        """Проверка, что get_filters возвращает корректный словарь"""
        filters = get_filters()
        self.assertIn("dmy", filters)
        self.assertIn("dmyt", filters)
        self.assertIn("zfill", filters)
        self.assertEqual(filters["dmy"], dmy)
        self.assertEqual(filters["dmyt"], dmyt)
        self.assertEqual(filters["zfill"], zfill)
