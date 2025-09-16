from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from catalog.models import ProductClass, ProductFamily, PipeMountingGroup, PipeMountingRule
from catalog.choices import PipeDirectionChoices
from ops.models import Item, DetailType, Variant, Attribute, FieldSet
from ops.choices import AttributeType, AttributeUsageChoices

User = get_user_model()


class AssemblyLengthAPITest(TestCase):
    def setUp(self):
        # Пользователь
        self.user = User.objects.create_user(email='u@example.com', password='pass')

        # Класс и семья SSB, флаг верхнего крепления не важен здесь
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

        # Вариант изделия и Item
        self.variant = Variant.objects.create(detail_type=self.detail, name="SSB Var")
        self.item = Item.objects.create(
            type=self.detail,
            variant=self.variant,
            author=self.user,
            parameters={
                "catalog": [
                    {"fn": 50, "stroke": 100, "L2_min": 40, "L2_max": 60, "L2_avg": 50,
                     "L3": 20, "L4": 20, "block_length": 40}
                ]
            }
        )

        # Группа креплений A → два варианта с mounting_size 10 и 15
        fs = FieldSet.objects.create(name="Mount Params", label="Монтаж")
        self.varA1 = Variant.objects.create(detail_type=self.detail, name="Clamp A1")
        Attribute.objects.create(
            variant=self.varA1, type=AttributeType.NUMBER, usage=AttributeUsageChoices.CUSTOM,
            name='mounting_size', default='10.0', fieldset=fs, position=1
        )
        self.varA2 = Variant.objects.create(detail_type=self.detail, name="Clamp A2")
        Attribute.objects.create(
            variant=self.varA2, type=AttributeType.NUMBER, usage=AttributeUsageChoices.CUSTOM,
            name='mounting_size', default='15.0', fieldset=fs, position=2
        )
        groupA = PipeMountingGroup.objects.create(name="Mount A Group")
        groupA.variants.add(self.varA1, self.varA2)
        PipeMountingRule.objects.create(
            family=fam, num_spring_blocks=1, pipe_direction=PipeDirectionChoices.X.value
        ).pipe_mounting_groups_bottom.add(groupA)

        # Группа креплений B → один вариант с mounting_size 5
        self.varB = Variant.objects.create(detail_type=self.detail, name="Clamp B")
        Attribute.objects.create(
            variant=self.varB, type=AttributeType.NUMBER, usage=AttributeUsageChoices.CUSTOM,
            name='mounting_size', default='5.0', fieldset=fs, position=3
        )
        from catalog.models import ComponentGroup
        from catalog.choices import ComponentGroupType
        groupB = ComponentGroup.objects.create(group_type=ComponentGroupType.SERIES_SELECTABLE)
        groupB.detail_types.add(self.detail)

        self.client = APIClient()
        self.url = reverse('shock-calc-assembly-length')

    def test_assembly_without_mounts(self):
        """Без A и B монтажей: system_length == L2_req."""
        payload = {
            "item_id": self.item.id,
            "load_type": "H",
            "load_value": 50.0,
            "sn": 10.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            "use_extra_margin": False,
            "mounting_variants": [],
            "top_mount_variants": []
        }
        print(f"\n>>> test_assembly_without_mounts REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_assembly_without_mounts RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        comp = resp.data["components"]
        # L2_req == 50
        self.assertEqual(comp["block_center"], 50)
        self.assertEqual(resp.data["system_length"], comp["block_center"])
        self.assertEqual(comp["mounting_A"], 0.0)
        self.assertEqual(comp["mounting_B"], 0.0)

    def test_assembly_with_mounts(self):
        """С монтажной длиной и креплениями: system_length = L2_req + sum_A + sum_B."""
        # Сначала получим L2_req через shock-calc: без монтажа это 50
        payload_block = {
            "item_id": self.item.id,
            "load_type": "H",
            "load_value": 50.0,
            "sn": 10.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            "use_extra_margin": False
        }
        # L2_req = 50
        # Теперь assembly-length с монтажами
        payload = {
            **payload_block,
            "mounting_variants": [self.varA1.id, self.varA2.id],  # sum_A = 25
            "top_mount_variants": [self.varB.id]  # sum_B = 5
        }
        print(f"\n>>> test_assembly_with_mounts REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_assembly_with_mounts RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK, msg=resp.content.decode('utf-8'))
        comp = resp.data["components"]
        # system_length = 50 + 25 + 5 = 80
        self.assertAlmostEqual(resp.data["system_length"], 80.0, places=3)
        self.assertAlmostEqual(comp["mounting_A"], 25.0, places=3)
        self.assertAlmostEqual(comp["mounting_B"], 5.0, places=3)
