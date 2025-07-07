from django.test import TestCase
from django.db.utils import IntegrityError
from catalog.models import NominalDiameter


class NominalDiameterModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.nominal_diameter, _ = NominalDiameter.objects.get_or_create(dn=100)

    def test_nominal_diameter_creation(self):
        """Тест создания объекта NominalDiameter"""
        self.assertEqual(self.nominal_diameter.dn, 100)

    def test_nominal_diameter_str_method(self):
        """Тест строкового представления модели NominalDiameter"""
        self.assertEqual(str(self.nominal_diameter), "DN100")

    def test_nominal_diameter_display_name(self):
        """Тест свойства display_name (если оно есть)"""
        if hasattr(self.nominal_diameter, "display_name"):
            self.assertEqual(self.nominal_diameter.display_name, str(self.nominal_diameter))

    def test_nominal_diameter_unique_constraint(self):
        """Тест уникальности dn"""
        with self.assertRaises(IntegrityError):
            NominalDiameter.objects.create(dn=100)

    def test_nominal_diameter_ordering(self):
        """Тест сортировки NominalDiameter по полю dn"""
        NominalDiameter.objects.create(dn=51)
        NominalDiameter.objects.create(dn=151)

        diameters = NominalDiameter.objects.all()
        dn_values = list(diameters.values_list("dn", flat=True))

        self.assertEqual(dn_values, sorted(dn_values))
