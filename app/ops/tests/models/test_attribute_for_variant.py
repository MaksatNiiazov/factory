from django.test import TestCase

from ops.choices import AttributeType
from ops.models import Attribute, Variant, DetailType, FieldSet


class AttributeForVariantTest(TestCase):
    """
    Тест-кейс для проверки метода for_variant у модели Attribute.

    Проверяет:
    - Корректную выбору атрибутов для исполнения (Variant),
      включая как базовые атрибуты типа детали (DetailType), так и конкретные атрибуты исполнения.
    - Приоритет конкретных атрибутов Variant над базовыми атрибутами DetailType при совпадении наименований.
    - Наличие атрибутов без дубликатов по имени с учётом правил приоритета.
    """

    def setUp(self):
        self.detail_type = DetailType.objects.create(
            name='Подвес пружинный',
            designation='FHD',
            category=DetailType.DETAIL,
        )

        self.variant = Variant.objects.create(
            detail_type=self.detail_type,
            name='Witz (1-4)',
        )

        self.fieldset = FieldSet.objects.create(
            name='Main',
        )

        # Атрибут только у DetailType
        Attribute.objects.create(
            name='E',
            detail_type=self.detail_type,
            type=AttributeType.INTEGER,
            fieldset=self.fieldset,
            position=1,
        )

        # Атрибут только у Variant
        Attribute.objects.create(
            name='D',
            variant=self.variant,
            type=AttributeType.INTEGER,
            fieldset=self.fieldset,
            position=1,
        )

        # Атрибут с одинаковым именем у DetailType
        Attribute.objects.create(
            name='m',
            detail_type=self.detail_type,
            type=AttributeType.INTEGER,
            fieldset=self.fieldset,
            position=2,
        )

        # Атрибут с таким же именем у Variant (должен замещать)
        Attribute.objects.create(
            name='m',
            variant=self.variant,
            type=AttributeType.INTEGER,
            fieldset=self.fieldset,
            position=2,
        )

    def test_for_variant_priority_and_filtering(self):
        attributes = Attribute.objects.for_variant(self.variant)

        names = [attr.name for attr in attributes]

        # Проверяем, что все нужные имена на месте
        self.assertIn('E', names, 'Должен быть атрибут только для DetailType')
        self.assertIn('D', names, 'Должен быть атрибут только для Variant')
        self.assertIn('m', names, 'Должен быть один m (от Variant)')

        # Проверяем, что m взят от Variant
        m_attr = attributes.get(name='m')
        self.assertEqual(m_attr.variant_id, self.variant.id, "m должен быть от Variant")
        self.assertIsNone(m_attr.detail_type_id, "m от Variant не должен быть связан с DetailType")

        # Проверяем, что D действительно от Variant
        d_attr = attributes.get(name='D')
        self.assertEqual(d_attr.variant_id, self.variant.id)

        # Проверяем, что E действительно от DetailType
        e_attr = attributes.get(name='E')
        self.assertEqual(e_attr.detail_type_id, self.detail_type.id)
