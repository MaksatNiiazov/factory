from django.core.exceptions import ValidationError
from django.test import TestCase

from kernel.fields import AttributeChoiceFormField, AttributeChoiceField


class AttributeChoiceFormFieldTest(TestCase):
    def setUp(self):
        self.field = AttributeChoiceFormField()

    def test_prepare_value(self):
        value = [{'value': '1', 'display_name': 'One'}, {'value': '2', 'display_name': 'Two'}]
        prepared = self.field.prepare_value(value)
        self.assertEqual(prepared, "1|One\n2|Two")

    def test_to_python_valid(self):
        value = "1|One\n2|Two"
        expected = [{'value': '1', 'display_name': 'One'}, {'value': '2', 'display_name': 'Two'}]
        self.assertEqual(self.field.to_python(value), expected)

    def test_to_python_invalid(self):
        with self.assertRaises(ValidationError):
            self.field.to_python(123)  # Неверный тип


class AttributeChoiceFieldTest(TestCase):
    def setUp(self):
        self.field = AttributeChoiceField()

    def test_to_python_valid(self):
        value = [{'value': '1', 'display_name': 'One'}, {'value': '2', 'display_name': 'Two'}]
        self.assertEqual(self.field.to_python(value), value)

    def test_to_python_invalid_type(self):
        with self.assertRaises(ValidationError):
            self.field.to_python(123)  # Неверный тип

    def test_get_prep_value(self):
        value = [{'value': '1', 'display_name': 'One'}, {'value': '2', 'display_name': 'Two'}]
        prepared = self.field.get_prep_value(value)
        self.assertEqual(prepared, "1|One\n2|Two")

    def test_get_prep_value_invalid(self):
        with self.assertRaises(ValidationError):
            self.field.get_prep_value("invalid string")

    def test_from_db_value(self):
        value = "1|One\n2|Two"
        expected = [{'value': '1', 'display_name': 'One'}, {'value': '2', 'display_name': 'Two'}]
        self.assertEqual(self.field.from_db_value(value, None, None), expected)

    def test_formfield(self):
        form_field = self.field.formfield()
        self.assertIsInstance(form_field, AttributeChoiceFormField)

    def test_deconstruct(self):
        name, path, args, kwargs = self.field.deconstruct()
        self.assertEqual(path, "kernel.fields.AttributeChoiceField")
