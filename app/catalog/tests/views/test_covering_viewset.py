from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from catalog.models import Covering
from kernel.models import User


class CoveringViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.covering = Covering.objects.create(name='Covering 1')
        cls.user = User.objects.create_superuser(email='testuser@example.com', password='testpass')

    def setUp(self):
        response = self.client.post(
            reverse('user-login'),
            {'username': 'testuser@example.com', 'password': 'testpass'},
            format='json'
        )
        self.token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_list_coverings(self):
        url = reverse('covering-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_covering(self):
        url = reverse('covering-detail', args=[self.covering.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name_ru'], 'Covering 1')

    def test_update_covering(self):
        """Проверяем частичное обновление (PATCH)"""
        url = reverse('covering-detail', args=[self.covering.id])
        data = {'name_ru': 'Updated Covering'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.covering.refresh_from_db()
        self.assertEqual(self.covering.name, 'Updated Covering')

    def test_create_covering(self):
        """Создание нового Covering (POST)"""
        url = reverse('covering-list')
        data = {'name_ru': 'New Covering'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Проверим, что объект реально создался в БД
        self.assertTrue(Covering.objects.filter(name='New Covering').exists())

    def test_delete_covering(self):
        """Удаление Covering (DELETE)"""
        url = reverse('covering-detail', args=[self.covering.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Covering.objects.filter(id=self.covering.id).exists())

    def test_retrieve_not_found(self):
        """Проверяем, что при запросе несуществующего ID будет 404"""
        url = reverse('covering-detail', args=[999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
