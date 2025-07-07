from django.db import transaction
from django.test import TestCase
from django.db.utils import IntegrityError
from catalog.models import PipeDiameter, NominalDiameter


class PipeDiameterModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.nominal_diameter, _ = NominalDiameter.objects.get_or_create(dn=100)
        cls.pipe_diameter = PipeDiameter.objects.create(
            dn=cls.nominal_diameter,
            standard=1,
            size=100.0,
        )

    def test_pipe_diameter_creation(self):
        """Тест создания объекта PipeDiameter"""
        self.assertEqual(self.pipe_diameter.dn.dn, 100)
        self.assertEqual(self.pipe_diameter.standard, 1)
        self.assertEqual(self.pipe_diameter.size, 100.0)

    def test_pipe_diameter_str_method(self):
        """Тест строкового представления модели PipeDiameter"""
        expected_str = f"DN100"  # Если `option` нет, просто DN100
        if self.pipe_diameter.option:
            expected_str = f"DN100({self.pipe_diameter.get_option_display()})"
        self.assertEqual(str(self.pipe_diameter), expected_str)

    def test_pipe_diameter_display_name(self):
        """Тест свойства display_name (если оно есть)"""
        if hasattr(self.pipe_diameter, "display_name"):
            self.assertEqual(self.pipe_diameter.display_name, str(self.pipe_diameter))

    def test_pipe_diameter_erp_display_name(self):
        """Тест свойства erp_display_name (если оно есть)"""
        if hasattr(self.pipe_diameter, "erp_display_name"):
            expected_erp_name = f"{self.pipe_diameter.dn.dn}"
            if self.pipe_diameter.option:
                expected_erp_name += self.pipe_diameter.get_option_display()
            self.assertEqual(self.pipe_diameter.erp_display_name, expected_erp_name)


    # def test_pipe_diameter_unique_constraint(self):
    #     """Проверяем, что нельзя создать дубликат `PipeDiameter`"""
    #     with self.assertRaises(IntegrityError):
    #         PipeDiameter.objects.create(
    #             dn=self.nominal_diameter,
    #             standard=2,
    #             size=100.0,
    #             option=88,  # Проверяем уникальность
    #         )
    def test_pipe_diameter_ordering(self):
        """Тест сортировки PipeDiameter по standard и dn"""
        nominal_diameter_50, _ = NominalDiameter.objects.get_or_create(dn=50)
        nominal_diameter_150, _ = NominalDiameter.objects.get_or_create(dn=150)

        PipeDiameter.objects.create(dn=nominal_diameter_50, standard=2, size=50.0)
        PipeDiameter.objects.create(dn=nominal_diameter_150, standard=1, size=150.0)

        diameters = PipeDiameter.objects.all()
        sorted_diameters = sorted(diameters, key=lambda x: (x.standard, x.dn.dn))

        self.assertEqual(list(diameters), sorted_diameters)
