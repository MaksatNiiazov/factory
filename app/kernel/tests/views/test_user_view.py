from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient
from kernel.models import Organization

User = get_user_model()


class UserViewSetTest(TestCase):
    def setUp(self):
        """Создаём тестового пользователя, организацию и даём нужные права"""
        self.client = APIClient()
        self.organization = Organization.objects.create(name="Тестовая организация")

        self.user = User.objects.create_user(
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            password="adminpassword",
            is_staff=True
        )

        self.user.user_permissions.add(
            Permission.objects.get(codename="view_user"),
            Permission.objects.get(codename="add_user")
        )

    def test_list_users_unauthorized(self):
        """Проверка, что без авторизации список пользователей недоступен"""
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, 403)

    def test_list_users_authorized(self):
        """Проверка, что пользователь с правами может получить список пользователей"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, 200)

    def test_create_user_unauthorized(self):
        """Попытка создать пользователя без авторизации"""
        data = {
            "email": "testuser@example.com",
            "first_name": "Test",
            "last_name": "User",
            "organization": self.organization.id,
            "password": "securepassword",
            "status": User.EXTERNAL_USER
        }
        response = self.client.post("/api/users/", data)
        self.assertEqual(response.status_code, 403)

    def test_create_user_authorized(self):
        """Проверка создания нового пользователя через API"""
        self.client.force_authenticate(user=self.user)

        data = {
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "organization": self.organization.id,
            "password": "securepassword",
            "status": User.EXTERNAL_USER
        }

        response = self.client.post("/api/users/", data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.count(), 2)
