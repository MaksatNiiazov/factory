from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.choices import FieldTypeChoices
from catalog.models import Directory, DirectoryField
from kernel.models import User

class DirectoryFieldViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.directory = Directory.objects.create(name='Test Directory')
        cls.directory_field = DirectoryField.objects.create(directory=cls.directory, name='Field 1')
        cls.user = User.objects.create_superuser(email='testuser@example.com', password='testpass')

    def setUp(self):
        response = self.client.post(
            reverse('user-login'),
            {'username': 'testuser@example.com', 'password': 'testpass'},
            format='json'
        )
        self.token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_list_directory_fields(self):
        url = reverse('directory-fields-list', args=[self.directory.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_directory_field(self):
        url = reverse('directory-fields-detail', args=[self.directory.id, self.directory_field.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Field 1')

    def test_update_directory_field(self):
        url = reverse('directory-fields-detail', args=[self.directory.id, self.directory_field.id])
        data = {'name': 'Updated Field'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.directory_field.refresh_from_db()
        self.assertEqual(self.directory_field.name, 'Updated Field')

    def test_create_directory_field(self):
        url = reverse('directory-fields-list', args=[self.directory.id])

        data = {
            'directory': self.directory.id,
            'name': 'New Field',
            'field_type': FieldTypeChoices.STR
        }

        response = self.client.post(url, data, format='json')


        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Field')

        self.assertTrue(DirectoryField.objects.filter(directory=self.directory, name='New Field').exists())
