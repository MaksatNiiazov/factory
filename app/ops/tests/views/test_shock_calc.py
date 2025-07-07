from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from catalog.choices import PipeDirectionChoices
from catalog.models import ProductClass, ProductFamily, PipeMountingGroup, PipeMountingRule
from ops.models import (
    Item, DetailType, Variant,
    FieldSet, Attribute, AttributeType, AttributeUsageChoices
)

User = get_user_model()


class ShockCalcAPITest(TestCase):
    def setUp(self):
        # 1) Пользователь
        self.user = User.objects.create_user(email='tester@example.com', password='pass')

        # 2) ProductClass → ProductFamily
        self.prod_class = ProductClass.objects.create(name="TestClass")
        self.prod_family = ProductFamily.objects.create(
            product_class=self.prod_class,
            name="SSB Family",
            is_upper_mount_selectable=False
        )

        # 3) DetailType
        self.detail_type = DetailType.objects.create(
            product_family=self.prod_family,
            name="SSB Product",
            designation="SSB",
            category=DetailType.PRODUCT,
            branch_qty=DetailType.BranchQty.ONE
        )

        # 4) Variant для самого амортизатора
        self.item_variant = Variant.objects.create(
            detail_type=self.detail_type,
            name="SSB Var"
        )

        # 5) Item с JSON-каталогом catalog
        self.item = Item.objects.create(
            type=self.detail_type,
            variant=self.item_variant,
            author=self.user,
            parameters={
                "catalog": [
                    {"fn": 50, "stroke": 100, "L2_min": 40, "L2_max": 60, "L2_avg": 50, "L3": 20, "L4": 20,
                     "block_length": 40},
                    {"fn": 100, "stroke": 200, "L2_min": 90, "L2_max": 110, "L2_avg": 100, "L3": 30, "L4": 30,
                     "block_length": 60},
                    {"fn": 1000, "stroke": None, "L2_min": None, "L2_max": None, "L2_avg": None, "L3": None, "L4": None,
                     "block_length": None}
                ]
            }
        )

        # 6) Группа креплений и два её варианта
        self.group = PipeMountingGroup.objects.create(name="Clamp Group")
        self.fieldset = FieldSet.objects.create(name="Mounting Params", label="Монтажные параметры")

        self.variant1 = Variant.objects.create(detail_type=self.detail_type, name="Clamp A")
        Attribute.objects.create(
            variant=self.variant1,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.CUSTOM,
            name='mounting_size',
            default='10.0',
            fieldset=self.fieldset,
            position=1
        )

        self.variant2 = Variant.objects.create(detail_type=self.detail_type, name="Clamp B")
        Attribute.objects.create(
            variant=self.variant2,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.CUSTOM,
            name='mounting_size',
            default='15.0',
            fieldset=self.fieldset,
            position=2
        )

        self.group.variants.add(self.variant1, self.variant2)

        # 7) Правило PipeMountingRule — используем PipeDirectionChoices.X
        self.rule = PipeMountingRule.objects.create(
            family=self.prod_family,
            num_spring_blocks=1,
            pipe_direction=PipeDirectionChoices.X.value
        )
        self.rule.pipe_mounting_groups.add(self.group)

        # 8) Клиент и URL для тестов
        self.client = APIClient()
        self.url = reverse('shock-calc')

    def test_minimal_request(self):
        """Без mounting_length и mounting_variants → 200 + базовые поля."""
        payload = {
            "item_id": self.item.id,
            "load_type": "H",
            "load_value": 50.0,
            "sn": 10.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            "use_extra_margin": False
        }
        # выведем запрос и ответ для отладки
        print(f"\n>>> test_minimal_request REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_minimal_request RESPONSE: status={resp.status_code}, data={resp.data}")

        # Проверяем, что вернулось 200 и ключевые поля
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for key in ("result", "fn", "stroke", "type"):
            self.assertIn(key, resp.data)
        # И что fn=50, stroke=100, type=1
        self.assertEqual(resp.data["fn"], 50)
        self.assertEqual(resp.data["stroke"], 100)
        self.assertEqual(resp.data["type"], 1)

    def test_hard_mounting_length_type1(self):
        """mounting_length_full внутри [L2_min;L2_max] → type=1, extender=0."""
        payload = {
            "item_id": self.item.id,
            "load_type": "H",
            "load_value": 50.0,
            "sn": 20.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            "mounting_length_full": 80.0,  # 80 - (10+15) = 55 ∈ [40;60]
            "mounting_variants": [self.variant1.id, self.variant2.id],
            "use_extra_margin": False
        }
        print(f"\n>>> test_hard_mounting_length_type1 REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_hard_mounting_length_type1 RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # проверим именно type и extender
        self.assertEqual(resp.data['type'], 1)
        self.assertEqual(resp.data['extender'], 0.0)

    def test_type2_with_extender(self):
        """L2_req вне [L2_min;L2_max] → type=2 и extender = L2_req - block_length."""
        payload = {
            "item_id": self.item.id,
            "load_type": "H",
            "load_value": 50.0,
            "sn": 20.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            # mounting_length_full так, что L2_req = 90 - (10+15) = 65 > L2_max(60)
            "mounting_length_full": 90.0,
            "mounting_variants": [self.variant1.id, self.variant2.id],
            "use_extra_margin": False
        }
        print(f"\n>>> test_type2_with_extender REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_type2_with_extender RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['type'], 2)
        # ожидаем extender = 65 - block_length(40) = 25
        self.assertAlmostEqual(resp.data['extender'], 25.0, places=3)

    def test_use_extra_margin_allows_type1(self):
        """use_extra_margin=True расширяет диапазон, и L2_req попадает в type=1."""
        payload = {
            "item_id": self.item.id,
            "load_type": "H",
            "load_value": 50.0,
            "sn": 20.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            # mounting_length_full так, что без доп. запаса было бы type=2,
            # но с запасом L2_req=85-(10+15)=60 попадает в расширенный [mn;mx]
            "mounting_length_full": 85.0,
            "mounting_variants": [self.variant1.id, self.variant2.id],
            "use_extra_margin": True
        }
        print(f"\n>>> test_use_extra_margin_allows_type1 REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_use_extra_margin_allows_type1 RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # теперь, несмотря на то что L2_req=60 == L2_max, type=1 and extender=0
        self.assertEqual(resp.data['type'], 1)
        self.assertEqual(resp.data['extender'], 0.0)

    def test_missing_mounting_variants(self):
        """mounting_length_full передана без mounting_variants → 400 Bad Request."""
        payload = {
            "item_id": self.item.id,
            "load_type": "H",
            "load_value": 50.0,
            "sn": 20.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            "mounting_length_full": 80.0,
            # "mounting_variants" отсутствует
            "use_extra_margin": False
        }
        print(f"\n>>> test_missing_mounting_variants REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_missing_mounting_variants RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_mounting_variants(self):
        """Переданы неверные mounting_variants → 400 Bad Request."""
        payload = {
            "item_id": self.item.id,
            "load_type": "H",
            "load_value": 50.0,
            "sn": 20.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            "mounting_length_full": 80.0,
            "mounting_variants": [9999],  # несуществующий ID
            "use_extra_margin": False
        }
        print(f"\n>>> test_invalid_mounting_variants REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_invalid_mounting_variants RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_load_too_large_returns_400(self):
        """Слишком большая нагрузка (нет подходящего FN) → 400 Bad Request."""
        payload = {
            "item_id": self.item.id,
            "load_type": "H",
            "load_value": 2000.0,  # слишком большая
            "sn": 10.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            "use_extra_margin": False
        }
        print(f"\n>>> test_load_too_large_returns_400 REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_load_too_large_returns_400 RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_stroke_candidate(self):
        """FN найден, но ни один stroke не ≥ sn*SN_MARGIN_COEF → 400 Bad Request."""
        payload = {
            "item_id": self.item.id,
            "load_type": "H",
            "load_value": 50.0,
            "sn": 1000.0,  # sn_margin = 1200 мм, ни один stroke (100 или 200) не дотягивает
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            "use_extra_margin": False
        }
        print(f"\n>>> test_no_stroke_candidate REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_no_stroke_candidate RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_pipe_direction(self):
        """Нет правила PipeMountingRule для заданного pipe_direction → 400 Bad Request."""
        payload = {
            "item_id": self.item.id,
            "load_type": "H",
            "load_value": 50.0,
            "sn": 10.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.Y.value,  # Y, а не X
            "mounting_length_full": 80.0,
            "mounting_variants": [self.variant1.id, self.variant2.id],
            "use_extra_margin": False
        }
        print(f"\n>>> test_invalid_pipe_direction REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_invalid_pipe_direction RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_item_id(self):
        """Неизвестный item_id → 404 Not Found."""
        payload = {
            "item_id": 9999,  # такого нет
            "load_type": "H",
            "load_value": 50.0,
            "sn": 10.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            "use_extra_margin": False
        }
        print(f"\n>>> test_invalid_item_id REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_invalid_item_id RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_load_type_hz(self):
        """Проверка load_type='HZ' (коэф. 1.5)."""
        payload = {
            "item_id": self.item.id,
            "load_type": "HZ",
            "load_value": 75.0,  # nom_per = 75/1.5 = 50
            "sn": 10.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            "use_extra_margin": False
        }
        print(f"\n>>> test_load_type_hz REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_load_type_hz RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['fn'], 50)
        self.assertEqual(resp.data['stroke'], 100)
        self.assertEqual(resp.data['type'], 1)

    def test_load_type_hs(self):
        """Проверка load_type='HS' (коэф. 1.7)."""
        payload = {
            "item_id": self.item.id,
            "load_type": "HS",
            "load_value": 85.0,  # nom_per = 85/1.7 = 50
            "sn": 10.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            "use_extra_margin": False
        }
        print(f"\n>>> test_load_type_hs REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_load_type_hs RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['fn'], 50)
        self.assertEqual(resp.data['stroke'], 100)
        self.assertEqual(resp.data['type'], 1)

    def test_negative_sn_handling(self):
        """SN отрицательное — используется abs(sn) для подбора stroke."""
        payload = {
            "item_id": self.item.id,
            "load_type": "H",
            "load_value": 50.0,
            "sn": -10.0,  # abs(-10)*1.2=12 → stroke=100
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            "use_extra_margin": False
        }
        print(f"\n>>> test_negative_sn_handling REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_negative_sn_handling RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # проверяем, что stroke выбран правильно
        self.assertEqual(resp.data['stroke'], 100)
        self.assertEqual(resp.data['type'], 1)

    def test_l2_req_default_equals_l2_avg(self):
        """Без монтажа L2_req == L2_avg выбранного блока."""
        payload = {
            "item_id": self.item.id,
            "load_type": "H",
            "load_value": 50.0,
            "sn": 10.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            "use_extra_margin": False
        }
        print(f"\n>>> test_l2_req_default_equals_l2_avg REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_l2_req_default_equals_l2_avg RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # L2_avg для fn=50 в нашем catalog == 50
        self.assertEqual(resp.data['L2_req'], resp.data['L2_avg'])

    def test_result_code_format(self):
        """Проверка формата строки result."""
        payload = {
            "item_id": self.item.id,
            "load_type": "H",
            "load_value": 50.0,
            "sn": 10.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            "use_extra_margin": False
        }
        print(f"\n>>> test_result_code_format REQUEST: {payload}")
        resp = self.client.post(self.url, payload, format='json')
        print(f"<<< test_result_code_format RESPONSE: status={resp.status_code}, data={resp.data}")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        expected = f"SSB {resp.data['fn']:04d}.{resp.data['stroke']:03d}.0000.{resp.data['type']}"
        self.assertEqual(resp.data['result'], expected)

    def test_auto_transition_to_next_stroke(self):
        """
        Если первый stroke меньше sn*1.2 → пропускается,
        и выбирается следующий stroke для того же FN.
        """
        # 1) Подготовим «двухступенчатый» каталог для fn=50:
        #    первый stroke=10 (меньше sn*1.2=24), второй stroke=100 (>=24)
        self.item.parameters['catalog'] = [
            {
                "fn": 50,
                "stroke": 10,
                "L2_min": 40, "L2_max": 60, "L2_avg": 50,
                "L3": 20, "L4": 20, "block_length": 40
            },
            {
                "fn": 50,
                "stroke": 100,
                "L2_min": 40, "L2_max": 60, "L2_avg": 50,
                "L3": 20, "L4": 20, "block_length": 40
            }
        ]
        # Сохраняем изменения в JSONField
        self.item.save(update_fields=['parameters'])

        # 2) Вызываем расчёт с sn=20 → sn_margin = 20*1.2 = 24
        resp = self.client.post(self.url, {
            "item_id": self.item.id,
            "load_type": "H",
            "load_value": 50.0,
            "sn": 20.0,
            "branch_qty": 1,
            "pipe_direction": PipeDirectionChoices.X.value,
            "use_extra_margin": False
        }, format='json')

        # 3) Ожидаем, что первый кандидат (stroke=10) пропущен,
        #    и выбран stroke=100
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['fn'], 50)
        self.assertEqual(resp.data['stroke'], 100)
        self.assertEqual(resp.data['type'], 1)
        self.assertEqual(resp.data['extender'], 0.0)
