from django.test import TestCase
from ops.forms import TmpCompositionForm
from catalog.models import Material


class TmpCompositionFormTest(TestCase):
    def setUp(self):
        """Настраиваем тестовые данные"""
        self.material = Material.objects.create(name="Steel", group="Metal")
        self.tmp_child = TmpCompositionForm().fields["tmp_child"].queryset.first()

    def test_valid_form(self):
        """Тест валидной формы"""
        form_data = {
            "tmp_child": self.tmp_child.id,
            "position": 1,
            "material": self.material.id,
            "count": 5,
        }
        form = TmpCompositionForm(data=form_data)
        print("Ошибки формы:", form.errors)
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_required_fields(self):
        """Тест формы с отсутствующими обязательными полями"""
        form = TmpCompositionForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("tmp_child", form.errors)
        self.assertIn("position", form.errors)
        self.assertIn("count", form.errors)

    def test_invalid_count(self):
        """Тест формы с отрицательным значением количества"""
        form_data = {
            "tmp_child": self.tmp_child.id,
            "position": 1,
            "material": self.material.id,
            "count": -1,
        }
        form = TmpCompositionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("count", form.errors)
