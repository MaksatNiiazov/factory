from django.test import TestCase
from django.contrib.auth.models import ContentType, Permission
from kernel.api.serializers import PermissionSerializer


class PermissionSerializerTest(TestCase):
    def setUp(self):
        """Создаём тестовое разрешение перед каждым тестом"""
        content_type = ContentType.objects.get_for_model(Permission)
        self.permission = Permission.objects.create(
            codename="test_permission",
            name="Тестовое разрешение",
            content_type=content_type,
        )

    def test_permission_serialization(self):
        """Проверка сериализации разрешения"""
        serializer = PermissionSerializer(instance=self.permission)
        data = serializer.data

        self.assertEqual(data["id"], self.permission.id)
        self.assertEqual(data["name"], self.permission.name)
        self.assertEqual(data["codename"], self.permission.codename)

    def test_permission_deserialization(self):
        """Проверка десериализации разрешения"""
        valid_data = {
            "id": self.permission.id,
            "name": "Обновленное разрешение",
            "codename": "updated_permission",
        }

        serializer = PermissionSerializer(instance=self.permission, data=valid_data, partial=True)

        if not serializer.is_valid():
            print(serializer.errors)

        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        updated_permission = serializer.save()

        self.assertEqual(updated_permission.name, "Обновленное разрешение")
        self.assertEqual(updated_permission.codename, "updated_permission")
