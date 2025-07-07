from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient
from kernel.models import Organization

User = get_user_model()


class OrganizationViewSetTest(TestCase):
    def setUp(self):
        """Создаём тестового пользователя и организацию"""
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            password="adminpassword",
            is_staff=True
        )

        self.user.user_permissions.add(
            Permission.objects.get(codename="view_organization"),
            Permission.objects.get(codename="add_organization"),
            Permission.objects.get(codename="change_organization"),
            Permission.objects.get(codename="delete_organization")
        )

        self.organization = Organization.objects.create(
            name="Test Organization",
            external_id=12345,
            inn="1234567890",
            kpp="0987654321",
            payment_bank="ТестБанк",
            payment_account="40817810099910000000",
            bik="044525225",
            correspondent_account="30101810400000000225"
        )

    def test_list_organizations_unauthorized(self):
        """Проверка, что без авторизации список организаций недоступен"""
        response = self.client.get("/api/organizations/")
        self.assertEqual(response.status_code, 403)

    def test_list_organizations_authorized(self):
        """Проверка, что пользователь с правами может получить список организаций"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/organizations/")
        self.assertEqual(response.status_code, 200)

    def test_create_organization_unauthorized(self):
        """Попытка создать организацию без авторизации"""
        data = {
            "name": "New Organization",
            "external_id": 54321,
            "inn": "9876543210",
            "kpp": "5678901234",
            "payment_bank": "ДругойБанк",
            "payment_account": "40817810099920000000",
            "bik": "044525226",
            "correspondent_account": "30101810400000000226"
        }
        response = self.client.post("/api/organizations/", data)
        self.assertEqual(response.status_code, 403)

    def test_create_organization_authorized(self):
        """Проверка создания новой организации через API"""
        self.client.force_authenticate(user=self.user)

        data = {
            "name": "New Organization",
            "external_id": 54321,
            "inn": "9876543210",
            "kpp": "5678901234",
            "payment_bank": "ДругойБанк",
            "payment_account": "40817810099920000000",
            "bik": "044525226",
            "correspondent_account": "30101810400000000226"
        }

        response = self.client.post("/api/organizations/", data, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Organization.objects.count(), 2)

    def test_delete_organization_unauthorized(self):
        """Попытка удалить организацию без авторизации"""
        response = self.client.delete(f"/api/organizations/{self.organization.id}/")
        self.assertEqual(response.status_code, 403)

    def test_delete_organization_authorized(self):
        """Проверка удаления организации через API"""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(f"/api/organizations/{self.organization.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Organization.objects.filter(id=self.organization.id).exists())
