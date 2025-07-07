from django.test import TestCase
from catalog.models import LoadGroup


class LoadGroupModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.load_group = LoadGroup.objects.create(lgv=12, kn=7)

    def test_load_group_creation(self):
        """Тест создания LoadGroup"""
        self.assertEqual(self.load_group.lgv, 12)
        self.assertEqual(self.load_group.kn, 7)

    def test_load_group_str_method(self):
        """Тест строкового представления модели LoadGroup"""
        self.assertEqual(str(self.load_group), "LGV=12 kN=7")

    def test_load_group_display_name(self):
        """Тест свойства display_name (если есть)"""
        if hasattr(self.load_group, "display_name"):
            self.assertEqual(self.load_group.display_name, str(self.load_group))

    def test_multiple_load_group_instances(self):
        """Тест создания нескольких объектов LoadGroup"""
        group1 = LoadGroup.objects.create(lgv=15, kn=10)
        group2 = LoadGroup.objects.create(lgv=20, kn=5)

        self.assertNotEqual(group1.lgv, group2.lgv)
        self.assertNotEqual(group1.kn, group2.kn)
        self.assertEqual(str(group1), "LGV=15 kN=10")
        self.assertEqual(str(group2), "LGV=20 kN=5")
