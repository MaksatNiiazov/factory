from django.test import TestCase
import pytz
from kernel.api.serializers import UserTimeZoneSerializer


class UserTimeZoneSerializerTest(TestCase):
    def test_valid_timezone(self):
        """Проверка сериализации корректного часового пояса"""
        valid_timezone = pytz.all_timezones[0]
        data = {"timezone": valid_timezone}

        serializer = UserTimeZoneSerializer(data=data)

        if not serializer.is_valid():
            print(serializer.errors)

        self.assertTrue(serializer.is_valid(), msg=serializer.errors)

    def test_invalid_timezone(self):
        """Проверка ошибки при неверном часовом поясе"""
        data = {"timezone": "неверный_пояс"}

        serializer = UserTimeZoneSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("timezone", serializer.errors)
