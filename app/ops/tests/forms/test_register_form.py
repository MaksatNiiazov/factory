from django.test import TestCase
from django.contrib.auth import get_user_model
from ops.forms import RegisterForm

User = get_user_model()


class RegisterFormTest(TestCase):
    """Тестирование формы регистрации (RegisterForm)"""

    def test_valid_form(self):
        """Тест с валидными данными"""
        form_data = {
            "last_name": "Иванов",
            "first_name": "Иван",
            "email": "ivanov@example.com",
            "password1": "SecurePassword123",
            "password2": "SecurePassword123",
        }
        form = RegisterForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_password_mismatch(self):
        """Тест: пароли должны совпадать"""
        form_data = {
            "last_name": "Иванов",
            "first_name": "Иван",
            "email": "ivanov@example.com",
            "password1": "SecurePassword123",
            "password2": "WrongPassword",
        }
        form = RegisterForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("password1", form.errors)

    def test_email_already_exists(self):
        """Тест: нельзя зарегистрировать пользователя с уже существующей почтой"""
        User.objects.create_user(
            last_name="Петров",
            first_name="Петр",
            email="existing@example.com",
            password="SomePassword",
        )

        form_data = {
            "last_name": "Сидоров",
            "first_name": "Сидор",
            "email": "existing@example.com",
            "password1": "AnotherSecurePassword",
            "password2": "AnotherSecurePassword",
        }
        form = RegisterForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_missing_required_fields(self):
        """Тест: все поля обязательны"""
        form_data = {}
        form = RegisterForm(data=form_data)

        self.assertFalse(form.is_valid())
        required_fields = ["last_name", "first_name", "email", "password1", "password2"]

        for field in required_fields:
            self.assertIn(field, form.errors)
