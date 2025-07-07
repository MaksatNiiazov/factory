from django.test import TestCase
from django.core.exceptions import ValidationError

from ops.choices import AttributeType
from ops.models import DetailType, Variant, Attribute, FieldSet


class DetailTypeTest(TestCase):
    def setUp(self):
        """Создаем тестовые объекты перед запуском тестов"""
        self.detail_type = DetailType.objects.create(
            name="Test Detail",
            designation="TD001",
            category=DetailType.DETAIL
        )

        self.product_type = DetailType.objects.create(
            name="Test Product",
            designation="TP001",
            category=DetailType.PRODUCT,
            branch_qty=DetailType.BranchQty.ONE
        )

    def test_create_detail_type(self):
        """Тест создания объекта DetailType"""
        detail = DetailType.objects.create(
            name="Another Detail",
            designation="TD002",
            category=DetailType.DETAIL
        )
        self.assertEqual(detail.name, "Another Detail")
        self.assertEqual(detail.designation, "TD002")

    def test_branch_qty_required_for_product(self):
        """Тест, что branch_qty обязателен для изделий (PRODUCT)"""
        with self.assertRaises(ValidationError):
            detail = DetailType(
                name="Invalid Product",
                designation="TP002",
                category=DetailType.PRODUCT
            )
            detail.full_clean()

    def test_str_representation(self):
        """Тест строкового представления DetailType"""
        self.assertEqual(str(self.detail_type), "TD001 - Test Detail")
        self.assertEqual(str(self.product_type), "TP001 - Test Product")

    def test_get_available_attributes(self):
        """Тест метода get_available_attributes"""
        variant = Variant.objects.create(detail_type=self.detail_type, name="Test Variant")
        fieldset = FieldSet.objects.create(name="Test Group", label="Test Label")

        attribute = Attribute.objects.create(
            variant=variant,
            type=AttributeType.STRING,
            name="test_attr",
            label="Test Attribute",
            fieldset=fieldset,
            position=1
        )

        attributes = self.detail_type.get_available_attributes(variant)

        self.assertEqual(len(attributes), 1)
        self.assertEqual(attributes[0]["name"], "test_attr")
        self.assertEqual(attributes[0]["label"], "Test Attribute")
