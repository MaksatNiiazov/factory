from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from catalog.models import LoadGroup
from kernel.models import User


class LoadGroupViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.load_group = LoadGroup.objects.create(lgv=12, kn=7)
        cls.user = User.objects.create_superuser(email='testuser@example.com', password='testpass')

    def setUp(self):
        response = self.client.post(
            reverse('user-login'),
            {'username': 'testuser@example.com', 'password': 'testpass'},
            format='json'
        )
        self.token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_list_load_groups(self):
        """
        Тест получения списка (GET).
        """
        url = reverse('loadgroup-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_load_group(self):
        """
        Тест получения конкретной записи (GET).
        """
        url = reverse('loadgroup-detail', args=[self.load_group.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['lgv'], 12)

    def test_create_load_group(self):
        """
        Тест создания новой записи (POST).
        """
        url = reverse('loadgroup-list')
        data = {'lgv': 20, 'kn': 5}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            LoadGroup.objects.filter(lgv=20, kn=5).exists()
        )

    def test_update_load_group(self):
        """
        Тест частичного обновления (PATCH).
        """
        url = reverse('loadgroup-detail', args=[self.load_group.id])
        data = {'kn': 10}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.load_group.refresh_from_db()
        self.assertEqual(self.load_group.kn, 10)

    def test_delete_load_group(self):
        """
        Тест удаления записи (DELETE).
        """
        url = reverse('loadgroup-detail', args=[self.load_group.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(LoadGroup.objects.filter(id=self.load_group.id).exists())

    def test_retrieve_load_group_not_found(self):
        """
        Тест 404 (GET) при запросе несуществующей записи.
        """
        url = reverse('loadgroup-detail', args=[999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
