from django.test import TestCase
from catalog.models import Directory
from catalog.api.serializers import DirectorySerializer

class DirectorySerializerErpDisplayNameTest(TestCase):
    def test_get_erp_display_name_returns_value_when_present(self):
        directory = Directory(name='Test Directory', display_name_template='Template')
        serializer = DirectorySerializer(instance=directory)
        self.assertEqual(serializer.data.get("erp_display_name"), None)

    def test_get_erp_display_name_returns_none_when_missing(self):
        directory = Directory(name='Test Directory', display_name_template='Template')
        serializer = DirectorySerializer(instance=directory)
        self.assertIsNone(serializer.data.get("erp_display_name"))
