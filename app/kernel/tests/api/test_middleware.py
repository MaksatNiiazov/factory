from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from kernel.api.middleware import ConvertFiltersToQueryParamsMiddleware


class ConvertFiltersToQueryParamsMiddlewareTestCase(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = ConvertFiltersToQueryParamsMiddleware(get_response=lambda request: JsonResponse({"message": "OK"}))

    def test_middleware_without_filters(self):
        """Проверяет, что middleware не изменяет запрос, если параметр 'filters' отсутствует."""
        request = self.factory.get("/api/test/")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.GET.get("filters"), None)

    def test_middleware_with_valid_filters(self):
        """Проверяет, что middleware корректно преобразует фильтры из query-параметров."""
        request = self.factory.get("/api/test/?filters=field1=value1&field2=value2")
        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.GET.getlist("field1"), ["value1"])
        self.assertEqual(request.GET.getlist("field2"), ["value2"])

    def test_middleware_with_multiple_values(self):
        """Проверяет, что middleware корректно обрабатывает несколько значений для одного поля."""
        request = self.factory.get("/api/test/?filters=field1=value1&field1=value2")
        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(request.GET.getlist("field1")), sorted(["value1", "value2"]))

    def test_middleware_with_empty_filters(self):
        """Проверяет, что middleware не вызывает ошибки, если параметр 'filters' пустой."""
        request = self.factory.get("/api/test/?filters=")
        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(request.GET), 1)  # filters пустой, но существует

    def test_middleware_preserves_existing_params(self):
        """Проверяет, что middleware сохраняет уже существующие параметры в запросе."""
        request = self.factory.get("/api/test/?filters=field1=value1&field2=value2&existing_param=keep")
        response = self.middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.GET.getlist("field1"), ["value1"])
        self.assertEqual(request.GET.getlist("field2"), ["value2"])
        self.assertEqual(request.GET.get("existing_param"), "keep")

