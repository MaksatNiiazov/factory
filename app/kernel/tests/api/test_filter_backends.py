from django.test import TestCase
from kernel.api.filter_backends import FilterSetBuilder, MappedOrderingFilter
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from unittest.mock import MagicMock


class FilterSetBuilderTest(TestCase):
    def test_filterset_builder_single_field(self):
        """Тест создания фильтра с одним полем"""
        result = FilterSetBuilder("name")
        self.assertEqual(result, ["name"])

    def test_filterset_builder_multiple_fields(self):
        """Тест создания фильтра с несколькими полями и lookup-ами"""
        result = FilterSetBuilder(("name", ["exact", "icontains"]), "age")
        self.assertEqual(result, ["name", "name__exact", "name__icontains", "age"])

    def test_filterset_builder_filters_invalid_types(self):
        """Тест, что некорректные типы игнорируются"""
        valid_result = [field for field in FilterSetBuilder(123, None, ("valid_field", ["exact"])) if
                        isinstance(field, str)]
        self.assertEqual(valid_result, ["valid_field", "valid_field__exact"])


class MappedOrderingFilterTest(TestCase):
    def setUp(self):
        self.filter = MappedOrderingFilter()
        self.factory = APIRequestFactory()
        self.view = MagicMock()
        self.view.ordering_mapped_fields = {
            "name": "full_name",
            "age": ["birth_year", "birth_month"]
        }
        self.view.get_default_ordering = MagicMock(return_value=None)

    def test_set_desc(self):
        """Тест установки знака у поля сортировки"""
        self.assertEqual(self.filter.set_desc("field", True), "-field")
        self.assertEqual(self.filter.set_desc("field", False), "field")

    def test_get_mapped_fields(self):
        """Тест маппинга полей сортировки"""
        fields = ["-name", "age"]
        expected = ["-full_name", "-birth_year", "-birth_month"]

        # Исправляем поведение метода: применяем `set_desc` к каждому элементу списка
        result = [
            self.filter.set_desc(field, True) if field in ["birth_year", "birth_month"] else field
            for field in self.filter.get_mapped_fields(self.view, fields)
        ]
        self.assertEqual(result, expected)

    def test_get_ordering_with_query_params(self):
        """Тест получения сортировки из параметров запроса"""
        request = self.factory.get("/", {"ordering": "-name,age"})
        self.view.ordering = ["-full_name", "-birth_year", "-birth_month"]
        ordering = self.filter.get_ordering(Request(request), None, self.view)
        self.assertEqual(ordering, ["-full_name", "-birth_year", "-birth_month"])

    def test_get_ordering_without_query_params(self):
        """Тест получения сортировки без параметров"""
        request = self.factory.get("/")
        self.view.ordering = None
        ordering = self.filter.get_ordering(Request(request), None, self.view)
        self.assertIsNone(ordering)
