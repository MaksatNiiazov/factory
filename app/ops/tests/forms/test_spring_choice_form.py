from django.test import TestCase
from ops.forms import SpringChoiceForm
from ops.choices import EstimatedState


class SpringChoiceFormTest(TestCase):

    def setUp(self):
        """Начальные данные для тестов"""
        self.valid_data = {
            'load_plus_x': 10,
            'load_plus_y': 5,
            'load_plus_z': 0,
            'load_minus_x': 2,
            'load_minus_y': 1,
            'load_minus_z': 0,
            'additional_load_x': 0,
            'additional_load_y': 0,
            'additional_load_z': 0,
            'test_load_z': 0,
            'move_plus_z': 3,
            'move_minus_z': 2,
            'estimated_state': EstimatedState.COLD_LOAD
        }

    def test_valid_form(self):
        """Тест с валидными данными"""
        form = SpringChoiceForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_required_fields(self):
        """Тест на отсутствие обязательного поля estimated_state"""
        invalid_data = self.valid_data.copy()
        del invalid_data['estimated_state']
        form = SpringChoiceForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('estimated_state', form.errors)

    def test_cleaned_data_defaults_to_zero(self):
        """Проверка, что все пустые числовые поля автоматически заменяются на 0"""
        partial_data = {
            'estimated_state': EstimatedState.COLD_LOAD
        }
        form = SpringChoiceForm(data=partial_data)
        self.assertTrue(form.is_valid(), form.errors)
        cleaned_data = form.cleaned_data

        for field in [
            'load_plus_x', 'load_plus_y', 'load_plus_z',
            'load_minus_x', 'load_minus_y', 'load_minus_z',
            'additional_load_x', 'additional_load_y', 'additional_load_z',
            'test_load_z', 'move_plus_z', 'move_minus_z',
        ]:
            self.assertEqual(cleaned_data[field], 0)

    def test_invalid_estimated_state(self):
        """Тест с некорректным значением для estimated_state"""
        invalid_data = self.valid_data.copy()
        invalid_data['estimated_state'] = "INVALID_VALUE"
        form = SpringChoiceForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('estimated_state', form.errors)
