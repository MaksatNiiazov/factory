from django.test import TestCase
from catalog.models import Material
from django.core.exceptions import ValidationError


class MaterialModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.material = Material.objects.create(name='09Г2С', group='Сталь')

    def test_material_creation(self):
        """Тест создания объекта Material"""
        self.assertEqual(self.material.name, '09Г2С')
        self.assertEqual(self.material.group, 'Сталь')

    def test_material_str_method(self):
        """Тест строкового представления модели Material"""
        self.assertEqual(str(self.material), '09Г2С')

    def test_material_display_name(self):
        """Тест свойства display_name (если есть)"""
        if hasattr(self.material, "display_name"):
            self.assertEqual(self.material.display_name, str(self.material))

    def test_multiple_material_instances(self):
        """Тест создания нескольких объектов Material"""
        material1 = Material.objects.create(name='AISI 304', group='Нержавеющая сталь')
        material2 = Material.objects.create(name='Титан ВТ6', group='Титановые сплавы')

        self.assertNotEqual(material1.name, material2.name)
        self.assertNotEqual(material1.group, material2.group)
        self.assertEqual(str(material1), "AISI 304")
        self.assertEqual(str(material2), "Титан ВТ6")

    def test_material_clean_validation(self):
        """Тест на валидацию температурных значений через clean()"""
        material = Material(name="Тест", group="Тестовая группа", min_temp=100, max_temp=50)

        with self.assertRaises(ValidationError) as context:
            material.clean()

        self.assertIn("max_temp", context.exception.message_dict)
