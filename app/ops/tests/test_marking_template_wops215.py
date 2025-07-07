from django.test import TestCase
from django.contrib.auth import get_user_model

from catalog.models import Material, CoveringType
from ops.choices import AttributeType, AttributeUsageChoices, AttributeCatalog
from ops.models import DetailType, Variant, FieldSet, Attribute, Item


class MarkingTemplateWOPS215Test(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@example.com", password="password123"
        )

        self.covering_type = CoveringType.objects.create(
            name_ru='Гальваника',
            numeric=1,
        )

        self.material = Material.objects.create(
            name_ru="09Г2С",
            group="16",
        )

        self.detail_type = DetailType.objects.create(
            name="Опора скользящая",
            designation="LSL 22",
            category=DetailType.ASSEMBLY_UNIT,
        )

        self.variant = Variant.objects.create(
            detail_type=self.detail_type,
            name="тип 1",
            marking_template="LSL 22.{{ OD.size|round(0, 'ceil')|int|zfill(4) }}.{{ E|int|zfill(3) }}-{{ material.group }}.{{ coating.numeric }} ({{ inner_id }})"
        )

        self.fieldset = FieldSet.objects.create(
            name="Main",
            label_ru="Main"
        )

        Attribute.objects.create(
            detail_type=self.detail_type,
            type=AttributeType.CATALOG,
            usage=AttributeUsageChoices.CUSTOM,
            catalog=AttributeCatalog.PIPE_DIAMETER,
            name="OD",
            label_ru="Диаметр трубопровода (OD)",
            is_required=True,
            fieldset=self.fieldset,
            position=1
        )
        Attribute.objects.create(
            detail_type=self.detail_type,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.CUSTOM,
            name="E",
            label_ru="Монтажный размер (E)",
            is_required=True,
            fieldset=self.fieldset,
            position=2
        )
        Attribute.objects.create(
            detail_type=self.detail_type,
            type=AttributeType.CATALOG,
            usage=AttributeUsageChoices.CUSTOM,
            catalog=AttributeCatalog.COVERING_TYPE,
            name="coating",
            label_ru="Покрытие (coating)",
            is_required=True,
            fieldset=self.fieldset,
            position=3
        )
        Attribute.objects.create(
            detail_type=self.detail_type,
            type=AttributeType.CATALOG,
            usage=AttributeUsageChoices.CUSTOM,
            catalog=AttributeCatalog.MATERIAL,
            name="material",
            label_ru="Материал (material)",
            is_required=True,
            fieldset=self.fieldset,
            position=4
        )
        Attribute.objects.create(
            detail_type=self.detail_type,
            type=AttributeType.INTEGER,
            usage=AttributeUsageChoices.CUSTOM,
            name="Fn",
            label_ru="Номинальная нагрузка (Fn)",
            is_required=True,
            fieldset=self.fieldset,
            position=5
        )
        Attribute.objects.create(
            detail_type=self.detail_type,
            type=AttributeType.NUMBER,
            usage=AttributeUsageChoices.SYSTEM_WEIGHT,
            name="m",
            label_ru="Масса (m)",
            is_required=True,
            fieldset=self.fieldset,
            position=6
        )

    def test_template_zfill_casting_error(self):
        """
        WOPS-215: https://ru.yougile.com/team/6a196c4265d6/#WOPS-215

        Проверяет исправление ошибки:
        'str' object cannot be interpreted as an integer
        при разборе шаблона:
        LSL 22.{{ OD.size|round('ceil')|int|zfill(4) }}
        """
        item = Item.objects.create(
            type=self.detail_type,
            variant=self.variant,
            parameters={
                "E": 150.0,
                "m": 22.0,
                "Fn": 22,
                "OD": 3,
                "coating": self.covering_type.id,
                "material": self.material.id,
            },
            author=self.user
        )

        item.refresh_from_db()

        self.assertNotIn("ERROR", item.marking, msg=f"marking_errors: {item.marking_errors}")
        self.assertFalse(item.marking_errors, msg=f"marking_errors: {item.marking_errors}")
        self.assertEqual(item.marking, f"LSL 22.0014.150-16.1 ({item.inner_id})")
