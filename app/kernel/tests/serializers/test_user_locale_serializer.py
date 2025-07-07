from django.test import TestCase
from django.conf import settings
from kernel.api.serializers import UserLocaleSerializer


class UserLocaleSerializerTest(TestCase):
    def test_valid_locale(self):
        """Проверка сериализации корректного языка"""
        valid_locale = settings.LANGUAGES[0][0]
        data = {"locale": valid_locale}

        serializer = UserLocaleSerializer(data=data)

        if not serializer.is_valid():
            print(serializer.errors)

        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

    def test_invalid_locale(self):
        """Проверка ошибки при неверном языке"""
        data = {"locale": "неверный_язык"}

        serializer = UserLocaleSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("locale", serializer.errors)
