from unittest.mock import Mock
from django.contrib.admin.sites import site
from django.test import TestCase
from catalog.admin import DirectoryEntryAdmin
from catalog.models import Directory, DirectoryEntry, DirectoryEntryValue, DirectoryField
from catalog.choices import FieldTypeChoices

class DirectoryAdminTest(TestCase):
    def setUp(self):
        # Создаем тестовый объект справочника
        self.directory = Directory.objects.create(name='Test Directory')
        # Создаем поле справочника для проверки отображения значений в админке
        self.directory_field = DirectoryField.objects.create(
            directory=self.directory,
            name='Field 1',
            field_type=FieldTypeChoices.STR
        )
        # Создаем запись справочника и устанавливаем для неё значение поля
        self.entry = DirectoryEntry.objects.create(directory=self.directory)
        self.entry_value = DirectoryEntryValue.objects.create(
            entry=self.entry,
            directory_field=self.directory_field
        )
        self.entry_value.set_value("Test Value")
        # Создаем экземпляр административного класса для DirectoryEntry
        self.admin_instance = DirectoryEntryAdmin(model=DirectoryEntry, admin_site=site)

    def test_get_queryset(self):
        request = Mock()
        queryset = self.admin_instance.get_queryset(request)
        # Проверяем, что нужное поле присутствует в префетч связанных полей
        self.assertIn('values__directory_field', queryset._prefetch_related_lookups)

    def test_get_values(self):
        # Проверяем, что метод get_values корректно формирует строку с данными записи
        result = self.admin_instance.get_values(self.entry)
        # Ожидаемый результат зависит от реализации метода.
        # Предположим, что метод формирует строку в формате "Field 1=Test Value"
        self.assertEqual(result, "Field 1=Test Value")
