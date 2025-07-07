import os
import json
import django
import requests
from unittest import TestCase
from unittest.mock import patch, Mock
from requests.auth import HTTPBasicAuth
from kernel.erp import ERPApi, ERPException


class TestERPApi(TestCase):
    @classmethod
    def setUpClass(cls):
        """Настраиваем Django перед запуском тестов"""
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "your_project.settings")  # Замените на свой проект
        django.setup()

    def setUp(self):
        """Создаём экземпляр API с тестовыми данными."""
        self.api = ERPApi(base_url="http://test-api.com", login="test_user", password="test_pass")

    @patch("kernel.erp.requests.post")
    def test_post_successful(self, mock_post):
        """Тест успешного POST-запроса"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_post.return_value = mock_response

        url = "http://test-api.com/test"
        data = {"key": "value"}

        response = self.api.post(url, data)

        self.assertEqual(response.status_code, 200)
        mock_post.assert_called_once_with(
            url,
            data=json.dumps(data),
            auth=HTTPBasicAuth(username="test_user", password="test_pass"),
            headers={"Host": "test-api.com"},
            timeout=60,
        )

    def test_validate_config_success(self):
        """Тест успешной валидации конфигурации"""
        self.api.validate_config()  # Не должно выбрасывать исключений

    def test_validate_config_missing_base_url(self):
        """Тест валидации без base_url"""
        self.api.base_url = None
        with self.assertRaises(ERPException) as context:
            self.api.validate_config()
        self.assertEqual(str(context.exception), "Не указан базовый URL в настройке")

    def test_validate_config_missing_login(self):
        """Тест валидации без логина"""
        self.api.login = None
        with self.assertRaises(ERPException) as context:
            self.api.validate_config()
        self.assertEqual(str(context.exception), "Не указан логин к системе ERP")

    def test_validate_config_missing_password(self):
        """Тест валидации без пароля"""
        self.api.password = None
        with self.assertRaises(ERPException) as context:
            self.api.validate_config()
        self.assertEqual(str(context.exception), "Не указан пароль к системе ERP")

    @patch("kernel.erp.requests.post")
    def test_sync_product_successful(self, mock_post):
        """Тест успешной синхронизации продукта"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"error": False}, "id": 12345}
        mock_post.return_value = mock_response

        mock_erp_sync = Mock()
        response = self.api.sync_product(
            idwicad=1,
            modelslug="test-model",
            art="ART123",
            name="Test Product",
            params={},
            erp_sync=mock_erp_sync,
        )

        self.assertEqual(response, 12345)
        mock_erp_sync.add_log.assert_called()

    @patch("kernel.erp.requests.post")
    def test_sync_product_error(self, mock_post):
        """Тест ошибки при синхронизации продукта"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": {"error": True, "text": "Ошибка на сервере"}}
        mock_post.return_value = mock_response

        mock_erp_sync = Mock()

        with self.assertRaises(ERPException) as context:
            self.api.sync_product(
                idwicad=1,
                modelslug="test-model",
                art="ART123",
                name="Test Product",
                params={},
                erp_sync=mock_erp_sync,
            )

        self.assertEqual(str(context.exception), "Ошибка на сервере")

    @patch("kernel.erp.requests.post")
    def test_sync_specifications_successful(self, mock_post):
        """Тест успешной синхронизации спецификаций"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": False, "message": "Success"}
        mock_post.return_value = mock_response

        mock_erp_sync = Mock()
        response = self.api.sync_specifications(
            idwicad=1,
            iderp=2,
            count=10,
            structure={},
            erp_sync=mock_erp_sync,
        )

        self.assertEqual(response, {"error": False, "message": "Success"})
        mock_erp_sync.add_log.assert_called()

    @patch("kernel.erp.requests.post")
    def test_sync_specifications_error(self, mock_post):
        """Тест ошибки при синхронизации спецификаций"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": True, "text": "Ошибка спецификации"}
        mock_post.return_value = mock_response

        mock_erp_sync = Mock()

        with self.assertRaises(ERPException) as context:
            self.api.sync_specifications(
                idwicad=1,
                iderp=2,
                count=10,
                structure={},
                erp_sync=mock_erp_sync,
            )

        self.assertEqual(str(context.exception), "Ошибка спецификации")
    #
    # @patch("kernel.erp.requests.post")
    # def test_post_failure(self, mock_post):
    #     """Тест на выброс ERPException при ошибке запроса"""
    #     mock_response = Mock()
    #     mock_response.status_code = 500  # Ошибка сервера
    #     mock_response.content.decode.return_value = "Internal Server Error"
    #     mock_post.return_value = mock_response  # Настраиваем mock
    #
    #     with self.assertRaises(ERPException) as context:
    #         self.api.post("http://test-api.com/error", {"key": "value"})
    #
    #     self.assertIn("Ошибка запроса: 500", str(context.exception))
    #     self.assertIn("Internal Server Error", str(context.exception))