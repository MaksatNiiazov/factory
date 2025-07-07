from django.test import TestCase
from ops.models import FieldSet


class FieldSetModelTest(TestCase):
    def setUp(self):
        self.fieldset = FieldSet.objects.create(
            name="Test Group",
            label="Test Label",
            icon="test-icon.png"
        )

    def test_str_returns_label(self):
        """Проверяет, что метод __str__ возвращает значение поля label."""
        self.assertEqual(str(self.fieldset), "Test Label")

    def test_str_returns_none_string_when_label_is_none(self):
        """Если label не задан, __str__ должен вернуть строку 'None'."""
        fs = FieldSet.objects.create(name="Another Group", label=None, icon="another-icon.png")
        self.assertEqual(str(fs), "None")

    def test_fieldset_creation_increases_count(self):
        """Проверяет, что при создании нового объекта количество записей увеличивается."""
        count_before = FieldSet.objects.count()
        FieldSet.objects.create(name="Group 3", label="Label 3")
        count_after = FieldSet.objects.count()
        self.assertEqual(count_after, count_before + 1)
