from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from catalog.models import CoveringType
from kernel.models import User

class CoveringTypeViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        """Создание тестовых данных перед выполнением всех тестов."""
        cls.covering_type = CoveringType.objects.create(name_ru='Type 1', description_ru='Description 1', numeric=1)
        cls.user = User.objects.create_superuser(email='testuser@example.com', password='testpass')

    def setUp(self):
        """Логин и установка токена перед каждым тестом."""
        response = self.client.post(
            reverse('user-login'),
            {'username': 'testuser@example.com', 'password': 'testpass'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f"Login failed: {response.json()}")
        self.token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_list_covering_types(self):
        """Тест списка CoveringType."""
        url = reverse('coveringtype-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_retrieve_covering_type(self):
        """Тест получения одного CoveringType по ID."""
        url = reverse('coveringtype-detail', args=[self.covering_type.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f"Ошибка при получении CoveringType: {response.json()}")
        # print("Response data:", response.data)
        self.assertEqual(response.data.get('name_ru'), 'Type 1', msg="Имя не совпадает!")

    def test_update_covering_type(self):
        """Тест частичного обновления CoveringType."""
        url = reverse('coveringtype-detail', args=[self.covering_type.id])
        data = {'description_ru': 'Updated Description'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f"Ошибка при обновлении CoveringType: {response.json()}")
        self.covering_type.refresh_from_db()
        # print("Updated Description:", self.covering_type.description_ru)
        self.assertEqual(self.covering_type.description_ru, 'Updated Description')

    def test_delete_covering_type(self):
        """Тест удаления CoveringType."""
        url = reverse('coveringtype-detail', args=[self.covering_type.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CoveringType.objects.filter(id=self.covering_type.id).exists())

    def test_create_covering_type(self):
        """Тест создания нового CoveringType."""
        url = reverse('coveringtype-list')
        data = {'name_ru': 'Type 2', 'description_ru': 'Description 2', 'numeric': 2}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, msg=f"Ошибка при создании CoveringType: {response.json()}")
        self.assertTrue(CoveringType.objects.filter(name_ru='Type 2').exists())

    def test_create_covering_type_invalid_data(self):
        """Тест попытки создания CoveringType с некорректными данными (ожидаем 400)."""
        url = reverse('coveringtype-list')
        data = {'name_ru': '', 'description_ru': 'Invalid', 'numeric': None}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
