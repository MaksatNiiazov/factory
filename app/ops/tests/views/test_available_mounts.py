from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from catalog.choices import PipeDirectionChoices
from catalog.models import ProductClass, ProductFamily, PipeMountingGroup, PipeMountingRule
from ops.choices import AttributeType, AttributeUsageChoices
from ops.models import Item, DetailType, Variant, Attribute, FieldSet

User = get_user_model()


class AvailableMountsAPITest(TestCase):
    def setUp(self):
        # 1) Пользователь
        self.user = User.objects.create_user(email='tester@example.com', password='pass')

        # 2) Класс и семья SSB
        prod_class = ProductClass.objects.create(name="TestClass")
        self.family = ProductFamily.objects.create(
            product_class=prod_class,
            name="SSB Family",
            is_upper_mount_selectable=False
        )

        # 3) DetailType SSB
        self.detail = DetailType.objects.create(
            product_family=self.family,
            name="SSB Product",
            designation="SSB",
            category=DetailType.PRODUCT,
            branch_qty=DetailType.BranchQty.ONE
        )

        # 4) Варианты нижних креплений A
        fs = FieldSet.objects.create(name="Mount Params", label="Монтаж")
        self.varA1 = Variant.objects.create(detail_type=self.detail, name="Clamp A1")
        Attribute.objects.create(
            variant=self.varA1,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.CUSTOM,
            name='mounting_size',
            default='10.0',
            fieldset=fs,
            position=1
        )
        self.varA2 = Variant.objects.create(detail_type=self.detail, name="Clamp A2")
        Attribute.objects.create(
            variant=self.varA2,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.CUSTOM,
            name='mounting_size',
            default='15.0',
            fieldset=fs,
            position=2
        )

        # 5) Группа A и правило
        self.group = PipeMountingGroup.objects.create(name="Clamp Group A")
        self.group.variants.add(self.varA1, self.varA2)
        self.rule = PipeMountingRule.objects.create(
            family=self.family,
            num_spring_blocks=1,
            pipe_direction=PipeDirectionChoices.X.value
        )
        self.rule.pipe_mounting_groups_bottom.add(self.group)

        # 6) Item с любым catalog
        self.item = Item.objects.create(
            type=self.detail,
            variant=self.varA1,
            author=self.user,
            parameters={"catalog": []}
        )

        # 7) Клиент и URL
        self.client = APIClient()
        self.url = reverse('shock-calc-mounts')

    def test_mounts_without_rule(self):
        """Если нет правила для заданных branch_qty/direction → []"""
        # удаляем правило
        PipeMountingRule.objects.all().delete()

        payload = {
            "item_id": self.item.id,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value
        }
        print(f"\n>>> test_mounts_without_rule REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_mounts_without_rule RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])

    def test_available_mounts(self):
        """Возвращает варианты нижних креплений A с правильными размерами."""
        payload = {
            "item_id": self.item.id,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value
        }
        print(f"\n>>> test_available_mounts REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_available_mounts RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        got = {e['id']: e for e in resp.data}
        self.assertIn(self.varA1.id, got)
        self.assertIn(self.varA2.id, got)
        self.assertEqual(got[self.varA1.id]['mounting_size'], 10.0)
        self.assertEqual(got[self.varA2.id]['mounting_size'], 15.0)

    def test_invalid_item_id(self):
        """Неизвестный item_id → 404 Not Found."""
        payload = {
            "item_id": 9999,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value
        }
        print(f"\n>>> test_invalid_item_id REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_invalid_item_id RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_branch_qty(self):
        """branch_qty не соответствует ни одному правилу → []"""
        payload = {
            "item_id": self.item.id,
            "branch_qty": 2,  # правило есть только для 1
            "pipe_direction": PipeDirectionChoices.X.value
        }
        print(f"\n>>> test_invalid_branch_qty REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_invalid_branch_qty RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])

    def test_wrong_direction(self):
        """Неподдерживаемое pipe_direction → []"""
        payload = {
            "item_id": self.item.id,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.Y.value
        }
        print(f"\n>>> test_wrong_direction REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_wrong_direction RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])
