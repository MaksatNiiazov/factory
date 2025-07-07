from rest_framework.test import APITestCase
from catalog.models import LoadGroup
from catalog.api.filters import LoadGroupFilter


class LoadGroupFilterTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        LoadGroup.objects.create(lgv=12, kn=98)
        LoadGroup.objects.create(lgv=11, kn=12)
        LoadGroup.objects.create(lgv=12, kn=10)

    def test_filter_loadgroup_by_lgv(self):
        filterset = LoadGroupFilter(data={'lgv': 11}, queryset=LoadGroup.objects.all())
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first().lgv, 11)

    def test_filter_loadgroup_by_kn(self):
        filterset = LoadGroupFilter(data={'kn': 98}, queryset=LoadGroup.objects.all())
        self.assertEqual(filterset.qs.count(), 1)
        self.assertEqual(filterset.qs.first().kn, 98)

    def test_filter_loadgroup_lgv_gt(self):
        filterset = LoadGroupFilter(data={'lgv__gt': 11}, queryset=LoadGroup.objects.all())
        self.assertEqual(filterset.qs.count(), 16)

    def test_filter_loadgroup_lgv_lt(self):
        filterset = LoadGroupFilter(data={'lgv__lt': 12}, queryset=LoadGroup.objects.all())
        self.assertEqual(filterset.qs.count(), 16)
        self.assertEqual(filterset.qs.first().lgv, 12)

    def test_filter_loadgroup_kn_gte(self):
        filterset = LoadGroupFilter(data={'kn__gte': 12}, queryset=LoadGroup.objects.all())
        self.assertEqual(filterset.qs.count(), 16)

    def test_filter_loadgroup_kn_lte(self):
        filterset = LoadGroupFilter(data={'kn__lte': 10}, queryset=LoadGroup.objects.all())
        self.assertEqual(filterset.qs.count(), 16)

    def test_filter_loadgroup_empty(self):
        filterset = LoadGroupFilter(data={}, queryset=LoadGroup.objects.all())
        self.assertEqual(filterset.qs.count(), LoadGroup.objects.count())
