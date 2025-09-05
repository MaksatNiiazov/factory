from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase
from rest_framework import status

from catalog.models import ProductClass, ProductFamily

from ops import models as opsmodels
from ops.models import BaseComposition

User = get_user_model()


class WVDSelectionAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(email="testuser@example.com", password="testpass")

        self.prod_class = ProductClass.objects.create(name="TestClass")
        self.family = ProductFamily.objects.create(product_class=self.prod_class, name="WVD Family")

        # DetailType
        # само изделие для исполнения
        self.product_detail = opsmodels.DetailType.objects.create(
            product_family=self.family,
            name="WVD Product",
            designation="WVD",
            category=opsmodels.DetailType.PRODUCT
        )
        print("product_detail", self.product_detail.id)

        # DetailType
        # тот СБЕ который можно выбрать
        self.detail = opsmodels.DetailType.objects.create(
            product_family=self.family,
            name="WVD Product",
            designation="WVD",
            category=opsmodels.DetailType.ASSEMBLY_UNIT
        )
        print("detail", self.detail.id)

        # Исполнение
        self.variant = opsmodels.Variant.objects.create(
            detail_type=self.product_detail,
            name="WVD",
            marking_template="WVD {{ Fv|int|zfill(4) }}.{{ Sv|int|zfill(3) }} ({{ inner_id }})",
            sketch=None,
            sketch_coords=[{"x": 875.0091796875001, "y": 1622.2050000000002, "id": 1685, "rotation": 270, "draggableId": "fd59ee00-8125-4e71-96c2-e43c1c3c1264"}, {"x": 2626.6454296875004, "y": 6273.1012500000015, "id": 1687, "rotation": 0, "draggableId": "298a1a51-2b35-42af-b600-12618e4ec9e1"}, {"x": 797.3504296875001, "y": 5815.7775, "id": 1691, "rotation": 0, "draggableId": "bb1ffad3-8364-42b7-8668-0ee901112560"}, {"x": 2652.5316796875, "y": 293.37750000000005, "id": 1589, "rotation": 0, "draggableId": "e92afd26-2275-47ec-828f-f0f528b948fb"}, {"x": 2678.4179296875, "y": 2381.5350000000003, "id": 1684, "rotation": 0, "draggableId": "562b9ebe-d8ee-48a5-84db-9646005a1a63"}, {"x": 2637.02689453125, "y": 2623.1400000000003, "id": 1589, "rotation": 0, "draggableId": "da7434aa-4737-4820-a498-c801584e5aba"}, {"x": 902.6481445312501, "y": 1311.57, "id": 1686, "rotation": 270, "draggableId": "a1d5203d-961a-4895-9a86-5a91913e7a6d"}],
        )

        # Item
        self.item1 = opsmodels.Item.objects.create(
            type=self.detail,
            variant=self.variant,
            author=self.user,
            parameters={
                "A": 646.0,
                "B": 542.0,
                "E": 556.0,
                "d": 60.0,
                "m": 685.0,
                "s": 35.0,
                "A1": 6.0,
                "B1": 5.0,
                "E1": 5.0,
                "Fh": 350.0,
                "Fv": 140.0,
                "Sa": 11.0,
                "Sh": 72.0,
                "Sv": 74.0,
                "d1": 3.0,
                "s1": 1.0
            }
        )
        print("item1", self.item1.id)
        self.item2 = opsmodels.Item.objects.create(
            type=self.detail,
            variant=self.variant,
            author=self.user,
            parameters={
                "A": 646.0,
                "B": 542.0,
                "E": 556.0,
                "d": 60.0,
                "m": 579.0,
                "s": 35.0,
                "A1": 6.0,
                "B1": 5.0,
                "E1": 5.0,
                "Fh": 260.0,
                "Fv": 100.0,
                "Sa": 11.0,
                "Sh": 122.0,
                "Sv": 74.0,
                "d1": 3.0,
                "s1": 1.0
            }
        )
        print("item2", self.item2.id)
        self.item3 = opsmodels.Item.objects.create(
            type=self.detail,
            variant=self.variant,
            author=self.user,
            parameters={
                "A": 434.0,
                "B": 368.0,
                "E": 378.0,
                "d": 39.0,
                "m": 190.0,
                "s": 25.0,
                "A1": 4.0,
                "B1": 4.0,
                "E1": 4.0,
                "Fh": 120.0,
                "Fv": 47.0,
                "Sa": 18.0,
                "Sh": 78.0,
                "Sv": 45.0,
                "d1": 3.0,
                "s1": 1.0
            }
        )
        print("item3", self.item3.id)
        self.item4 = opsmodels.Item.objects.create(
            type=self.detail,
            variant=self.variant,
            author=self.user,
            parameters={
                "A": 342.0,
                "B": 286.0,
                "E": 333.0,
                "d": 33.0,
                "m": 113.0,
                "s": 20.0,
                "A1": 3.0,
                "B1": 3.0,
                "E1": 3.0,
                "Fh": 45.0,
                "Fv": 25.0,
                "Sa": 9.0,
                "Sh": 34.0,
                "Sv": 40.0,
                "d1": 2.0,
                "s1": 1.0
            }
        )
        print("item4", self.item4.id)
        # изделие
        self.item_main = opsmodels.Item.objects.create(
            type=self.product_detail,
            variant=self.variant,
            author=self.user,
            parameters={
                "A": 342.0,
                "B": 286.0,
                "E": 333.0,
                "d": 33.0,
                "m": 113.0,
                "s": 20.0,
                "A1": 3.0,
                "B1": 3.0,
                "E1": 3.0,
                "Fh": 45.0,
                "Fv": 25.0,
                "Sa": 9.0,
                "Sh": 34.0,
                "Sv": 40.0,
                "d1": 2.0,
                "s1": 1.0
            }
        )
        print("item_main", self.item_main.id)

        # делаем базовый состав
        self.base_composition = opsmodels.BaseComposition.objects.create(
            base_parent=self.product_detail,
            base_parent_variant=self.variant,
            base_child=self.detail,
            position=1,
            count=1
        )

        # Проект
        self.project = opsmodels.Project.objects.create(
            number="P-001",
            owner=self.user,
        )

        self.project_item_1 = opsmodels.ProjectItem.objects.create(project=self.project)

        response = self.client.post(
            reverse("user-login"),
            {"username": "testuser@example.com", "password": "testpass"},
            format="json"
        )
        self.token = response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.token)

        get_params_url = reverse("project_item-selection-params", args=[self.project.id, self.project_item_1.id])
        self.get_params_url = get_params_url + "?selection_type=wvd_selection"

        set_url = reverse("project_item-set-selection", args=[self.project.id, self.project_item_1.id])
        self.set_url = set_url + "?selection_type=wvd_selection"

        get_url = reverse("project_item-get-selection-options", args=[self.project.id, self.project_item_1.id])
        self.get_url = get_url + "?selection_type=wvd_selection"

    def test_selection(self):
        response = self.client.post(
            self.set_url,
            data={
                "product_class": self.prod_class.id,
                "product_family": self.family.id,
                "load_and_move": {},
                "variant": None,
                "selected_assembly_unit": None,
            },
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.project_item_1.id)
        self.assertEqual(response.data["selection_params"]["product_class"], self.prod_class.id)
        self.assertEqual(response.data["selection_params"]["product_family"], self.family.id)

        print(">> .../set_selection/")

        # 1 сценарий: без параметров находит все 4 items
        response = self.client.post(self.get_url, format="json")
        print(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assembly_units = response.data["assembly_units"]
        self.assertTrue((
            self.item1.id in assembly_units and
            self.item2.id in assembly_units and
            self.item3.id in assembly_units and
            self.item4.id in assembly_units
        ))

        print(">> .../get_selection_options/ ALL")

        # 2 сценарий: найдено всего 2 Items
        response = self.client.post(
            self.set_url,
            data={
                "product_class": self.prod_class.id,
                "product_family": self.family.id,
                "load_and_move": {"load_plus_x": 250, "move_minus_d": 12},
                "variant": None,
                "selected_assembly_unit": None,
            },
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.project_item_1.id)
        self.assertEqual(response.data["selection_params"]["product_class"], self.prod_class.id)
        self.assertEqual(response.data["selection_params"]["product_family"], self.family.id)

        response = self.client.post(self.get_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assembly_units = response.data["assembly_units"]
        self.assertTrue((
                self.item1.id in assembly_units and
                self.item2.id in assembly_units and
                self.item3.id not in assembly_units and
                self.item4.id not in assembly_units
        ))

        # выбираем selected_assembly_unit, который не подходит по параметрам
        response = self.client.post(
            self.set_url,
            data={
                "product_class": self.prod_class.id,
                "product_family": self.family.id,
                "load_and_move": {"load_plus_x": 250, "move_minus_d": 12},
                "variant": None,
                "selected_assembly_unit": self.item4.id,
            },
            format="json"
        )
        response = self.client.post(self.get_url, format="json")
        debug = response.data["debug"]
        self.assertIn("#Инициализация: выбранный СБЕ не подходит по параметрам (selected_assembly_unit).", debug)

        # выбираем selected_assembly_unit, который подходит по параметрам
        response = self.client.post(
            self.set_url,
            data={
                "product_class": self.prod_class.id,
                "product_family": self.family.id,
                "load_and_move": {"load_plus_x": 250, "move_minus_d": 12},
                "variant": None,
                "selected_assembly_unit": self.item1.id,
            },
            format="json"
        )
        self.assertEqual(response.data["selection_params"]["selected_assembly_unit"], self.item1.id)
        # ищем исполнение и спецификацию
        response = self.client.post(self.get_url, format="json")
        self.assertEqual(response.data["suitable_variant"]["id"], self.variant.id)
        print(response.data["specification"])

    def tearDown(self):
        self.family.hard_delete()
        self.prod_class.hard_delete()
        self.item1.hard_delete()
        self.item2.hard_delete()
        self.item3.hard_delete()
        self.item4.hard_delete()
        self.item_main.hard_delete()
        self.base_composition.hard_delete()
        self.variant.hard_delete()
        self.detail.hard_delete()
        self.product_detail.hard_delete()
        self.project_item_1.hard_delete()
        self.project.hard_delete()
        self.user.delete()
