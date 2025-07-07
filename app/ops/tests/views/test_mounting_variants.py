from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from catalog.choices import ComponentGroupType
from catalog.models import ProductClass, ProductFamily, ComponentGroup
from ops.choices import AttributeType, AttributeUsageChoices
from ops.models import Item, DetailType, Variant, Attribute, FieldSet

User = get_user_model()


class AvailableTopMountsAPITest(TestCase):
    def setUp(self):
        # Пользователь
        self.user = User.objects.create_user(email='u@example.com', password='pass')

        # Класс и семья SSB, включаем выбор верхнего крепления
        cls = ProductClass.objects.create(name="TestClass")
        fam = ProductFamily.objects.create(
            product_class=cls,
            name="SSB Family",
            is_upper_mount_selectable=True
        )

        # DetailType SSB
        self.detail = DetailType.objects.create(
            product_family=fam,
            name="SSB Product",
            designation="SSB",
            category=DetailType.PRODUCT,
            branch_qty=DetailType.BranchQty.ONE
        )

        # Варианты для верхнего крепления
        self.varA = Variant.objects.create(detail_type=self.detail, name="Top A")
        self.varB = Variant.objects.create(detail_type=self.detail, name="Top B")

        # Атрибут mounting_size только для varA
        fs = FieldSet.objects.create(name="Mount Params", label="Монтаж")
        Attribute.objects.create(
            variant=self.varA,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.CUSTOM,
            name='mounting_size',
            default='12.5',
            fieldset=fs,
            position=1
        )
        # varB не имеет атрибута, будет size=0.0

        # ComponentGroup для верхнего крепления (B)
        grp = ComponentGroup.objects.create(group_type=ComponentGroupType.SERIES_SELECTABLE)
        grp.detail_types.add(self.detail)

        # Сам item (он нужен для lookup)
        self.item = Item.objects.create(
            type=self.detail,
            variant=self.varA,
            author=self.user,
            parameters={"catalog": []}
        )

        self.client = APIClient()
        self.url = reverse('shock-calc-top-mounts')

    def test_top_mounts_not_selectable(self):
        """Если is_upper_mount_selectable=False → пустой список."""
        # Выключаем флаг в семье
        self.detail.product_family.is_upper_mount_selectable = False
        self.detail.product_family.save()

        payload = {
            "item_id": self.item.id,
            "branch_qty": 1
        }
        print(f"\n>>> test_top_mounts_not_selectable REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_top_mounts_not_selectable RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])

    def test_available_top_mounts(self):
        """Возвращает все варианты верхнего крепления с правильным mounting_size."""
        payload = {
            "item_id": self.item.id,
            "branch_qty": 1
        }
        print(f"\n>>> test_available_top_mounts REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_available_top_mounts RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        got = {e['id']: e for e in resp.data}
        self.assertIn(self.varA.id, got)
        self.assertIn(self.varB.id, got)

        self.assertEqual(got[self.varA.id]['name'], self.varA.name)
        self.assertAlmostEqual(got[self.varA.id]['mounting_size'], 12.5)

        self.assertEqual(got[self.varB.id]['name'], self.varB.name)
        self.assertAlmostEqual(got[self.varB.id]['mounting_size'], 0.0)
