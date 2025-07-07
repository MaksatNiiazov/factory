from django.contrib.auth import get_user_model
from django.test import TestCase

from catalog.models import Material
from ops.models import TemporaryComposition, DetailType, Item
from ops.models import Variant

User = get_user_model()


class TemporaryCompositionModelTest(TestCase):
    def setUp(self):
        self.parent_detail = DetailType.objects.create(
            product_family=None,
            name="Parent Detail",
            designation="PARENT",
            category=DetailType.PRODUCT,
            branch_qty=DetailType.BranchQty.ONE
        )
        self.variant_detail = DetailType.objects.create(
            product_family=None,
            name="Variant Detail",
            designation="VARIANT",
            category=DetailType.PRODUCT,
            branch_qty=DetailType.BranchQty.ONE
        )
        self.user = User.objects.create_user(email="test@example.com", password="testpass")
        self.variant = Variant.objects.create(
            detail_type=self.variant_detail,
            name="Variant 1",
            marking_template="TestMarking"
        )
        self.item = Item.objects.create(
            type=self.parent_detail,
            variant=self.variant,
            author=self.user
        )
        self.tmp_child_detail = DetailType.objects.create(
            product_family=None,
            name="Tmp Child Detail",
            designation="TMPCHILD",
            category=DetailType.DETAIL,
            branch_qty=DetailType.BranchQty.ONE
        )
        self.material = Material.objects.create(
            name="Test Material",
            group="Test Group",
            type="A"
        )

    def test_valid_temporary_composition(self):
        """Проверка успешного создания TemporaryComposition и корректности __str__."""
        tmp_comp = TemporaryComposition.objects.create(
            tmp_parent=self.item,
            tmp_child=self.tmp_child_detail,
            position=1,
            material=self.material,
            count=5
        )
        self.assertIsNotNone(tmp_comp.id)
        expected_str = f"{self.item}: #1 {self.tmp_child_detail} (Кол.: 5)"
        self.assertEqual(str(tmp_comp), expected_str)

    def test_ordering(self):
        """Проверка, что объекты TemporaryComposition упорядочены по полю position для одного tmp_parent."""
        comp1 = TemporaryComposition.objects.create(
            tmp_parent=self.item,
            tmp_child=self.tmp_child_detail,
            position=2,
            material=self.material,
            count=3
        )
        comp2 = TemporaryComposition.objects.create(
            tmp_parent=self.item,
            tmp_child=self.tmp_child_detail,
            position=1,
            material=self.material,
            count=4
        )
        qs = TemporaryComposition.objects.filter(tmp_parent=self.item)
        positions = [comp.position for comp in qs]
        self.assertEqual(positions, sorted(positions))
