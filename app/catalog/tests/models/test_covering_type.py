from django.test import TestCase
from catalog.models import CoveringType


class CoveringTypeModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.covering_type = CoveringType.objects.create(
            name='Тип 1',
            description='Описание типа 1',
            numeric=1
        )

    def test_covering_type_creation(self):
        """Тест создания объекта CoveringType"""
        self.assertEqual(self.covering_type.name, 'Тип 1')
        self.assertEqual(self.covering_type.description, 'Описание типа 1')
        self.assertEqual(self.covering_type.numeric, 1)

    def test_str_representation(self):
        """Тест строкового представления модели"""
        self.assertEqual(str(self.covering_type), 'Тип 1')

    def test_display_name_property(self):
        """Тест свойства display_name"""
        self.assertEqual(self.covering_type.display_name, 'Тип 1')

    def test_covering_type_without_description(self):
        """Тест создания CoveringType без описания"""
        covering_type = CoveringType.objects.create(name='Без описания', numeric=2)
        self.assertEqual(covering_type.description, None)
        self.assertEqual(str(covering_type), 'Без описания')
