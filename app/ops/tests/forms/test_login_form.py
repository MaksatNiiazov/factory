from django.test import TestCase
from django.contrib.auth import get_user_model
from ops.forms import LoginForm

User = get_user_model()


class LoginFormTest(TestCase):
    """Тестирование формы входа (LoginForm)"""

    def test_valid_form(self):
        """Тест с валидными данными"""
        form_data = {"username": "testuser", "password": "securepassword"}
        form = LoginForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_empty_username(self):
        """Тест: поле username не должно быть пустым"""
        form_data = {"username": "", "password": "securepassword"}
        form = LoginForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_empty_password(self):
        """Тест: поле password не должно быть пустым"""
        form_data = {"username": "testuser", "password": ""}
        form = LoginForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)
