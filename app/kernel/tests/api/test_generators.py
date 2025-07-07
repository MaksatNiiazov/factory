from django.test import TestCase
from unittest.mock import MagicMock, patch
from drf_yasg import openapi
from kernel.api.generators import SchemaGenerator

class SchemaGeneratorTest(TestCase):
    def setUp(self):
        """Создаем экземпляр SchemaGenerator с `info`"""
        self.generator = SchemaGenerator(
            info=openapi.Info(title="Test API", default_version="v1")
        )

    @patch("kernel.api.generators.OpenAPISchemaGenerator.get_path_parameters")
    def test_get_path_parameters_with_id(self, mock_super_get_path_parameters):
        """Тест: изменение типа `id` на `string`"""
        mock_super_get_path_parameters.return_value = [{"name": "id", "type": "integer"}]

        path = "/api/users/{id}/"
        view = MagicMock()

        updated_params = self.generator.get_path_parameters(path, view)

        self.assertEqual(updated_params[0]["type"], "string")  # `id` должен стать строкой

    @patch("kernel.api.generators.OpenAPISchemaGenerator.get_path_parameters")
    def test_get_path_parameters_without_id(self, mock_super_get_path_parameters):
        """Тест: параметр `id` отсутствует, ничего не меняем"""
        mock_super_get_path_parameters.return_value = [{"name": "order_id", "type": "integer"}]

        path = "/api/orders/{order_id}/"
        view = MagicMock()

        updated_params = self.generator.get_path_parameters(path, view)

        self.assertEqual(updated_params[0]["type"], "integer")  # `order_id` не должен изменяться

    @patch("kernel.api.generators.OpenAPISchemaGenerator.get_path_parameters")
    def test_get_path_parameters_with_id_already_string(self, mock_super_get_path_parameters):
        """Тест: если `id` уже строка, изменений нет"""
        mock_super_get_path_parameters.return_value = [{"name": "id", "type": "string"}]

        path = "/api/users/{id}/"
        view = MagicMock()

        updated_params = self.generator.get_path_parameters(path, view)

        self.assertEqual(updated_params[0]["type"], "string")  # Должно остаться без изменений
