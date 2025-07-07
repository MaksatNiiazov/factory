from django.test import TestCase
from django.contrib.auth import get_user_model

from catalog.choices import Standard
from catalog.models import (
    ProductFamily,
    ProductClass,
    SupportDistance,
    Material,
    PipeDiameter,
    NominalDiameter,
    PipeMountingRule,
    PipeMountingGroup,
)
from ops.choices import (
    LoadUnit,
    MoveUnit,
    TemperatureUnit,
)
from ops.models import BaseComposition, FieldSet, ProjectItem, DetailType, Variant, Item, Project, Attribute
from ops.services.shock_selection import ShockSelectionAvailableOptions
from ops.choices import AttributeType, AttributeUsageChoices

User = get_user_model()


class CalculateShockTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        self.product_class = ProductClass.objects.create(name="SSB-Класс")
        self.family = ProductFamily.objects.create(
            name="SSB", product_class=self.product_class, is_upper_mount_selectable=True
        )

        self.detail_type = DetailType.objects.create(
            name="Тип SSB",
            designation="SSB",
            category="product",
            product_family=self.family,
        )
        self.detail_type_assembly_unit = DetailType.objects.create(
            name="Тип SSB (Assembly Unit)",
            designation="SSB",
            category="assembly_unit",
            product_family=self.family,
        )
        self.detail_type_clamp = DetailType.objects.create(
            name="Хомут",
            designation="HDH",
            category="assembly_unit",
            product_family=self.family,
        )
        self.detail_type_clamp_2 = DetailType.objects.create(
            name="Хомут 2",
            designation="HDI",
            category="assembly_unit",
            product_family=self.family,
        )

        self.variant = Variant.objects.create(
            name="Вариант A", detail_type=self.detail_type
        )
        self.variant_assembly_unit = Variant.objects.create(
            name="Вариант B", detail_type=self.detail_type_assembly_unit
        )
        self.variant_clamp = Variant.objects.create(
            name="Вариант C", detail_type=self.detail_type_clamp
        )
        self.variant_clamp_2 = Variant.objects.create(
            name="Вариант D", detail_type=self.detail_type_clamp_2
        )

        # Создание базовой композиции для self.variant
        self.base_composition = BaseComposition.objects.create(
            base_parent=self.detail_type,
            base_parent_variant=self.variant,
            base_child=self.detail_type_assembly_unit,
            base_child_variant=self.variant_assembly_unit,
            position=1,
            count=2,
        )
        self.base_composition_1 = BaseComposition.objects.create(
            base_parent=self.detail_type,
            base_parent_variant=self.variant,
            base_child=self.detail_type_clamp,
            base_child_variant=self.variant_clamp,
            position=2,
            count=1,
        )
        self.base_composition_2 = BaseComposition.objects.create(
            base_parent=self.detail_type,
            base_parent_variant=self.variant,
            base_child=self.detail_type_clamp_2,
            base_child_variant=self.variant_clamp_2,
            position=3,
            count=1,
        )

        fieldset = FieldSet.objects.create(
            name="Main",
        )

        Attribute.objects.create(
            variant=self.variant,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.INSTALLATION_SIZE,
            name="installation_size",
            label_ru="Монтажный размер",
            calculated_value="<assembly_unit_SSB>.installation_size + <assembly_unit_HDH>.installation_size + <assembly_unit_HDI>.installation_size",
            is_required=True,
            fieldset=fieldset,
            position=1,
        )

        Attribute.objects.create(
            variant=self.variant_assembly_unit,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.INSTALLATION_SIZE,
            name="installation_size",
            label_ru="Монтажный размер",
            is_required=True,
            fieldset=fieldset,
            position=1,
        )
        Attribute.objects.create(
            variant=self.variant_assembly_unit,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.LOAD,
            name="load",
            label_ru="Нагрузка",
            is_required=True,
            fieldset=fieldset,
            position=2,
        )
        Attribute.objects.create(
            variant=self.variant_assembly_unit,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.RATED_STROKE,
            name="rated_stroke",
            label_ru="Номинальный ход",
            is_required=True,
            fieldset=fieldset,
            position=3,
        )

        Attribute.objects.create(
            variant=self.variant_clamp,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.INSTALLATION_SIZE,
            name="installation_size",
            label_ru="Монтажный размер",
            is_required=True,
            fieldset=fieldset,
            position=1,
        )

        Attribute.objects.create(
            variant=self.variant_clamp_2,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.INSTALLATION_SIZE,
            name="installation_size",
            label_ru="Монтажный размер",
            is_required=True,
            fieldset=fieldset,
            position=1,
        )

        # Группа креплений + связь с вариантом
        self.mounting_group = PipeMountingGroup.objects.create(name="Группа A")
        self.mounting_group.variants.add(self.variant_clamp)

        self.mounting_group_2 = PipeMountingGroup.objects.create(name="Группа B")
        self.mounting_group_2.variants.add(self.variant_clamp_2)

        # Правило выбора, связанное с группой
        self.rule = PipeMountingRule.objects.create(
            family=self.family, num_spring_blocks=2, pipe_direction="x"
        )
        self.rule.pipe_mounting_groups.add(self.mounting_group)
        self.rule.mounting_groups_b.add(self.mounting_group_2)

        # Диаметры
        self.nominal_diameter = NominalDiameter.objects.create(dn=199)
        self.pipe_diameter = PipeDiameter.objects.create(
            dn=self.nominal_diameter, standard=Standard.RF, size=150.0
        )
        self.support_distance = SupportDistance.objects.create(name="2м", value=2000)
        self.material = Material.objects.create(name="Сталь AISI", group="Сталь")

        self.project = Project.objects.create(
            number="PRJ-001",
            owner=self.user,
            load_unit=LoadUnit.KN,
            move_unit=MoveUnit.MM,
            temperature_unit=TemperatureUnit.CELSIUS,
            standard=Standard.RF,
        )

        self.shock = Item.objects.create(
            type=self.detail_type_assembly_unit,
            variant=self.variant_assembly_unit,
            name="SSB (Assembly Unit)",
            parameters={
                "load": 45,
                "rated_stroke": 200,
                "installation_size": 250,
            },
            author=self.user,
        )

        # Крепления с installation_size
        self.clamp_a = Item.objects.create(
            type=self.detail_type_clamp,
            variant=self.variant_clamp,
            name="Крепление A",
            parameters={"installation_size": 250},
            author=self.user,
        )
        self.clamp_b = Item.objects.create(
            type=self.detail_type_clamp_2,
            variant=self.variant_clamp_2,
            name="Крепление B",
            parameters={"installation_size": 250},
            author=self.user,
        )

        # ProjectItem с нужными параметрами подбора
        self.project_item = ProjectItem.objects.create(
            project=self.project,
            selection_params={
                "product_class": self.product_class.id,
                "product_family": self.family.id,
                "load_and_move": {
                    "installation_length": 1072,
                    "load": 45,
                    "load_type": "h",
                    "move": 200
                },
                "pipe_options": {
                    "location": "horizontal",
                    "shock_counts": 2,
                    "direction": "x",
                },
                "pipe_params": {
                    "temperature": 120,
                    "pipe_diameter": self.pipe_diameter.id,
                    "pipe_diameter_size_manual": None,
                    "support_distance": self.support_distance.id,
                    "support_distance_manual": None,
                    "mounting_group_a": self.mounting_group.id,
                    "mounting_group_b": self.mounting_group_2.id,
                    "material": self.material.id,
                },
                "pipe_clamp": {
                    "pipe_clamp_a": self.clamp_a.id,
                    "pipe_clamp_b": self.clamp_b.id,
                },
                "variant": None,
            },
        )

    def test_get_pipe_clamps_a(self):
        """
        Проверяет, что get_available_pipe_clamps_a() возвращает clamp_a.
        """
        selector = ShockSelectionAvailableOptions(self.project_item)
        items = selector.get_available_pipe_clamps_a()

        self.assertTrue(items, msg="Список креплений A пуст")
        self.assertIn(self.clamp_a.id, items.values_list("id", flat=True))

    def test_get_pipe_clamps_b(self):
        """
        Проверяет, что метод get_available_pipe_clamps_b возвращает clamp_b.
        """
        selector = ShockSelectionAvailableOptions(self.project_item)
        items = selector.get_available_pipe_clamps_b()

        self.assertTrue(items, msg="Список креплений B пуст")
        self.assertIn(self.clamp_b.id, items.values_list("id", flat=True))

    def test_get_load_with_valid_load_and_type_hz(self):
        """
        Проверяет корректность вычисления нагрузки при типе 'hz'.
        """
        self.project_item.selection_params["load_and_move"]["load"] = 90
        self.project_item.selection_params["load_and_move"]["load_type"] = "hz"
        self.project_item.selection_params["pipe_options"]["shock_counts"] = 1

        selector = ShockSelectionAvailableOptions(self.project_item)
        load = selector.get_load()

        self.assertEqual(
            load, 60.0, msg="Нагрузка при типе 'hz' должна быть делена на 1.5"
        )

    def test_get_load_with_valid_load_and_type_hs(self):
        """
        Проверяет корректность вычисления нагрузки при типе 'hs'.
        """
        self.project_item.selection_params["load_and_move"]["load"] = 85
        self.project_item.selection_params["load_and_move"]["load_type"] = "hs"
        self.project_item.selection_params["pipe_options"]["shock_counts"] = 1

        selector = ShockSelectionAvailableOptions(self.project_item)
        load = selector.get_load()

        self.assertEqual(
            load, 50.0, msg="Нагрузка при типе 'hs' должна быть делена на 1.7"
        )

    def test_get_load_with_missing_load_type(self):
        """
        Проверяет, что метод возвращает None, если тип нагрузки не указан.
        """
        self.project_item.selection_params["load_and_move"]["load"] = 100
        self.project_item.selection_params["load_and_move"]["load_type"] = None

        selector = ShockSelectionAvailableOptions(self.project_item)
        load = selector.get_load()

        self.assertIsNone(
            load, msg="Нагрузка должна быть None, если тип нагрузки не указан"
        )
        self.assertIn("Не указан тип нагрузки.", selector.debug)

    def test_get_load_with_missing_load_value(self):
        """
        Проверяет, что метод возвращает None, если значение нагрузки не указано.
        """
        self.project_item.selection_params["load_and_move"]["load"] = None
        self.project_item.selection_params["load_and_move"]["load_type"] = "h"

        selector = ShockSelectionAvailableOptions(self.project_item)
        load = selector.get_load()

        self.assertIsNone(
            load, msg="Нагрузка должна быть None, если значение нагрузки не указано"
        )
        self.assertIn("Не указан нагрузка.", selector.debug)

    def test_get_load_with_invalid_load_type(self):
        """
        Проверяет, что метод возвращает исходное значение нагрузки, если тип нагрузки некорректен.
        """
        self.project_item.selection_params["load_and_move"]["load"] = 100
        self.project_item.selection_params["load_and_move"][
            "load_type"
        ] = "invalid_type"
        self.project_item.selection_params["pipe_options"]["shock_counts"] = 1

        selector = ShockSelectionAvailableOptions(self.project_item)
        load = selector.get_load()

        self.assertEqual(
            load,
            100,
            msg="Нагрузка должна быть возвращена без изменений при некорректном типе нагрузки",
        )

    def test_get_available_mounting_groups_a_with_valid_data(self):
        """
        Проверяет, что get_available_mounting_groups_a возвращает корректные группы креплений A.
        """
        selector = ShockSelectionAvailableOptions(self.project_item)
        groups = selector.get_available_mounting_groups_a()

        self.assertTrue(groups.exists(), msg="Список групп креплений A пуст")
        self.assertIn(self.mounting_group.id, groups.values_list("id", flat=True))

    def test_get_available_mounting_groups_a_without_product_family(self):
        """
        Проверяет, что get_available_mounting_groups_a возвращает пустой QuerySet,
        если семейство изделия не выбрано.
        """
        self.project_item.selection_params["product_family"] = None
        selector = ShockSelectionAvailableOptions(self.project_item)
        groups = selector.get_available_mounting_groups_a()

        self.assertFalse(groups.exists(), msg="Список групп креплений A должен быть пуст")
        self.assertIn(
            "#Тип крепления A: Не выбран семейство изделии", selector.debug
        )

    def test_get_available_mounting_groups_a_without_shock_counts(self):
        """
        Проверяет, что get_available_mounting_groups_a добавляет сообщение в debug,
        если количество амортизаторов не выбрано.
        """
        self.project_item.selection_params["pipe_options"]["shock_counts"] = None
        selector = ShockSelectionAvailableOptions(self.project_item)
        groups = selector.get_available_mounting_groups_a()

        self.assertFalse(groups.exists(), msg="Список групп креплений A должен быть пуст")
        self.assertIn(
            "#Тип крепления A: Не выбран количество амортизаторов", selector.debug
        )

    def test_get_available_mounting_groups_a_without_pipe_direction(self):
        """
        Проверяет, что get_available_mounting_groups_a возвращает пустой QuerySet,
        если направление трубы не выбрано.
        """
        self.project_item.selection_params["pipe_options"]["location"] = None
        selector = ShockSelectionAvailableOptions(self.project_item)
        groups = selector.get_available_mounting_groups_a()

        self.assertFalse(groups.exists(), msg="Список групп креплений A должен быть пуст")
        self.assertIn(
            "#Тип крепления A: Не выбран направление трубы", selector.debug
        )

    def test_get_available_mounting_groups_a_without_rules(self):
        """
        Проверяет, что get_available_mounting_groups_a возвращает пустой QuerySet,
        если правила выбора креплений отсутствуют.
        """
        self.project_item.selection_params["pipe_options"]["shock_counts"] = 99  # Некорректное значение
        selector = ShockSelectionAvailableOptions(self.project_item)
        groups = selector.get_available_mounting_groups_a()

        self.assertFalse(groups.exists(), msg="Список групп креплений A должен быть пуст")
        self.assertIn(
            "#Тип крепления A: Отсутствует \"Правила выбора крепления\".", selector.debug
        )

    def test_get_available_mounting_groups_b_without_product_family(self):
        """
        Проверяет, что get_available_mounting_groups_b возвращает пустой QuerySet,
        если семейство изделия не выбрано.
        """
        self.project_item.selection_params["product_family"] = None
        selector = ShockSelectionAvailableOptions(self.project_item)
        groups = selector.get_available_mounting_groups_b()

        self.assertFalse(groups.exists(), msg="Список групп креплений B должен быть пуст")
        self.assertIn(
            "#Тип крепления B: Не выбран семейство изделии", selector.debug
        )

    def test_get_available_mounting_groups_b_without_upper_mount_selectable(self):
        """
        Проверяет, что get_available_mounting_groups_b возвращает пустой QuerySet,
        если семейство изделия не поддерживает верхнее крепление.
        """
        self.family.is_upper_mount_selectable = False
        self.family.save()

        selector = ShockSelectionAvailableOptions(self.project_item)
        groups = selector.get_available_mounting_groups_b()

        self.assertFalse(groups.exists(), msg="Список групп креплений B должен быть пуст")
        self.assertIn(
            "#Тип крепления B: Должен быть выбран \"Доступен выбор верхнего крепления\" в семейство изделии",
            selector.debug,
        )

    def test_get_available_mounting_groups_b_without_shock_counts(self):
        """
        Проверяет, что get_available_mounting_groups_b добавляет сообщение в debug,
        если количество амортизаторов не выбрано.
        """
        self.project_item.selection_params["pipe_options"]["shock_counts"] = None
        selector = ShockSelectionAvailableOptions(self.project_item)
        groups = selector.get_available_mounting_groups_b()

        self.assertFalse(groups.exists(), msg="Список групп креплений B должен быть пуст")
        self.assertIn(
            "#Тип крепления B: Не выбран количество амортизаторов", selector.debug
        )

    def test_get_available_mounting_groups_b_without_pipe_location(self):
        """
        Проверяет, что get_available_mounting_groups_b возвращает пустой QuerySet,
        если направление трубы не выбрано.
        """
        self.project_item.selection_params["pipe_options"]["location"] = None
        selector = ShockSelectionAvailableOptions(self.project_item)
        groups = selector.get_available_mounting_groups_b()

        self.assertFalse(groups.exists(), msg="Список групп креплений B должен быть пуст")
        self.assertIn(
            "#Тип крепления B: Не выбран направление трубы", selector.debug
        )

    def test_get_available_mounting_groups_b_without_rules(self):
        """
        Проверяет, что get_available_mounting_groups_b возвращает пустой QuerySet,
        если правила выбора креплений отсутствуют.
        """
        self.project_item.selection_params["pipe_options"]["shock_counts"] = 99  # Некорректное значение
        selector = ShockSelectionAvailableOptions(self.project_item)
        groups = selector.get_available_mounting_groups_b()

        self.assertFalse(groups.exists(), msg="Список групп креплений B должен быть пуст")
        self.assertIn(
            "#Тип крепления B: Отсутствует \"Правила выбора крепления\".", selector.debug
        )

    def test_get_available_options_with_valid_data(self):
        """
        Проверяет, что get_available_options возвращает корректные доступные параметры.
        """
        selector = ShockSelectionAvailableOptions(self.project_item)
        options = selector.get_available_options()

        self.assertIn("debug", options, msg="Отсутствует ключ 'debug' в результатах.")
        self.assertIn("load_and_move", options, msg="Отсутствует ключ 'load_and_move' в результатах.")
        self.assertIn("pipe_options", options, msg="Отсутствует ключ 'pipe_options' в результатах.")
        self.assertIn("pipe_params", options, msg="Отсутствует ключ 'pipe_params' в результатах.")
        self.assertIn("pipe_clamp", options, msg="Отсутствует ключ 'pipe_clamp' в результатах.")
        self.assertIn("suitable_variant", options, msg="Отсутствует ключ 'suitable_variant' в результатах.")
        self.assertIn("specifications", options, msg="Отсутствует ключ 'specifications' в результатах.")

        self.assertIn("load_types", options["load_and_move"], msg="Отсутствует ключ 'load_types' в 'load_and_move'.")
        self.assertIn("locations", options["pipe_options"], msg="Отсутствует ключ 'locations' в 'pipe_options'.")
        self.assertIn("shock_counts", options["pipe_options"], msg="Отсутствует ключ 'shock_counts' в 'pipe_options'.")
        self.assertIn("pipe_diameters", options["pipe_params"], msg="Отсутствует ключ 'pipe_diameters' в 'pipe_params'.")
        self.assertIn("support_distances", options["pipe_params"], msg="Отсутствует ключ 'support_distances' в 'pipe_params'.")
        self.assertIn("mounting_groups_a", options["pipe_params"], msg="Отсутствует ключ 'mounting_groups_a' в 'pipe_params'.")
        self.assertIn("mounting_groups_b", options["pipe_params"], msg="Отсутствует ключ 'mounting_groups_b' в 'pipe_params'.")
        self.assertIn("materials", options["pipe_params"], msg="Отсутствует ключ 'materials' в 'pipe_params'.")
        self.assertIn("pipe_clamps_a", options["pipe_clamp"], msg="Отсутствует ключ 'pipe_clamps_a' в 'pipe_clamp'.")
        self.assertIn("pipe_clamps_b", options["pipe_clamp"], msg="Отсутствует ключ 'pipe_clamps_b' в 'pipe_clamp'.")

    def test_get_available_options_with_missing_data(self):
        """
        Проверяет, что get_available_options корректно обрабатывает отсутствующие данные.
        """
        self.project_item.selection_params["product_family"] = None
        self.project_item.selection_params["pipe_options"]["shock_counts"] = None
        self.project_item.selection_params["pipe_options"]["location"] = None

        selector = ShockSelectionAvailableOptions(self.project_item)
        options = selector.get_available_options()

        self.assertFalse(options["pipe_params"]["mounting_groups_a"], msg="Список 'mounting_groups_a' должен быть пуст.")
        self.assertFalse(options["pipe_params"]["mounting_groups_b"], msg="Список 'mounting_groups_b' должен быть пуст.")
        self.assertFalse(options["pipe_clamp"]["pipe_clamps_a"], msg="Список 'pipe_clamps_a' должен быть пуст.")
        self.assertFalse(options["pipe_clamp"]["pipe_clamps_b"], msg="Список 'pipe_clamps_b' должен быть пуст.")
        self.assertIn("#Тип крепления A: Не выбран семейство изделии", selector.debug, msg="Отсутствует сообщение в debug.")
        self.assertIn("#Тип крепления B: Не выбран семейство изделии", selector.debug, msg="Отсутствует сообщение в debug.")

    def test_get_load_with_multiple_shock_counts(self):
        """
        Проверяет корректность вычисления нагрузки при наличии нескольких амортизаторов.
        """
        self.project_item.selection_params["load_and_move"]["load"] = 90
        self.project_item.selection_params["load_and_move"]["load_type"] = "hz"
        self.project_item.selection_params["pipe_options"]["shock_counts"] = 2

        selector = ShockSelectionAvailableOptions(self.project_item)
        load = selector.get_load()

        self.assertEqual(
            load, 30.0, msg="Нагрузка должна быть делена на 1.5 и на количество амортизаторов"
        )

    def test_get_load_with_single_shock_count(self):
        """
        Проверяет корректность вычисления нагрузки при наличии одного амортизатора.
        """
        self.project_item.selection_params["load_and_move"]["load"] = 90
        self.project_item.selection_params["load_and_move"]["load_type"] = "hz"
        self.project_item.selection_params["pipe_options"]["shock_counts"] = 1

        selector = ShockSelectionAvailableOptions(self.project_item)
        load = selector.get_load()

        self.assertEqual(
            load, 60.0, msg="Нагрузка должна быть делена только на 1.5 при одном амортизаторе"
        )

    def test_get_load_with_no_shock_counts(self):
        """
        Проверяет корректность вычисления нагрузки при отсутствии количества амортизаторов.
        """
        self.project_item.selection_params["load_and_move"]["load"] = 90
        self.project_item.selection_params["load_and_move"]["load_type"] = "hz"
        self.project_item.selection_params["pipe_options"]["shock_counts"] = None

        selector = ShockSelectionAvailableOptions(self.project_item)
        load = selector.get_load()

        self.assertEqual(
            load, 60.0, msg="Нагрузка должна быть делена только на 1.5 при отсутствии количества амортизаторов"
        )

    def test_get_load_with_zero_shock_counts(self):
        """
        Проверяет корректность вычисления нагрузки при количестве амортизаторов равном нулю.
        """
        self.project_item.selection_params["load_and_move"]["load"] = 90
        self.project_item.selection_params["load_and_move"]["load_type"] = "hz"
        self.project_item.selection_params["pipe_options"]["shock_counts"] = 0

        selector = ShockSelectionAvailableOptions(self.project_item)
        load = selector.get_load()

        self.assertEqual(
            load, 60.0, msg="Нагрузка должна быть делена только на 1.5 при количестве амортизаторов равном нулю"
        )

    def test_get_suitable_variant_with_missing_pipe_clamp_a(self):
        """
        Проверяет, что get_suitable_variant возвращает None, если крепление A отсутствует.
        """
        self.project_item.selection_params["pipe_clamp"]["pipe_clamp_a"] = None
        self.project_item.selection_params["pipe_clamp"]["pipe_clamp_b"] = self.clamp_b.id
        self.project_item.selection_params["load_and_move"]["load"] = 90
        self.project_item.selection_params["load_and_move"]["load_type"] = "hz"
        self.project_item.selection_params["pipe_options"]["shock_counts"] = 1

        selector = ShockSelectionAvailableOptions(self.project_item)
        variant = selector.get_suitable_variant()

        self.assertIsNone(variant, msg="Вариант изделия должен быть None при отсутствии крепления A.")
        self.assertIn("#Поиск исполнения изделия: Не выбран крепление A.", selector.debug)

    def test_get_suitable_variant_with_missing_load(self):
        """
        Проверяет, что get_suitable_variant возвращает None, если нагрузка отсутствует.
        """
        self.project_item.selection_params["pipe_clamp"]["pipe_clamp_a"] = self.clamp_a.id
        self.project_item.selection_params["pipe_clamp"]["pipe_clamp_b"] = self.clamp_b.id
        self.project_item.selection_params["load_and_move"]["load"] = None
        self.project_item.selection_params["load_and_move"]["load_type"] = "hz"
        self.project_item.selection_params["pipe_options"]["shock_counts"] = 1

        selector = ShockSelectionAvailableOptions(self.project_item)
        variant = selector.get_suitable_variant()

        self.assertIsNone(variant, msg="Вариант изделия должен быть None при отсутствии нагрузки.")
        self.assertIn("Не задана нагрузка для поиска исполнения изделия.", selector.debug)

    def test_get_suitable_variant_with_missing_sn_margin(self):
        """
        Проверяет, что get_suitable_variant возвращает None, если SN margin отсутствует.
        """
        self.project_item.selection_params["pipe_clamp"]["pipe_clamp_a"] = self.clamp_a.id
        self.project_item.selection_params["pipe_clamp"]["pipe_clamp_b"] = self.clamp_b.id
        self.project_item.selection_params["load_and_move"]["load"] = 90
        self.project_item.selection_params["load_and_move"]["load_type"] = "hz"
        self.project_item.selection_params["pipe_options"]["shock_counts"] = 1
        self.project_item.selection_params["load_and_move"]["move"] = None  # SN margin зависит от move

        selector = ShockSelectionAvailableOptions(self.project_item)
        variant = selector.get_suitable_variant()

        self.assertIsNone(variant, msg="Вариант изделия должен быть None при отсутствии SN margin.")
        self.assertIn("Не задан SN margin для поиска исполнения изделия.", selector.debug)

    def test_get_suitable_variant_with_no_candidates(self):
        """
        Проверяет, что get_suitable_variant возвращает None, если нет подходящих кандидатов.
        """
        self.project_item.selection_params["pipe_clamp"]["pipe_clamp_a"] = self.clamp_a.id
        self.project_item.selection_params["pipe_clamp"]["pipe_clamp_b"] = self.clamp_b.id
        self.project_item.selection_params["load_and_move"]["load"] = 1000  # Нагрузка слишком большая
        self.project_item.selection_params["load_and_move"]["load_type"] = "hz"
        self.project_item.selection_params["pipe_options"]["shock_counts"] = 1

        selector = ShockSelectionAvailableOptions(self.project_item)
        variant = selector.get_suitable_variant()

        self.assertIsNone(variant, msg="Вариант изделия должен быть None при отсутствии подходящих кандидатов.")
        self.assertIn("Не найдено подходящих исполнений для всех вариантов нагрузки.", selector.debug)

    def test_get_available_mounting_groups_a_with_horizontal_pipe_direction(self):
        """
        Проверяет, что get_available_mounting_groups_a возвращает корректные группы креплений A
        при горизонтальном направлении трубы.
        """
        self.project_item.selection_params["pipe_options"]["direction"] = "x"
        self.project_item.selection_params["pipe_options"]["location"] = "horizontal"
        selector = ShockSelectionAvailableOptions(self.project_item)
        groups = selector.get_available_mounting_groups_a()

        self.assertTrue(groups.exists(), msg="Список групп креплений A пуст")
        self.assertIn(self.mounting_group.id, groups.values_list("id", flat=True))

    def test_get_available_mounting_groups_a_with_vertical_pipe_direction(self):
        """
        Проверяет, что get_available_mounting_groups_a возвращает корректные группы креплений A
        при вертикальном направлении трубы.
        """
        rule = PipeMountingRule.objects.create(
            family=self.family, num_spring_blocks=2, pipe_direction="z"
        )
        rule.pipe_mounting_groups.add(self.mounting_group)
        self.rule.pipe_mounting_groups.add(self.mounting_group)
        self.rule.mounting_groups_b.add(self.mounting_group_2)
        self.project_item.selection_params["pipe_options"]["location"] = "vertical"
        selector = ShockSelectionAvailableOptions(self.project_item)
        groups = selector.get_available_mounting_groups_a()

        self.assertTrue(groups.exists(), msg="Список групп креплений A пуст")
        self.assertIn(self.mounting_group.id, groups.values_list("id", flat=True))

    def test_get_available_mounting_groups_a_with_invalid_pipe_location(self):
        """
        Проверяет, что get_available_mounting_groups_a возвращает пустой QuerySet,
        если направление трубы некорректно.
        """
        self.project_item.selection_params["pipe_options"]["location"] = "invalid_direction"
        selector = ShockSelectionAvailableOptions(self.project_item)
        groups = selector.get_available_mounting_groups_a()

        self.assertFalse(groups.exists(), msg="Список групп креплений A должен быть пуст")
        self.assertIn(
            "#Тип крепления A: Неверное направление трубы.", selector.debug
        )

    def test_get_available_mounting_groups_a_with_missing_pipe_location(self):
        """
        Проверяет, что get_available_mounting_groups_a возвращает пустой QuerySet,
        если расположение трубы не указано.
        """
        self.project_item.selection_params["pipe_options"]["location"] = None
        selector = ShockSelectionAvailableOptions(self.project_item)
        groups = selector.get_available_mounting_groups_a()

        self.assertFalse(groups.exists(), msg="Список групп креплений A должен быть пуст")
        self.assertIn(
            "#Тип крепления A: Не выбран направление трубы", selector.debug
        )

    def test_get_available_mounting_groups_a_with_no_matching_rules(self):
        """
        Проверяет, что get_available_mounting_groups_a возвращает пустой QuerySet,
        если правила выбора креплений отсутствуют.
        """
        self.project_item.selection_params["pipe_options"]["shock_counts"] = 99  # Некорректное значение
        selector = ShockSelectionAvailableOptions(self.project_item)
        groups = selector.get_available_mounting_groups_a()

        self.assertFalse(groups.exists(), msg="Список групп креплений A должен быть пуст")
        self.assertIn(
            "#Тип крепления A: Отсутствует \"Правила выбора крепления\".", selector.debug
        )