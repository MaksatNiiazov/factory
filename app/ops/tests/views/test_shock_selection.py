from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from catalog.choices import PipeDirectionChoices
from catalog.models import ProductClass, ProductFamily, PipeMountingGroup, PipeMountingRule
from ops.choices import MoveUnit, TemperatureUnit, LoadUnit
from ops.models import (
    Item, DetailType, Variant,
    FieldSet, Attribute, AttributeType, AttributeUsageChoices, Project, ProjectItem
)

User = get_user_model()


class ShockSelectionAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(email='testuser@example.com', password='testpass')

        prod_class = ProductClass.objects.create(name="TestClass")
        cls.family = ProductFamily.objects.create(
            product_class=prod_class,
            name="SSB Family",
            is_upper_mount_selectable=False
        )

        # 3) DetailType SSB
        cls.detail = DetailType.objects.create(
            product_family=cls.family,
            name="SSB Product",
            designation="SSB",
            category=DetailType.PRODUCT,
            branch_qty=DetailType.BranchQty.ONE
        )

        # 4) Варианты нижних креплений A
        fs = FieldSet.objects.create(name="Mount Params", label="Монтаж")
        cls.varA1 = Variant.objects.create(detail_type=cls.detail, name="Clamp A1")
        Attribute.objects.create(
            variant=cls.varA1,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.CUSTOM,
            name='mounting_size',
            default='10.0',
            fieldset=fs,
            position=1
        )
        cls.varA2 = Variant.objects.create(detail_type=cls.detail, name="Clamp A2")
        Attribute.objects.create(
            variant=cls.varA2,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.CUSTOM,
            name='mounting_size',
            default='15.0',
            fieldset=fs,
            position=2
        )

        # 5) Группа A и правило
        cls.group = PipeMountingGroup.objects.create(name="Clamp Group A")
        cls.group.variants.add(cls.varA1, cls.varA2)
        cls.rule = PipeMountingRule.objects.create(
            family=cls.family,
            num_spring_blocks=1,
            pipe_direction=PipeDirectionChoices.X.value
        )
        cls.rule.pipe_mounting_groups_bottom.add(cls.group)

        # 6) Item с любым catalog
        cls.item = Item.objects.create(
            type=cls.detail,
            variant=cls.varA1,
            author=cls.user,
            parameters={"catalog": []}
        )

        cls.project = Project.objects.create(
            number='P-001',
            owner=cls.user,
            load_unit=LoadUnit.KN,
            move_unit=MoveUnit.MM,
            temperature_unit=TemperatureUnit.CELSIUS,
        )

        cls.project_item_1 = ProjectItem.objects.create(
            project=cls.project,
            original_item=cls.item,
            selection_params={
                "product_class": cls.family.product_class.id,
                "product_family": cls.family.id,
                "load_and_move": {
                    "load": 14,
                    "move": 100,
                    "load_type": "h",
                    "installation_length": None
                },
                "pipe_options": {
                    "location": "horizontal",
                    "shock_counts": 1
                },
                "pipe_params": {
                    "pipe_diameter": None,
                    "pipe_diameter_size_manual": None,
                    "support_distance": None,
                    "support_distance_manual": None,
                    "mounting_group_bottom": None,
                    "mounting_group_top": None,
                    "material": None,
                    "temperature": None
                },
                "pipe_clamp": {
                    "pipe_clamp_a": None,
                    "pipe_clamp_b": None
                },
                "variant": None
            }
        )

    def setUp(self):
        response = self.client.post(
            reverse('user-login'),
            {'username': 'testuser@example.com', 'password': 'testpass'},
            format='json'
        )
        self.token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

        url = reverse('project_item-get-selection-options', args=[self.project.id, self.project_item_1.id])
        self.url = url + "?selection_type=shock_selection"

    def test_simple_request(self):
        response = self.client.post(self.url, format='json')
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_all_selection_scenarios(self):
        test_cases = [
            ("Успешный подбор без длины",
             {"load": 14, "move": 100, "load_type": "h", "installation_length": None, "shock_counts": 1,
              "location": "horizontal"}, 200),
            ("С длиной и регулировкой штока",
             {"load": 14, "move": -40, "load_type": "h", "installation_length": 320, "shock_counts": 1,
              "location": "horizontal"}, 200),
            ("Вертикальная труба",
             {"load": 80, "move": 200, "load_type": "h", "installation_length": None, "shock_counts": 2,
              "location": "vertical"}, 200),
            ("Неудачный подбор (ход мал)",
             {"load": 305, "move": 400, "load_type": "hs", "installation_length": None, "shock_counts": 1,
              "location": "horizontal"}, 200),
            ("HZ нагрузка",
             {"load": 67.5, "move": 100, "load_type": "hz", "installation_length": None, "shock_counts": 1,
              "location": "horizontal"}, 200),
            ("С удлинителем (тип 2)",
             {"load": 45, "move": 200, "load_type": "h", "installation_length": 1250, "shock_counts": 1,
              "location": "horizontal"}, 200),
            ("Ошибка (недопустимая нагрузка)",
             {"load": -10, "move": 0, "load_type": "h", "installation_length": None, "shock_counts": 1,
              "location": "horizontal"}, 200),
            ("С креплениями нижнего и верхнего креплений",
             {"load": 40, "move": 200, "load_type": "h", "installation_length": 1250, "shock_counts": 2,
              "location": "horizontal", "material": 1, "pipe_diameter": 102, "mounting_group_bottom": 1,
              "mounting_group_top": 2, "pipe_clamp_a": 100, "pipe_clamp_b": 200}, 200),

            ("Без креплений",
             {"load": 45, "move": 130, "load_type": "h", "installation_length": None, "shock_counts": 1,
              "location": "horizontal"}, 200),
        ]

        for name, data, expected_status in test_cases:
            with self.subTest(name=name):
                payload = {
                    "product_class": self.family.product_class.id,
                    "product_family": self.family.id,
                    "load_and_move": {
                        "load": data["load"],
                        "move": data["move"],
                        "load_type": data["load_type"],
                        "installation_length": data["installation_length"],
                    },
                    "pipe_options": {
                        "shock_counts": data["shock_counts"],
                        "location": data["location"],
                    },
                    "pipe_params": {
                        "pipe_diameter": data.get("pipe_diameter"),
                        "pipe_diameter_size_manual": None,
                        "support_distance": data.get("support_distance"),
                        "support_distance_manual": None,
                        "mounting_group_bottom": data.get("mounting_group_bottom"),
                        "mounting_group_top": data.get("mounting_group_top"),
                        "material": data.get("material"),
                        "temperature": data.get("temperature"),
                    },
                    "pipe_clamp": {
                        "pipe_clamp_a": data.get("pipe_clamp_a"),
                        "pipe_clamp_b": data.get("pipe_clamp_b"),
                    },
                    "variant": None,
                }

                response = self.client.post(self.url, payload, format='json')
                self.assertEqual(response.status_code, expected_status, msg=f"Failed: {name}")
                print(f"\n{name}:\n{response.data}")

