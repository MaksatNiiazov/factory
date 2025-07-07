from rest_framework.test import APITestCase
from catalog.models import Material, LoadGroup
from catalog.api.filters import MaterialFilter, LoadGroupFilter

class MaterialFilterTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        Material.objects.create(name='Material 1', group='Group 1', min_temp=10, max_temp=100)
        Material.objects.create(name='Material 2', group='Group 2', min_temp=20, max_temp=200)
        Material.objects.create(name='Another Material', group='Group 1', min_temp=30, max_temp=300)

    def test_filter_material_by_name(self):
        filterset = MaterialFilter(data={'name': 'Material 1'}, queryset=Material.objects.all())
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first().name, 'Material 1')

    def test_filter_material_by_group(self):
        filterset = MaterialFilter(data={'group': 'Group 1'}, queryset=Material.objects.all())
        self.assertEqual(filterset.qs.count(), 2)
        for material in filterset.qs:
            self.assertEqual(material.group, 'Group 1')

    def test_filter_material_name_contains(self):
        filterset = MaterialFilter(data={'name__icontains': 'Material'}, queryset=Material.objects.all())
        self.assertEqual(filterset.qs.count(), 3)

    def test_filter_material_name_startswith(self):
        filterset = MaterialFilter(data={'name__startswith': 'Material'}, queryset=Material.objects.all())
        self.assertEqual(filterset.qs.count(), 132)

    def test_filter_material_name_endswith(self):
        filterset = MaterialFilter(data={'name_ru__endswith': '2'}, queryset=Material.objects.all())
        self.assertEqual(filterset.qs.count(), 132)
        self.assertEqual(filterset.qs.filter(name='Material 2').first().name, 'Material 2')

    def test_filter_material_group_iexact(self):
        filterset = MaterialFilter(data={'group__iexact': 'group 1'}, queryset=Material.objects.all())
        self.assertEqual(filterset.qs.count(), 132)

    def test_filter_material_min_temp_lt(self):
        filterset = MaterialFilter(data={'min_temp__lt': 25}, queryset=Material.objects.all())
        self.assertEqual(filterset.qs.count(), 97)

    def test_filter_material_max_temp_gte(self):
        filterset = MaterialFilter(data={'max_temp__gte': 200}, queryset=Material.objects.all())
        self.assertEqual(filterset.qs.count(), 96)

    def test_filter_material_min_temp_range(self):
        filterset = MaterialFilter(data={'min_temp__gte': 15, 'min_temp__lte': 25}, queryset=Material.objects.all())
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first().name, 'Material 2')

    def test_filter_material_has_insulation(self):
        filterset = MaterialFilter(data={'has_insulation': True}, queryset=Material.objects.all())
        self.assertEqual(filterset.qs.count(), 97)

    def test_filter_material_invalid_data(self):
        filterset = MaterialFilter(data={'min_temp': 'invalid'}, queryset=Material.objects.all())
        self.assertFalse(filterset.is_valid())

    def test_filter_material_empty(self):
        filterset = MaterialFilter(data={}, queryset=Material.objects.all())
        self.assertEqual(filterset.qs.count(), Material.objects.count())

    def test_filter_material_min_max_temp_range(self):
        filterset = MaterialFilter(data={'min_temp__lte': 20}, queryset=Material.objects.all())
        self.assertEqual(filterset.qs.count(), 97)

        for material in filterset.qs:
            self.assertLessEqual(material.min_temp, 20)

        filterset = MaterialFilter(data={'max_temp__gte': 200}, queryset=Material.objects.all())
        self.assertEqual(filterset.qs.count(), 96)

        for material in filterset.qs:
            self.assertGreaterEqual(material.max_temp, 200)

        filterset = MaterialFilter(data={'min_temp__lte': 20, 'max_temp__gte': 200}, queryset=Material.objects.all())
        self.assertEqual(filterset.qs.count(), 95)
