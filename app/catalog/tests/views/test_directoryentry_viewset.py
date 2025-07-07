from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from catalog.models import Directory, DirectoryField, DirectoryEntry, DirectoryEntryValue
from catalog.choices import FieldTypeChoices
from kernel.models import User

class DirectoryEntryViewSetTest(APITestCase):
    def setUp(self):
        # Очистим записи перед каждым тестом
        DirectoryEntry.objects.all().delete()
        # Создадим справочник
        self.directory = Directory.objects.create(name="Test Directory")
        # Создадим два поля: одно для общих тестов и другое для теста получения записи
        self.valid_field = DirectoryField.objects.create(
            directory=self.directory,
            name="valid_field",  # имя, которое будет использоваться в запросах
            field_type=FieldTypeChoices.STR
        )
        self.field1 = DirectoryField.objects.create(
            directory=self.directory,
            name="field1",  # для теста retrieve
            field_type=FieldTypeChoices.STR
        )
        # Создадим суперпользователя и авторизуемся
        self.user = User.objects.create_superuser(email='testuser@example.com', password='testpass')
        response = self.client.post(
            reverse('user-login'),
            {'username': 'testuser@example.com', 'password': 'testpass'},
            format='json'
        )
        self.token = response.data.get('token')
        self.assertIsNotNone(self.token, "Ошибка авторизации: токен не получен")
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_create_directory_entry(self):
        """Проверяем, что API успешно создаёт запись при корректных данных"""
        url = reverse('directory-entries-list', kwargs={'directory_pk': self.directory.id})
        # Передаём данные как плоский JSON-объект, ключ должен совпадать с именем поля: "valid_field"
        data = {self.valid_field.name: "Correct Value"}
        response = self.client.post(url, data, format='json')
        # Если всё прошло хорошо, API должно вернуть статус 201
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Проверяем, что запись создана
        self.assertTrue(DirectoryEntry.objects.filter(directory=self.directory).exists(), "Запись должна быть создана")
        new_entry = DirectoryEntry.objects.filter(directory=self.directory).order_by('-id').first()
        entry_value = DirectoryEntryValue.objects.filter(entry=new_entry, directory_field=self.valid_field).first()
        self.assertIsNotNone(entry_value, "Значение записи не создано")
        self.assertEqual(entry_value.str_value, "Correct Value")

    def test_list_directory_entries(self):
        """Проверяем получение списка записей справочника"""
        url = reverse('directory-entries-list', kwargs={'directory_pk': self.directory.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_directory_entry(self):
        """Проверяем получение одной записи справочника"""
        directory_entry = DirectoryEntry.objects.create(directory=self.directory)
        # Создаем значение для поля "field1"
        DirectoryEntryValue.objects.create(
            entry=directory_entry,
            directory_field=self.field1,
            str_value="Value 1"
        )
        url = reverse(
            'directory-entries-detail',
            kwargs={'directory_pk': self.directory.id, 'pk': directory_entry.id}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get(self.field1.name), "Value 1")

    def test_update_directory_entry(self):
        """Проверяем обновление записи справочника через PUT"""
        directory_entry = DirectoryEntry.objects.create(directory=self.directory)
        update_field = DirectoryField.objects.create(
            directory=self.directory,
            name='field_to_update',
            field_type=FieldTypeChoices.STR
        )
        DirectoryEntryValue.objects.create(
            entry=directory_entry,
            directory_field=update_field,
            str_value='Initial Value'
        )
        url = reverse(
            'directory-entries-detail',
            kwargs={'directory_pk': self.directory.id, 'pk': directory_entry.id}
        )
        data = {update_field.name: 'Updated Value'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        entry_value = DirectoryEntryValue.objects.get(entry=directory_entry, directory_field=update_field)
        self.assertEqual(entry_value.str_value, 'Updated Value')

    def test_delete_directory_entry(self):
        """Проверяем удаление записи справочника"""
        directory_entry = DirectoryEntry.objects.create(directory=self.directory)
        url = reverse(
            'directory-entries-detail',
            kwargs={'directory_pk': self.directory.id, 'pk': directory_entry.id}
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_with_non_dict_data(self):
        """Проверяем, что если тело запроса не является объектом, возвращается ошибка 400"""
        url = reverse('directory-entries-list', kwargs={'directory_pk': self.directory.id})
        response = self.client.post(url, data=[1, 2, 3], format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("JSON-объектом", str(response.data))

    def test_partial_update_with_non_dict_data(self):
        """Проверяем, что PATCH с некорректным типом данных возвращает ошибку 400"""
        entry = DirectoryEntry.objects.create(directory=self.directory)
        url = reverse('directory-entries-detail', kwargs={'directory_pk': self.directory.id, 'pk': entry.id})
        response = self.client.patch(url, data=[1, 2, 3], format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("JSON-объектом", str(response.data))

    def test_directory_field_not_found(self):
        """Проверяем, что попытка создать запись в несуществующем справочнике возвращает 404"""
        url = reverse('directory-entries-list', kwargs={'directory_pk': 0})
        data = {self.valid_field.name: "New Value"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'].code, 'not_found')

    def test_create_directory_field_with_missing_directory(self):
        """Проверяем создание DirectoryField с автоматическим привязыванием к справочнику"""
        url = reverse('directory-fields-list', kwargs={'directory_pk': self.directory.id})
        data = {
            'name': 'New Field',
            'field_type': FieldTypeChoices.STR,
            'directory': self.directory.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, f"Ошибка: {response.data}")
        created_field = DirectoryField.objects.filter(name='New Field').first()
        self.assertIsNotNone(created_field, "Поле справочника не создано")
        self.assertEqual(created_field.directory, self.directory, "Поле должно автоматически привязываться к справочнику")

    def test_create_directory_field_with_invalid_field_type(self):
        """Проверяем, что создание DirectoryField с неверным field_type вызывает ошибку"""
        url = reverse('directory-fields-list', kwargs={'directory_pk': self.directory.id})
        data = {'name': 'Invalid Field', 'field_type': 'wrong_type'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('field_type', response.data['fields'], "Поле field_type должно вызывать ошибку валидации")

    def test_delete_nonexistent_directory_entry(self):
        """Проверяем, что попытка удалить несуществующую запись возвращает 404"""
        url = reverse('directory-entries-detail', kwargs={'directory_pk': self.directory.id, 'pk': 9999})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'].code, 'not_found')

    def test_create_entry_with_nonexistent_field(self):
        """Проверяем, что API не создаёт запись, если указано несуществующее поле"""
        url = reverse('directory-entries-list', kwargs={'directory_pk': self.directory.id})
        data = {'nonexistent_field': 'Some Value'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, "Ожидался 400, но API вернул другой код")
        error_messages = str(response.data.get("fields", ""))
        self.assertIn("не найдено в справочнике", error_messages, "Сообщение об ошибке отсутствует")
        self.assertFalse(DirectoryEntry.objects.exists(), "Запись не должна существовать после ошибки")

    def test_create_entry_with_valid_data(self):
        """Проверяем, что API успешно создаёт запись при корректных данных"""
        url = reverse('directory-entries-list', kwargs={'directory_pk': self.directory.id})
        data = {self.valid_field.name: "Correct Value"}
        response = self.client.post(url, data, format='json')
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(DirectoryEntry.objects.filter(directory=self.directory).exists(), "Запись должна быть создана")
        new_entry = DirectoryEntry.objects.latest('id')
        entry_value = DirectoryEntryValue.objects.filter(entry=new_entry, directory_field=self.valid_field).first()
        self.assertIsNotNone(entry_value, "Значение должно быть сохранено")
        self.assertEqual(entry_value.str_value, "Correct Value")
