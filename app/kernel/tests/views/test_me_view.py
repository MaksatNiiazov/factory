from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

User = get_user_model()


class MeViewSetTest(TestCase):
    def setUp(self):
        """Создаём тестового пользователя и даём ему права на изменение профиля"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="testuser@example.com",
            first_name="Test",
            last_name="User",
            password="securepassword",
            status=User.EXTERNAL_USER
        )

        self.user.user_permissions.add(Permission.objects.get(codename="change_user"))

    def test_me_unauthorized(self):
        """Проверка, что без авторизации доступ к /me/ запрещён"""
        response = self.client.get("/api/users/me/")
        self.assertEqual(response.status_code, 403)

    def test_me_authorized(self):
        """Проверка, что авторизованный пользователь получает свои данные"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/users/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], self.user.email)

    def test_me_update(self):
        """Проверка обновления данных пользователя через /me/"""
        self.client.force_authenticate(user=self.user)

        data = {
            "first_name": "UpdatedName",
            "status": self.user.status
        }

        response = self.client.patch("/api/users/me/", data, format="json")

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "UpdatedName")
