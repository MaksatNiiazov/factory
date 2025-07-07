from datetime import datetime, date
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from catalog.models import NominalDiameter
from ops.models import Attribute, FieldSet, DetailType


class AttributeModelTest(TestCase):
    def setUp(self):
        self.field_name = "test_field"
        self.detail_type = DetailType.objects.create(
            name="TestDetailType", designation="TDT", category="test"
        )
        self.fieldset = FieldSet.objects.create(
            name="fs", label="Field Set", icon="icon"
        )

    def _create_attribute(self, attr_type, **kwargs):
        """
        Вспомогательная функция для создания объекта Attribute.
        По умолчанию тип (self.type) и имя (self.name) задаются.
        Дополнительные параметры можно передать через kwargs.
        """
        data = {
            "type": attr_type,
            "name": self.field_name,
            "label": "Test Label",
            "is_required": False,
            "default": "",
            "choices": None,
            "fieldset": self.fieldset,
            "position": 1,
            "detail_type": self.detail_type,  # Обязательное поле теперь
        }
        data.update(kwargs)
        return Attribute(**data)

    def test_convert_integer_valid(self):
        """Проверка корректного преобразования для типа integer."""
        attr = self._create_attribute("integer")
        self.assertEqual(attr.convert("123"), 123)

    def test_convert_integer_invalid(self):
        """Проверка, что неверное значение для integer приводит к ошибке."""
        attr = self._create_attribute("integer")
        with self.assertRaises(ValidationError):
            attr.convert("abc", field_name="test_integer")

    def test_convert_number_valid(self):
        """Проверка корректного преобразования для типа number (float)."""
        attr = self._create_attribute("number")
        self.assertEqual(attr.convert("3.14"), 3.14)

    def test_convert_number_invalid(self):
        """Проверка, что неверное значение для number вызывает ошибку."""
        attr = self._create_attribute("number")
        with self.assertRaises(ValidationError):
            attr.convert("not_a_float", field_name="test_number")

    def test_convert_boolean_valid(self):
        """Проверка преобразования для типа boolean."""
        attr = self._create_attribute("boolean")
        self.assertTrue(attr.convert("true"))
        self.assertFalse(attr.convert("false"))

    def test_convert_boolean_invalid(self):
        """Проверка, что неверное значение для boolean вызывает ошибку."""
        attr = self._create_attribute("boolean")
        with self.assertRaises(ValidationError):
            attr.convert("yes", field_name="test_boolean")

    def test_convert_datetime_valid(self):
        """Проверка преобразования для типа datetime."""
        attr = self._create_attribute("datetime")
        now = timezone.now()
        iso_str = now.isoformat()
        result = attr.convert(iso_str)
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.replace(microsecond=0), now.replace(microsecond=0))

    def test_convert_date_valid(self):
        """Проверка преобразования для типа date."""
        attr = self._create_attribute("date")
        today = date.today()
        iso_str = today.isoformat()
        result = attr.convert(iso_str)
        self.assertIsInstance(result, date)
        self.assertEqual(result, today)

    def test_convert_string(self):
        """Для типа string значение возвращается без преобразования."""
        attr = self._create_attribute("string")
        value = "some text"
        self.assertEqual(attr.convert(value), value)

    def test_convert_catalog_builtin_valid(self):
        """
        Проверяем преобразование для типа catalog, когда self.catalog
        соответствует одному из статических каталогов (например, NominalDiameter).
        """
        attr = self._create_attribute("catalog", catalog="NominalDiameter")
        nd = NominalDiameter.objects.create(dn=101)
        result = attr.convert(str(nd.pk))
        self.assertEqual(result, nd.pk)

    def test_clean_calculated_value(self):
        """
        Если задано calculated_value, то наличие choices должно привести к ошибке.
        """
        attr = self._create_attribute(
            "string",
            calculated_value="some_formula",
            choices="some_choices",
            default="value",
            is_required=True,
        )
        with self.assertRaises(ValidationError) as cm:
            attr.clean()
        errors = cm.exception.message_dict
        self.assertIn("choices", errors)
        self.assertIn("default", errors)
        self.assertIn("is_required", errors)

    def test_clean_catalog_required(self):
        """
        Если тип 'catalog' и значение catalog не задано – должно быть вызвано исключение.
        """
        attr = self._create_attribute("catalog", catalog="")
        with self.assertRaises(ValidationError) as cm:
            attr.clean()
        self.assertIn("catalog", cm.exception.message_dict)

    def test_clean_default_conversion(self):
        """
        Если задано значение по умолчанию, то вызов clean должен успешно пройти, если значение корректно.
        """
        attr = self._create_attribute("integer", default="42")
        try:
            attr.clean()
        except ValidationError:
            self.fail("clean() вызвал ValidationError для корректного default значения")
        self.assertEqual(attr.convert(attr.default), 42)

    def test_str_returns_label(self):
        """Проверяем, что метод __str__ возвращает значение label."""
        attr = self._create_attribute("string", label="Attribute Label")
        self.assertEqual(str(attr), "Attribute Label")
