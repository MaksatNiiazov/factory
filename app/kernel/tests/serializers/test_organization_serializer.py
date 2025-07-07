from django.test import TestCase
from kernel.models import Organization
from kernel.api.serializers import OrganizationSerializer


class OrganizationSerializerTest(TestCase):
    def setUp(self):
        self.organization_data = {
            "name": "Тестовая организация",
            "external_id": 12345,
            "inn": "1234567890",
            "kpp": "0987654321",
            "payment_bank": "ТестБанк",
            "payment_account": "40817810099910000000",
            "bik": "044525225",
            "correspondent_account": "30101810400000000225"
        }
        self.organization = Organization.objects.create(**self.organization_data)

    def test_organization_serialization(self):
        """Проверка корректной сериализации модели Organization"""
        serializer = OrganizationSerializer(instance=self.organization)
        data = serializer.data

        self.assertEqual(data["name"], self.organization_data["name"])
        self.assertEqual(data["external_id"], self.organization_data["external_id"])
        self.assertEqual(data["inn"], self.organization_data["inn"])
        self.assertEqual(data["kpp"], self.organization_data["kpp"])
        self.assertEqual(data["payment_bank"], self.organization_data["payment_bank"])
        self.assertEqual(data["payment_account"], self.organization_data["payment_account"])
        self.assertEqual(data["bik"], self.organization_data["bik"])
        self.assertEqual(data["correspondent_account"], self.organization_data["correspondent_account"])
