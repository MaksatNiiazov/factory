from django.test import TestCase
from ops.models import DetailType
from kernel.api.serializers import ItemTableSerializer

class ItemTableSerializerTest(TestCase):
    def setUp(self):
        """Создаём тестовый объект DetailType перед каждым тестом"""
        self.detail_type = DetailType.objects.create(name="Тестовый тип детали")

    def test_item_table_serialization(self):
        """Проверка сериализации ItemTableSerializer"""
        data = {
            "detail_type": self.detail_type.id,
            "attributes": ["цвет", "размер"]
        }
        serializer = ItemTableSerializer(data=data)

        if not serializer.is_valid():
            print(serializer.errors)

        self.assertTrue(serializer.is_valid(), msg=serializer.errors)
        self.assertEqual(serializer.validated_data["detail_type"], self.detail_type)
        self.assertEqual(serializer.validated_data["attributes"], ["цвет", "размер"])

    def test_item_table_invalid_data(self):
        """Проверка валидации с некорректными данными"""
        data = {
            "detail_type": None,
            "attributes": "не список"
        }
        serializer = ItemTableSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("detail_type", serializer.errors)
        self.assertIn("attributes", serializer.errors)
