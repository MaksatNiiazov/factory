from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from catalog.models import NominalDiameter
from kernel.models import User


class NominalDiameterViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.nominal_diameter = NominalDiameter.objects.create(dn=99)
        cls.user = User.objects.create_superuser(email='testuser@example.com', password='testpass')

    def setUp(self):
        response = self.client.post(
            reverse('user-login'),
            {'username': 'testuser@example.com', 'password': 'testpass'},
            format='json'
        )
        self.token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_list_nominal_diameters(self):
        """
        Тест получения списка (GET).
        """
        url = reverse('nominaldiameter-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_nominal_diameter(self):
        """
        Тест получения одного объекта (GET).
        """
        url = reverse('nominaldiameter-detail', args=[self.nominal_diameter.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['dn'], 99)

    def test_create_nominal_diameter(self):
        """
        Тест создания нового объекта (POST).
        """
        url = reverse('nominaldiameter-list')
        data = {'dn': 120}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(NominalDiameter.objects.filter(dn=120).exists())

    def test_update_nominal_diameter(self):
        """
        Тест частичного обновления (PATCH).
        """
        url = reverse('nominaldiameter-detail', args=[self.nominal_diameter.id])
        data = {'dn': 98}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.nominal_diameter.refresh_from_db()
        self.assertEqual(self.nominal_diameter.dn, 98)

    def test_delete_nominal_diameter(self):
        """
        Тест удаления (DELETE).
        """
        url = reverse('nominaldiameter-detail', args=[self.nominal_diameter.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(NominalDiameter.objects.filter(id=self.nominal_diameter.id).exists())

    def test_retrieve_nominal_diameter_not_found(self):
        """
        Тест 404 (GET) при запросе несуществующего объекта.
        """
        url = reverse('nominaldiameter-detail', args=[999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
