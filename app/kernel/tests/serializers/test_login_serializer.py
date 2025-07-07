from django.test import TestCase
from kernel.api.serializers import LoginSerializer


class LoginSerializerTest(TestCase):
    def test_valid_login(self):
        """Проверка валидации корректных данных для входа"""
        data = {"username": "testuser@example.com", "password": "securepassword"}
        serializer = LoginSerializer(data=data)

        if not serializer.is_valid():
            print(serializer.errors)

        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

    def test_invalid_login_missing_fields(self):
        """Проверка ошибки при отсутствии обязательных полей"""
        data = {"username": "testuser@example.com"}
        serializer = LoginSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_invalid_login_empty_fields(self):
        """Проверка ошибки при пустых значениях"""
        data = {"username": "", "password": ""}
        serializer = LoginSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("username", serializer.errors)
        self.assertIn("password", serializer.errors)
