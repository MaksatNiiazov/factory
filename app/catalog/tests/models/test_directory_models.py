from unittest.mock import Mock
from django.test import TestCase
from catalog.models import Directory, DirectoryField, DirectoryEntry, DirectoryEntryValue
from catalog.choices import FieldTypeChoices


class DirectoryModelLogicTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.directory = Directory.objects.create(name='Test Directory')
        cls.directory_field_int = DirectoryField.objects.create(
            directory=cls.directory, name='Integer Field', field_type=FieldTypeChoices.INT
        )
        cls.directory_field_str = DirectoryField.objects.create(
            directory=cls.directory, name='String Field', field_type=FieldTypeChoices.STR
        )
        cls.directory_entry = DirectoryEntry.objects.create(directory=cls.directory)

    def test_directory_str_method(self):
        """Тест строкового представления модели Directory"""
        directory = Directory.objects.create(name='Test Directory')
        self.assertEqual(str(directory), 'Test Directory')

    def test_directory_entry_str_method(self):
        """Тест строкового представления модели DirectoryEntry"""
        entry = DirectoryEntry.objects.create(directory=self.directory)
        self.assertEqual(str(entry), f'Запись #{entry.id} в {self.directory.name}')

    def test_directory_field_str_method(self):
        """Тест строкового представления модели DirectoryField"""
        field = DirectoryField.objects.create(directory=self.directory, name="Test Field",
                                              field_type=FieldTypeChoices.STR)
        self.assertEqual(str(field), "Test Directory -> Test Field (str)")

    def test_directory_save_updates_entries(self):
        """Тест обновления display_name у DirectoryEntry при изменении шаблона"""
        directory = Directory.objects.create(name='Test Directory', display_name_template='Old Template')
        entry = DirectoryEntry.objects.create(directory=directory)
        directory.display_name_template = 'New Template'
        directory.save()
        entry.refresh_from_db()
        self.assertEqual(entry.display_name, 'New Template')

    def test_directory_entry_value_set_value_integer(self):
        """Тест установки числового значения в DirectoryEntryValue"""
        value = DirectoryEntryValue(entry=self.directory_entry, directory_field=self.directory_field_int)
        value.set_value(10)
        self.assertEqual(value.int_value, 10)
        self.assertIsNone(value.str_value)

    def test_directory_entry_value_set_value_string(self):
        """Тест установки строкового значения в DirectoryEntryValue"""
        value = DirectoryEntryValue(entry=self.directory_entry, directory_field=self.directory_field_str)
        value.set_value("Test String")
        self.assertEqual(value.str_value, "Test String")
        self.assertIsNone(value.int_value)

    def test_directory_entry_value_set_value_none(self):
        """Тест очистки значения в DirectoryEntryValue"""
        value = DirectoryEntryValue(entry=self.directory_entry, directory_field=self.directory_field_int)
        value.set_value(None)
        self.assertIsNone(value.int_value)

    def test_directory_entry_display_name(self):
        """Тест display_name у DirectoryEntry"""
        entry = DirectoryEntry.objects.create(directory=self.directory, display_name="Custom Name")
        self.assertEqual(entry.display_name, "Custom Name")

    def test_directory_refresh_all_entries_display_name(self):
        """Тест массового обновления display_name у записей DirectoryEntry"""
        directory = Directory.objects.create(name='Test Directory')
        entry1 = DirectoryEntry.objects.create(directory=directory)
        entry2 = DirectoryEntry.objects.create(directory=directory)
        directory.refresh_all_entries_display_name()
        entry1.refresh_from_db()
        entry2.refresh_from_db()
        self.assertEqual(entry1.display_name, entry1.display_name)
        self.assertEqual(entry2.display_name, entry2.display_name)

    def test_directory_entry_value_reset_on_type_change(self):
        """Тест очистки ненужных полей в DirectoryEntryValue при изменении типа"""
        value = DirectoryEntryValue.objects.create(entry=self.directory_entry, directory_field=self.directory_field_int)
        value.set_value(10)
        self.assertEqual(value.int_value, 10)

        # Меняем поле на строковое
        value.directory_field = self.directory_field_str
        value.set_value("New String")
        value.save()

        # Проверяем, что старое числовое значение стерлось
        self.assertIsNone(value.int_value)
        self.assertEqual(value.str_value, "New String")
