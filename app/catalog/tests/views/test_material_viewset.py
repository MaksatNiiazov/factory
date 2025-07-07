from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from catalog.models import Material
from kernel.models import User


class MaterialViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.material = Material.objects.create(
            name='Material 1',
            group='Group 1'
        )
        cls.user = User.objects.create_superuser(
            email='testuser@example.com',
            password='testpass'
        )

    def setUp(self):
        response = self.client.post(
            reverse('user-login'),
            {'username': 'testuser@example.com', 'password': 'testpass'},
            format='json'
        )
        self.token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_list_materials(self):
        """
        Тест получения списка (GET) без авторизации.
        """
        self.client.logout()
        url = reverse('material-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_material(self):
        """
        Тест получения конкретного объекта (GET) без авторизации.
        """
        self.client.logout()
        url = reverse('material-detail', args=[self.material.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('name_ru', response.data)
        self.assertEqual(response.data['name_ru'], 'Material 1')

    def test_create_material(self):
        """
        Тест создания нового объекта (POST) с корректными данными.
        """
        url = reverse('material-list')
        data = {
            'name_ru': 'New Material',
            'group': 'New Group'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Material.objects.filter(name_ru='New Material', group='New Group').exists()
        )

    def test_create_material_with_invalid_data(self):
        """
        Тест создания нового объекта (POST) с некорректными данными,
        ожидается 400 Bad Request.
        """
        url = reverse('material-list')
        data = {
            'type': 'ABC',
            'group': 'Group 1'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_access_control(self):
        """
        Тест создания (POST) при отсутствии авторизации,
        ожидается 403 Forbidden.
        """
        self.client.logout()
        url = reverse('material-list')
        data = {'name': 'New Material', 'group': 'New Group'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_material(self):
        """
        Тест частичного обновления (PATCH).
        """
        url = reverse('material-detail', args=[self.material.id])
        data = {"type": "A"}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.material.refresh_from_db()
        self.assertEqual(self.material.type, 'A')

    def test_delete_material(self):
        """
        Тест удаления (DELETE).
        """
        url = reverse('material-detail', args=[self.material.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Material.objects.filter(id=self.material.id).exists())

    def test_retrieve_material_not_found(self):
        """
        Тест 404 (GET) при запросе несуществующего объекта.
        """
        url = reverse('material-detail', args=[999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
