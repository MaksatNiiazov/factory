from django.test import TestCase
from rest_framework.exceptions import NotFound
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
from kernel.api.pagination import DynamicPageNumberPagination


class DynamicPageNumberPaginationTestCase(TestCase):
    def setUp(self):
        self.pagination = DynamicPageNumberPagination()
        self.factory = APIRequestFactory()
        self.queryset = list(range(1, 101))  # Данные для тестирования

    def test_standard_pagination(self):
        request = self.factory.get("/", {"size": "10", "page": "1"})
        request = Request(request)  # Оборачиваем в DRF Request
        paginated_queryset = self.pagination.paginate_queryset(self.queryset, request)
        self.assertEqual(len(paginated_queryset), 10)

    def test_disable_pagination_with_size_minus_one(self):
        request = self.factory.get("/", {"size": "-1"})
        request = Request(request)
        paginated_queryset = self.pagination.paginate_queryset(self.queryset, request)
        self.assertEqual(paginated_queryset, self.queryset)

    def test_invalid_page_raises_not_found(self):
        request = self.factory.get("/", {"size": "10", "page": "999"})
        request = Request(request)
        with self.assertRaises(NotFound):
            self.pagination.paginate_queryset(self.queryset, request)

    def test_paginated_response_format(self):
        request = self.factory.get("/", {"size": "10", "page": "1"})
        request = Request(request)
        paginated_queryset = self.pagination.paginate_queryset(self.queryset, request)
        response = self.pagination.get_paginated_response(paginated_queryset)
        self.assertIn("count", response.data)
        self.assertIn("size", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)

    def test_get_page_size_fallback(self):
        request = self.factory.get("/")
        request = Request(request)
        page_size = self.pagination.get_page_size(request)
        self.assertEqual(page_size, self.pagination.page_size)  # Проверка дефолтного размера
