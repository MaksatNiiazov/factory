from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


class AuthViewSetTest(TestCase):
    def setUp(self):
        """Создаём тестового пользователя"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="testuser@example.com",
            first_name="Test",
            last_name="User",
            password="securepassword"
        )

    def test_login_success(self):
        """Проверка успешного входа"""
        data = {"username": self.user.email, "password": "securepassword"}
        response = self.client.post("/api/users/login/", data, format="json")


        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.json())

    def test_login_fail_wrong_password(self):
        """Проверка ошибки входа при неверном пароле"""
        data = {"username": self.user.email, "password": "wrongpassword"}
        response = self.client.post("/api/users/login/", data, format="json")

        self.assertEqual(response.status_code, 403)

    def test_logout_success(self):
        """Проверка успешного выхода"""

        login_data = {"username": self.user.email, "password": "securepassword"}
        login_response = self.client.post("/api/users/login/", login_data, format="json")
        token = login_response.json().get("token")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.post("/api/users/logout/")

        self.assertEqual(response.status_code, 200)

    def test_access_after_logout(self):
        """Проверка, что после выхода доступ к API запрещён"""

        login_data = {"username": self.user.email, "password": "securepassword"}
        login_response = self.client.post("/api/users/login/", login_data, format="json")
        token = login_response.json().get("token")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        self.client.post("/api/users/logout/")

        response = self.client.get("/api/users/me/")
        self.assertEqual(response.status_code, 403)
