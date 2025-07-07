from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from catalog.models import PipeDiameter, NominalDiameter
from kernel.models import User


class PipeDiameterViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.normal_diameter = NominalDiameter.objects.create(dn=99)
        cls.pipe_diameter = PipeDiameter.objects.create(dn=cls.normal_diameter, standard=1, size=100.0)
        cls.user = User.objects.create_superuser(email='testuser@example.com', password='testpass')

    def setUp(self):
        response = self.client.post(
            reverse('user-login'),
            {'username': 'testuser@example.com', 'password': 'testpass'},
            format='json'
        )
        self.token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_list_pipe_diameters(self):
        url = reverse('pipediameter-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_pipe_diameter(self):
        url = reverse('pipediameter-detail', args=[self.pipe_diameter.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['size'], 100)

    def test_update_pipe_diameter(self):
        url = reverse('pipediameter-detail', args=[self.pipe_diameter.id])
        data = {'size': 150.0}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.pipe_diameter.refresh_from_db()
        self.assertEqual(self.pipe_diameter.size, 150.0)

    def test_get_dn_by_diameter(self):
        url = reverse('pipediameter-get-dn-by-diameter')
        data = {'standard': 1, 'size': 100.0}
        response = self.client.get(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['dn'], 99)

    def test_get_dn_by_diameter_without_standard(self):
        url = reverse('pipediameter-get-dn-by-diameter')
        data = {}
        response = self.client.get(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "Параметр 'standard' обязателен.")


    def test_get_dn_by_diameter_with_wrong_data(self):
        url = reverse('pipediameter-get-dn-by-diameter')
        data = {'standard': 'test', 'size': 100.0}  # Некорректный стандарт
        response = self.client.get(url, data, format='json')
        data_2 = {'standard': 1, 'size': 'test'}  # Не верные размеры
        response_2 = self.client.get(url, data_2, format='json')
        data_3 = {'standard': 3}  # Отсутствующий DN
        response_3 = self.client.get(url, data_3, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "Некорректное значение standard. Оно должно содержать числа, разделенные запятой.")

        self.assertEqual(response_2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response_2.data['error'], "Некорректное значение size. Оно должно содержать положительные числа, разделенные запятой.")

        self.assertEqual(response_3.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response_3.data['error'], "DN не найден")
