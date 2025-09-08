from django.contrib.auth import get_user_model
from django.test import TestCase

from catalog.choices import MaterialType
from catalog.models import CoveringType, LoadGroup, Material, PipeDiameter, PipeMountingGroup, ClampSelectionMatrix, ProductClass, ProductFamily

from ops.choices import AttributeCatalog, AttributeType, AttributeUsageChoices, LoadUnit, MoveUnit, ProjectStatus, TemperatureUnit
from ops.models import Attribute, DetailType, FieldSet, Item, Project, ProjectItem, Variant
from ops.services.product_selection import ProductSelectionAvailableOptions


User = get_user_model()


class ProductSelectionAvailableOptionsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpassword'
        )
        self.fieldset = FieldSet.objects.create(name='Main')
        self.material = Material.objects.create(
            name='Сталь',
            group='13',
            type=MaterialType.A,
        )
        self.pipe_diameter = PipeDiameter.objects.first()
        self.covering_type = CoveringType.objects.create(
            numeric=0,
            name='Без покрытия',
        )

        self.spring_detail_type = DetailType.objects.create(
            name='Пружинный блок',
            designation='SPR',
            category=DetailType.DETAIL,
        )
        self.spring_variant = Variant.objects.create(
            detail_type=self.spring_detail_type,
            name='SpringVariant',
        )
        self.spring_load_attribute = Attribute.objects.create(
            variant=self.spring_variant,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.LOAD,
            name='Fn',
            label_ru='Номинальная нагрузка',
            fieldset=self.fieldset,
            position=1,
        )

    def test_12x12(self):
        load_group, _ = LoadGroup.objects.get_or_create(
            lgv=12,
            defaults={
                'kn': 1,
            }
        )

        product_class = ProductClass.objects.create(
            name='ProductClass',
        )

        product_family = ProductFamily.objects.create(
            product_class=product_class,
            name='ProductFamily',
            is_upper_mount_selectable=True,
        )

        zom_detail_type = DetailType.objects.create(
            name='Рым-гайка',
            designation='ZOM',
            category=DetailType.DETAIL,
        )

        zom_lgv_attribute = Attribute.objects.create(
            detail_type=zom_detail_type,
            type=AttributeType.CATALOG,
            usage=AttributeUsageChoices.LOAD_GROUP,
            catalog=AttributeCatalog.LOAD_GROUP,
            name='LGV',
            label_ru='Нагрузочная группа',
            fieldset=self.fieldset,
            position=1,
        )

        zom_variant = Variant.objects.create(
            detail_type=zom_detail_type,
            name='1',
            marking_template='ZOM {{ LGV.lgv }} ({{ inner_id }})',
        )

        zom_item_12 = Item.objects.create(
            type=zom_detail_type,
            variant=zom_variant,
            parameters={
                'LGV': load_group.id,
            },
            author=self.user,
        )

        hzn_detail_type = DetailType.objects.create(
            name='Хомут двухболтовый',
            designation='HZN',
            category=DetailType.ASSEMBLY_UNIT,
        )

        hzn_lgv_attribute = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.CATALOG,
            usage=AttributeUsageChoices.LOAD_GROUP,
            catalog=AttributeCatalog.LOAD_GROUP,
            name='LGV',
            label_ru='Нагрузочная группа',
            fieldset=self.fieldset,
            position=1,
        )

        hzn_pipe_diameter = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.CATALOG,
            catalog=AttributeCatalog.PIPE_DIAMETER,
            name='OD',
            label_ru='Диаметр трубопровода',
            fieldset=self.fieldset,
            position=2,
        )

        hzn_material = Attribute.objects.create(
            detail_type= hzn_detail_type,
            type= AttributeType.CATALOG,
            catalog=AttributeCatalog.MATERIAL,
            name='material',
            label_ru='Материал',
            fieldset=self.fieldset,
            position=3,
        )

        hzn_load_attribute = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.LOAD,
            name='Fn',
            label_ru='Номинальная нагрузка',
            fieldset=self.fieldset,
            position=4,
        )

        hzn_clamp_load_attribute = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.CLAMP_LOAD,
            name='Fn1',
            label_ru='Нагрузка для хомутов',
            fieldset=self.fieldset,
            position=5,
        )

        hzn_covering_type = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.CATALOG,
            catalog=AttributeCatalog.COVERING_TYPE,
            name='coating',
            label_ru='Покрытие',
            fieldset=self.fieldset,
            position=6,
        )

        hzn_variant = Variant.objects.create(
            detail_type=hzn_detail_type,
            name='1',
            marking_template='HZN {{ LGV.lgv }} ({{ inner_id }})',
        )

        pipe_mounting_group = PipeMountingGroup.objects.create(
            name='Хомуты двухболтовые',
        )
        pipe_mounting_group.variants.add(hzn_variant)

        hzn_item_12 = Item.objects.create(
            type=hzn_detail_type,
            variant=hzn_variant,
            parameters={
                'LGV': load_group.id,
                'material': self.material.id,
                'OD': self.pipe_diameter.id,
                'Fn': 1000,
                'Fn1': 1000,
                'coating': self.covering_type.id,
            },
            author=self.user,
        )

        matrix = ClampSelectionMatrix.objects.create(
            product_family=product_family,
        )
        matrix.clamp_detail_types.add(hzn_detail_type)
        matrix.fastener_detail_types.add(zom_detail_type)
        matrix.entries.create(
            hanger_load_group=12,
            clamp_load_group=12,
            result="unlimited",
        )

        project = Project.objects.create(
            number='12345',
            owner=self.user,
            status=ProjectStatus.DRAFT,
            load_unit=LoadUnit.KN,
            move_unit=MoveUnit.MM,
            temperature_unit=TemperatureUnit.CELSIUS,
        )
        project_item = ProjectItem.objects.create(
            project=project,
            position_number=1,
        )
        product_selection = ProductSelectionAvailableOptions(project_item)
        product_selection.params['product_family'] = product_family.id
        product_selection.params['load_and_move']['load_minus_z'] = 500
        product_selection.params['pipe_params']['pipe_mounting_group'] = pipe_mounting_group.id
        product_selection.params['pipe_params']['clamp_material'] = self.material.id
        product_selection.params['pipe_params']['nominal_diameter'] = self.pipe_diameter.id
        product_selection.params['pipe_params']['temp1'] = 130
        product_selection.params['spring_choice']['selected_spring'] = {
            'load_group_lgv': load_group.lgv,
            'variant': self.spring_variant,
            'parameters': {self.spring_load_attribute.name: 1000},
        }

        items = product_selection.get_available_pipe_clamps()
        self.assertIn(hzn_item_12.id, items)

        product_selection.params['pipe_clamp']['pipe_mount'] = hzn_item_12.id
        found_hzn_item_12, found_zom_item = product_selection.get_pipe_mount_item()
        self.assertIsNotNone(found_hzn_item_12)
        self.assertIsNotNone(found_zom_item)
        self.assertEqual(found_hzn_item_12.id, hzn_item_12.id)
        self.assertEqual(found_zom_item.id, zom_item_12.id)

    def test_12x16(self):
        load_group, _ = LoadGroup.objects.get_or_create(
            lgv=12,
            defaults={
                'kn': 1,
            }
        )

        load_group_16, _ = LoadGroup.objects.get_or_create(
            lgv=16,
            defaults={
                'kn': 1,
            }
        )

        product_class = ProductClass.objects.create(
            name='ProductClass',
        )

        product_family = ProductFamily.objects.create(
            product_class=product_class,
            name='ProductFamily',
            is_upper_mount_selectable=True,
        )

        zom_detail_type = DetailType.objects.create(
            name='Рым-гайка',
            designation='ZOM',
            category=DetailType.DETAIL,
        )

        zom_lgv_attribute = Attribute.objects.create(
            detail_type=zom_detail_type,
            type=AttributeType.CATALOG,
            usage=AttributeUsageChoices.LOAD_GROUP,
            catalog=AttributeCatalog.LOAD_GROUP,
            name='LGV',
            label_ru='Нагрузочная группа',
            fieldset=self.fieldset,
            position=1,
        )

        hzn_lgv_attribute_2 = Attribute.objects.create(
            detail_type=zom_detail_type,
            type=AttributeType.CATALOG,
            usage=AttributeUsageChoices.LOAD_GROUP,
            catalog=AttributeCatalog.LOAD_GROUP,
            name='LGV2',
            label_ru='Нагрузочная группа 2',
            fieldset=self.fieldset,
            position=2,
        )

        zom_variant = Variant.objects.create(
            detail_type=zom_detail_type,
            name='1',
            marking_template='ZOM {{ LGV.lgv }} ({{ inner_id }})',
        )

        zom_item = Item.objects.create(
            type=zom_detail_type,
            variant=zom_variant,
            parameters={
                'LGV': load_group.id,
                'LGV2': load_group_16.id,
            },
            author=self.user,
        )

        hzn_detail_type = DetailType.objects.create(
            name='Хомут двухболтовый',
            designation='HZN',
            category=DetailType.ASSEMBLY_UNIT,
        )

        hzn_lgv_attribute = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.CATALOG,
            usage=AttributeUsageChoices.LOAD_GROUP,
            catalog=AttributeCatalog.LOAD_GROUP,
            name='LGV',
            label_ru='Нагрузочная группа',
            fieldset=self.fieldset,
            position=1,
        )

        hzn_pipe_diameter = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.CATALOG,
            catalog=AttributeCatalog.PIPE_DIAMETER,
            name='OD',
            label_ru='Диаметр трубопровода',
            fieldset=self.fieldset,
            position=2,
        )

        hzn_material = Attribute.objects.create(
            detail_type= hzn_detail_type,
            type= AttributeType.CATALOG,
            catalog=AttributeCatalog.MATERIAL,
            name='material',
            label_ru='Материал',
            fieldset=self.fieldset,
            position=3,
        )

        hzn_load_attribute = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.LOAD,
            name='Fn',
            label_ru='Номинальная нагрузка',
            fieldset=self.fieldset,
            position=4,
        )

        hzn_clamp_load_attribute = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.CLAMP_LOAD,
            name='Fn1',
            label_ru='Нагрузка для хомутов',
            fieldset=self.fieldset,
            position=5,
        )

        hzn_covering_type = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.CATALOG,
            catalog=AttributeCatalog.COVERING_TYPE,
            name='coating',
            label_ru='Покрытие',
            fieldset=self.fieldset,
            position=6,
        )

        hzn_variant = Variant.objects.create(
            detail_type=hzn_detail_type,
            name='1',
            marking_template='HZN {{ LGV.lgv }} ({{ inner_id }})',
        )

        pipe_mounting_group = PipeMountingGroup.objects.create(
            name='Хомуты двухболтовые',
        )
        pipe_mounting_group.variants.add(hzn_variant)

        hzn_item = Item.objects.create(
            type=hzn_detail_type,
            variant=hzn_variant,
            parameters={
                'LGV': load_group_16.id,
                'material': self.material.id,
                'OD': self.pipe_diameter.id,
                'Fn': 1000,
                'Fn1': 1000,
                'coating': self.covering_type.id,
            },
            author=self.user,
        )

        matrix = ClampSelectionMatrix.objects.create(
            product_family=product_family,
        )
        matrix.clamp_detail_types.add(hzn_detail_type)
        matrix.fastener_detail_types.add(zom_detail_type)
        matrix.entries.create(
            hanger_load_group=12,
            clamp_load_group=16,
            result="adapter_required",
        )

        project = Project.objects.create(
            number='12345',
            owner=self.user,
            status=ProjectStatus.DRAFT,
            load_unit=LoadUnit.KN,
            move_unit=MoveUnit.MM,
            temperature_unit=TemperatureUnit.CELSIUS,
        )
        project_item = ProjectItem.objects.create(
            project=project,
            position_number=1,
        )
        product_selection = ProductSelectionAvailableOptions(project_item)
        product_selection.params['product_family'] = product_family.id
        product_selection.params['load_and_move']['load_minus_z'] = 500
        product_selection.params['pipe_params']['pipe_mounting_group'] = pipe_mounting_group.id
        product_selection.params['pipe_params']['clamp_material'] = self.material.id
        product_selection.params['pipe_params']['nominal_diameter'] = self.pipe_diameter.id
        product_selection.params['pipe_params']['temp1'] = 130
        product_selection.params['spring_choice']['selected_spring'] = {
            'load_group_lgv': load_group.lgv,
            'variant': self.spring_variant,
            'parameters': {self.spring_load_attribute.name: 1000},
        }

        items = product_selection.get_available_pipe_clamps()
        self.assertIn(hzn_item.id, items)

        product_selection.params['pipe_clamp']['pipe_mount'] = hzn_item.id
        found_hzn_item, found_zom_item = product_selection.get_pipe_mount_item()
        self.assertIsNotNone(found_hzn_item)
        self.assertIsNotNone(found_zom_item)
        self.assertEqual(found_hzn_item.id, hzn_item.id)
        self.assertEqual(found_zom_item.id, zom_item.id)

    def test_double_clamp_load_filtering(self):
        load_group, _ = LoadGroup.objects.get_or_create(
            lgv=12,
            defaults={'kn': 1},
        )

        product_class = ProductClass.objects.create(name='ProductClass')
        product_family = ProductFamily.objects.create(
            product_class=product_class,
            name='ProductFamily',
            is_upper_mount_selectable=True,
        )

        hzn_detail_type = DetailType.objects.create(
            name='Хомут двухболтовый',
            designation='HZN',
            category=DetailType.ASSEMBLY_UNIT,
        )

        hzn_lgv_attribute = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.CATALOG,
            usage=AttributeUsageChoices.LOAD_GROUP,
            catalog=AttributeCatalog.LOAD_GROUP,
            name='LGV',
            label_ru='Нагрузочная группа',
            fieldset=self.fieldset,
            position=1,
        )

        hzn_pipe_diameter = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.CATALOG,
            catalog=AttributeCatalog.PIPE_DIAMETER,
            name='OD',
            label_ru='Диаметр трубопровода',
            fieldset=self.fieldset,
            position=2,
        )

        hzn_material = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.CATALOG,
            catalog=AttributeCatalog.MATERIAL,
            name='material',
            label_ru='Материал',
            fieldset=self.fieldset,
            position=3,
        )

        hzn_load_attribute = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.LOAD,
            name='Fn',
            label_ru='Номинальная нагрузка',
            fieldset=self.fieldset,
            position=4,
        )

        hzn_clamp_load_attribute = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.CLAMP_LOAD,
            name='Fn1',
            label_ru='Нагрузка для хомутов',
            fieldset=self.fieldset,
            position=5,
        )

        hzn_covering_type = Attribute.objects.create(
            detail_type=hzn_detail_type,
            type=AttributeType.CATALOG,
            catalog=AttributeCatalog.COVERING_TYPE,
            name='coating',
            label_ru='Покрытие',
            fieldset=self.fieldset,
            position=6,
        )

        hzn_variant = Variant.objects.create(
            detail_type=hzn_detail_type,
            name='1',
            marking_template='HZN {{ LGV.lgv }} ({{ inner_id }})',
        )

        pipe_mounting_group = PipeMountingGroup.objects.create(name='Хомуты двухболтовые')
        pipe_mounting_group.variants.add(hzn_variant)

        hzn_item_ok = Item.objects.create(
            type=hzn_detail_type,
            variant=hzn_variant,
            parameters={
                'LGV': load_group.id,
                'material': self.material.id,
                'OD': self.pipe_diameter.id,
                'Fn': 200,
                'Fn1': 200,
                'coating': self.covering_type.id,
            },
            author=self.user,
        )

        hzn_item_low_fn1 = Item.objects.create(
            type=hzn_detail_type,
            variant=hzn_variant,
            parameters={
                'LGV': load_group.id,
                'material': self.material.id,
                'OD': self.pipe_diameter.id,
                'Fn': 200,
                'Fn1': 190,
                'coating': self.covering_type.id,
            },
            author=self.user,
        )

        hzn_item_low_fn = Item.objects.create(
            type=hzn_detail_type,
            variant=hzn_variant,
            parameters={
                'LGV': load_group.id,
                'material': self.material.id,
                'OD': self.pipe_diameter.id,
                'Fn': 140,
                'Fn1': 250,
                'coating': self.covering_type.id,
            },
            author=self.user,
        )

        project = Project.objects.create(
            number='12345',
            owner=self.user,
            status=ProjectStatus.DRAFT,
            load_unit=LoadUnit.KN,
            move_unit=MoveUnit.MM,
            temperature_unit=TemperatureUnit.CELSIUS,
        )

        project_item = ProjectItem.objects.create(project=project, position_number=1)

        product_selection = ProductSelectionAvailableOptions(project_item)
        product_selection.params['product_family'] = product_family.id
        product_selection.params['load_and_move']['load_minus_z'] = 150
        product_selection.params['pipe_options']['branch_qty'] = 2
        product_selection.params['pipe_params']['pipe_mounting_group'] = pipe_mounting_group.id
        product_selection.params['pipe_params']['clamp_material'] = self.material.id
        product_selection.params['pipe_params']['nominal_diameter'] = self.pipe_diameter.id
        product_selection.params['pipe_params']['temp1'] = 200
        product_selection.params['spring_choice']['selected_spring'] = {
            'load_group_lgv': load_group.lgv,
            'variant': self.spring_variant,
            'parameters': {self.spring_load_attribute.name: 200},
        }

        items = product_selection.get_available_pipe_clamps()

        self.assertIn(hzn_item_ok.id, items)
        self.assertNotIn(hzn_item_low_fn1.id, items)
        self.assertNotIn(hzn_item_low_fn.id, items)
