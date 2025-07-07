from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from ops.choices import ProjectStatus, LoadUnit, MoveUnit, TemperatureUnit
from ops.marking_compiler import MarkingCompiler
from ops.models import Item, DetailType, Project

User = get_user_model()


class DummyMarkingCompiler:
    def __init__(self, item, marking_template=None):
        self.item = item
        self.marking_template = marking_template or ""

    def compile(self):
        return "TestMarking"


class ItemModelTest(TestCase):
    def setUp(self):
        self.original_MarkingCompiler_init = MarkingCompiler.__init__
        self.original_MarkingCompiler_compile = MarkingCompiler.compile
        MarkingCompiler.__init__ = DummyMarkingCompiler.__init__
        MarkingCompiler.compile = DummyMarkingCompiler.compile

        self.user = User.objects.create_user(email="test@example.com", password="password")

        self.detail_type = DetailType.objects.create(
            product_family=None,
            name="Test Detail",
            designation="TD",
            category=DetailType.DETAIL,
            branch_qty=DetailType.BranchQty.ONE,
            default_comment="Default Comment"
        )

        from ops.models import Variant
        self.variant = Variant.objects.create(
            detail_type=self.detail_type,
            name="Variant 1",
            marking_template="Template"
        )

        self.project = Project.objects.create(
            number="P-001",
            contragent="TestContragent",
            organization=None,
            owner=self.user,
            status=ProjectStatus.DRAFT,
            load_unit=LoadUnit.KN,
            move_unit=MoveUnit.MM,
            temperature_unit=TemperatureUnit.CELSIUS,
            standard=1
        )

        self.item_data = {
            "type": self.detail_type,
            "variant": self.variant,
            "author": self.user,
        }

    def tearDown(self):
        MarkingCompiler.__init__ = self.original_MarkingCompiler_init
        MarkingCompiler.compile = self.original_MarkingCompiler_compile

    def test_inner_id_generation(self):
        """При первом сохранении у Item должен сгенерироваться inner_id (не меньше 100000)."""
        item = Item.objects.create(**self.item_data)
        self.assertIsNotNone(item.inner_id)
        self.assertGreaterEqual(item.inner_id, 100000)

    def test_default_comment_set(self):
        """Если комментарий не задан, должен быть установлен comment из типа (default_comment)."""
        item = Item.objects.create(**self.item_data)
        self.assertEqual(item.comment, self.detail_type.default_comment)

    def test_marking_and_name_generation(self):
        """
        Если name_manual_changed = False (по умолчанию), то после сохранения
        name должна совпадать с сгенерированной маркировкой, которая равна "TestMarking".
        """
        item = Item.objects.create(**self.item_data)
        self.assertEqual(item.marking, "TestMarking")
        self.assertFalse(item.name_manual_changed)
        self.assertEqual(item.name, "TestMarking")

    def test_clean_variant_type_mismatch(self):
        """
        Если поле type не совпадает с variant.detail_type, метод clean должен выбросить ValidationError.
        """
        different_detail_type = DetailType.objects.create(
            product_family=None,
            name="Other Detail",
            designation="OD",
            category=DetailType.DETAIL,
            branch_qty=DetailType.BranchQty.ONE,
            default_comment="Other Comment"
        )
        item = Item(**self.item_data)
        item.type = different_detail_type
        with self.assertRaises(ValidationError):
            item.clean()

    def test_str_returns_marking(self):
        """Метод __str__ должен возвращать сгенерированную маркировку."""
        item = Item.objects.create(**self.item_data)
        self.assertEqual(str(item), "TestMarking")

    def test_generate_name_returns_marking(self):
        """Метод generate_name должен возвращать значение маркировки."""
        item = Item.objects.create(**self.item_data)
        self.assertEqual(item.generate_name(), "TestMarking")
