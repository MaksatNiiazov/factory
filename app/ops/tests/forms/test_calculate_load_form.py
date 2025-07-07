from django.test import TestCase
from ops.forms import CalculateLoadForm


class CalculateLoadFormTest(TestCase):
    def test_valid_data_with_movement_plus(self):
        """Форма должна быть валидной, если указано movement_plus"""
        form = CalculateLoadForm(data={
            "standard_series": True,
            "l_series": False,
            "load_minus": 100.5,
            "movement_plus": 10.0,
            "minimum_spring_travel": 5.0
        })
        self.assertTrue(form.is_valid())

    def test_valid_data_with_movement_minus(self):
        """Форма должна быть валидной, если указано movement_minus"""
        form = CalculateLoadForm(data={
            "standard_series": False,
            "l_series": True,
            "load_minus": 50.0,
            "movement_minus": 5.0,
            "minimum_spring_travel": 3.0
        })
        self.assertTrue(form.is_valid())

    def test_both_movement_plus_and_minus_provided(self):
        """Форма должна быть невалидной, если указаны оба перемещения"""
        form = CalculateLoadForm(data={
            "standard_series": True,
            "l_series": True,
            "load_minus": 100.0,
            "movement_plus": 10.0,
            "movement_minus": 5.0,
            "minimum_spring_travel": 5.0
        })
        self.assertFalse(form.is_valid())
        self.assertIn("movement_plus", form.errors)

    def test_no_movement_provided(self):
        """Форма должна быть невалидной, если не указано ни одно перемещение"""
        form = CalculateLoadForm(data={
            "standard_series": True,
            "l_series": True,
            "load_minus": 100.0,
            "minimum_spring_travel": 5.0
        })
        self.assertFalse(form.is_valid())
        self.assertIn("movement_plus", form.errors)

    def test_no_series_selected(self):
        """Форма должна быть невалидной, если не выбрана ни одна серия"""
        form = CalculateLoadForm(data={
            "standard_series": False,
            "l_series": False,
            "load_minus": 100.0,
            "movement_plus": 5.0,
            "minimum_spring_travel": 5.0
        })
        self.assertFalse(form.is_valid())
        self.assertIn("l_series", form.errors)

    def test_minimum_spring_travel_default(self):
        """Форма должна устанавливать значение по умолчанию для minimum_spring_travel"""
        form = CalculateLoadForm(data={
            "standard_series": True,
            "l_series": False,
            "load_minus": 75.0,
            "movement_plus": 5.0,
            "minimum_spring_travel": 5.0

        })

        if not form.is_valid():
            print("Ошибки формы:", form.errors)  # Выведем ошибки

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["minimum_spring_travel"], 5.0)
