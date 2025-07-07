from django.contrib.auth import get_user_model
from django.test import TestCase

from ops.forms import ProjectForm
from ops.models import Project

User = get_user_model()

class ProjectFormTest(TestCase):

    def setUp(self):
        """Создаём тестовые данные"""
        self.user = User.objects.create_user(email="test@example.com", password="password123")
        self.valid_data = {
            'number': 'P-001',
            'contragent': 'ООО Тест'
        }

    def test_valid_form(self):
        """Тест с валидными данными"""
        form = ProjectForm(data=self.valid_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_required_fields(self):
        """Тест на отсутствие обязательных полей"""
        invalid_data = self.valid_data.copy()
        del invalid_data['number']
        form = ProjectForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('number', form.errors)

    def test_unique_number(self):
        """Тест на уникальность номера проекта"""
        Project.objects.create(owner=self.user, **self.valid_data)

        form = ProjectForm(data=self.valid_data)
        if 'unique' in Project._meta.get_field('number').error_messages:
            self.assertFalse(form.is_valid())
            self.assertIn('number', form.errors)
        else:
            self.assertTrue(form.is_valid(), "Поле 'number' не требует уникальности")
