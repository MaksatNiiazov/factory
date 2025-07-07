from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from kernel.models import User

class UserSettingsViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        """Создание тестового пользователя"""
        cls.user = User.objects.create_superuser(email="testuser@example.com", password="testpass")

    def setUp(self):
        """Аутентификация перед каждым тестом"""
        response = self.client.post(
            reverse("user-login"),
            {"username": "testuser@example.com", "password": "testpass"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg="Ошибка аутентификации!")
        self.token = response.data.get("token")
        self.assertIsNotNone(self.token, msg="Токен не был получен!")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_set_locale_authorized(self):
        """Тест установки локали для авторизованного пользователя"""
        url = reverse("user-set-locale", args=[self.user.id])
        data = {"locale": "ru"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f"Ошибка при установке локали: {response.json()}")

    def test_set_locale_invalid_data(self):
        """Тест установки локали с некорректными данными"""
        url = reverse("user-set-locale", args=[self.user.id])
        data = {"locale": "invalid-lang"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=f"Некорректный код локали: {response.json()}")

    def test_set_timezone_authorized(self):
        """Тест установки временной зоны для авторизованного пользователя"""
        url = reverse("user-set-timezone", args=[self.user.id])
        data = {"timezone": "Asia/Bishkek"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f"Ошибка при установке временной зоны: {response.json()}")

    def test_set_timezone_invalid_data(self):
        """Тест установки временной зоны с некорректными данными"""
        url = reverse("user-set-timezone", args=[self.user.id])
        data = {"timezone": "Invalid/Timezone"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=f"Некорректный код временной зоны: {response.json()}")

