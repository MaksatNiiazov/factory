from django.test import TestCase
from django.contrib.auth import get_user_model
from kernel.models import Organization
from kernel.api.serializers import UserSerializer

User = get_user_model()


class UserSerializerTest(TestCase):
    def setUp(self):
        """Создаём тестовые данные перед каждым тестом"""
        self.organization = Organization.objects.create(name="Тестовая организация")
        self.user = User.objects.create(
            email="test@example.com",
            first_name="Иван",
            last_name="Иванов",
            middle_name="Иванович",
            organization=self.organization,
            status=User.INTERNAL_USER
        )

    def test_user_serialization(self):
        """Проверка сериализации пользователя"""
        serializer = UserSerializer(instance=self.user)
        data = serializer.data

        self.assertEqual(data["email"], self.user.email)
        self.assertEqual(data["first_name"], self.user.first_name)
        self.assertEqual(data["last_name"], self.user.last_name)
        self.assertEqual(data["middle_name"], self.user.middle_name)
        self.assertEqual(data["organization"], self.organization.id)
        self.assertEqual(data["status"], self.user.status)

    def test_user_deserialization(self):
        """Проверка десериализации данных пользователя"""
        valid_data = {
            "email": "newuser@example.com",
            "first_name": "Петр",
            "last_name": "Петров",
            "middle_name": "Петрович",
            "organization": self.organization.id,
            "status": User.EXTERNAL_USER,
            "password": "securepassword123"
        }

        serializer = UserSerializer(data=valid_data)

        if not serializer.is_valid():
            print(serializer.errors)

        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
