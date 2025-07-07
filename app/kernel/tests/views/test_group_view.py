from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework.test import APIClient

User = get_user_model()


class GroupViewSetTest(TestCase):
    def setUp(self):
        """Создаём тестового пользователя и группу"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            password="adminpassword",
            is_staff=True
        )

        self.user.user_permissions.add(
            Permission.objects.get(codename="view_group"),
            Permission.objects.get(codename="add_group"),
            Permission.objects.get(codename="change_group"),
            Permission.objects.get(codename="delete_group")
        )

        self.group = Group.objects.create(name="Test Group")

    def test_list_groups_unauthorized(self):
        """Проверка, что без авторизации список групп недоступен"""
        response = self.client.get("/api/groups/")
        self.assertEqual(response.status_code, 403)

    def test_list_groups_authorized(self):
        """Проверка, что пользователь с правами может получить список групп"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/groups/")
        self.assertEqual(response.status_code, 200)

    def test_create_group_unauthorized(self):
        """Попытка создать группу без авторизации"""
        data = {"name": "New Group"}
        response = self.client.post("/api/groups/", data)
        self.assertEqual(response.status_code, 403)

    def test_create_group_authorized(self):
        """Проверка создания новой группы через API"""
        self.client.force_authenticate(user=self.user)

        data = {"name": "New Group"}
        response = self.client.post("/api/groups/", data, format="json")

        print(response.content)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Group.objects.count(), 2)

    def test_delete_group_unauthorized(self):
        """Попытка удалить группу без авторизации"""
        response = self.client.delete(f"/api/groups/{self.group.id}/")
        self.assertEqual(response.status_code, 403)

    def test_delete_group_authorized(self):
        """Проверка удаления группы через API"""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f"/api/groups/{self.group.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Group.objects.filter(id=self.group.id).exists())
