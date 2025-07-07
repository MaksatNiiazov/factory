from django.test import TestCase
from catalog.models import Material
from catalog.api.serializers import MaterialSerializer

class MaterialSerializerTest(TestCase):
    def test_material_serializer_fields(self):
        # Создаем тестовый объект материала
        material = Material.objects.create(name='Material 1', group='Group 1')
        serializer = MaterialSerializer(material)
        # Проверяем, что обязательные поля присутствуют в сериализованных данных
        self.assertIn('name_ru', serializer.data)
        # Предполагается, что для поля name_ru используется значение из поля name
        self.assertEqual(serializer.data['name_ru'], 'Material 1')
        # Можно добавить проверки и для других полей, если они сериализуются
        self.assertEqual(serializer.data.get('group', None), 'Group 1')

    def test_material_serializer_with_missing_optional_fields(self):
        # Если у модели есть опциональные поля, проверяем их значение по умолчанию
        material = Material.objects.create(name='Material 2', group='Group 2')
        serializer = MaterialSerializer(material)
        # Например, если отсутствует дополнительное поле, то его значение может быть None или пустой строкой
        self.assertEqual(serializer.data.get('description', ''), '')
