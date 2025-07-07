from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from catalog.models import Directory
from kernel.models import User

class DirectoryViewSetTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Создаём тестовый справочник
        cls.directory = Directory.objects.create(
            name='Test Directory',
            display_name_template='Template'
        )
        # Создаём суперпользователя с нужными правами
        cls.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='testpass'
        )

    def setUp(self):
        """
        Выполняем логин под суперпользователем,
        чтобы иметь доступ к create/update/delete.
        """
        response = self.client.post(
            reverse('user-login'),  # поменяйте на актуальный эндпоинт логина, если нужно
            {'username': 'admin@example.com', 'password': 'testpass'},
            format='json'
        )
        self.token = response.data['token']
        # Устанавливаем заголовок Authorization для всех последующих запросов
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_list_directories(self):
        url = reverse('directory-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_directory(self):
        url = reverse('directory-detail', args=[self.directory.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Directory')

    def test_create_directory(self):
        """Создание нового справочника (POST)"""
        url = reverse('directory-list')
        data = {
            'name': 'New Directory',
            'display_name_template': 'Some template'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Directory.objects.filter(name='New Directory').exists())

    def test_update_directory(self):
        """Полное обновление (PUT)"""
        url = reverse('directory-detail', args=[self.directory.id])
        data = {
            'name': 'Updated Directory',
            'display_name_template': 'Updated Template'
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.directory.refresh_from_db()
        self.assertEqual(self.directory.name, 'Updated Directory')
        self.assertEqual(self.directory.display_name_template, 'Updated Template')

    def test_partial_update_directory(self):
        """Частичное обновление (PATCH)"""
        url = reverse('directory-detail', args=[self.directory.id])
        data = {'name': 'Partially Updated Directory'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.directory.refresh_from_db()
        # Убедимся, что обновилось только поле 'name'
        self.assertEqual(self.directory.name, 'Partially Updated Directory')
        self.assertEqual(self.directory.display_name_template, 'Template')

    def test_delete_directory(self):
        """Удаление (DELETE)"""
        url = reverse('directory-detail', args=[self.directory.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Directory.objects.filter(id=self.directory.id).exists())

    def test_retrieve_directory_not_found(self):
        """Сценарий, когда объект не найден (404)"""
        url = reverse('directory-detail', args=[999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
