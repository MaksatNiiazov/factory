from django.test import TestCase, override_settings
from django.http import JsonResponse
import json


class FrontLanguageJsonTest(TestCase):
    def setUp(self):
        self.valid_lang = "ru"
        self.invalid_lang = "fr"

    def test_valid_language_code(self):
        """Тест запроса с корректным языковым кодом"""
        response = self.client.get(f"/kernel/languages/{self.valid_lang}.json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("title", response.json())

    def test_invalid_language_code(self):
        """Тест запроса с некорректным языковым кодом"""
        response = self.client.get(f"/kernel/languages/{self.invalid_lang}.json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        self.assertEqual(response.json()["error"], "Lang code not found")

    @override_settings(LANGUAGES=[("en", "English"), ("ru", "Russian")])
    def test_language_codes_extraction(self):
        """Проверяем, что список языковых кодов корректно извлекается из settings.LANGUAGES"""
        response = self.client.get(f"/kernel/languages/{self.valid_lang}.json")
        self.assertEqual(response.status_code, 200)

    @override_settings(LANGUAGES=[])
    def test_empty_language_settings(self):
        """Проверяем поведение при пустом списке LANGUAGES"""
        response = self.client.get(f"/kernel/languages/{self.valid_lang}.json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Lang code not found")
