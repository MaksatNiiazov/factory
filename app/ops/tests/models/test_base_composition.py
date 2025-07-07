from django.core.exceptions import ValidationError
from django.test import TestCase

from ops.models import BaseComposition, DetailType, Material


class BaseCompositionModelTest(TestCase):
    def setUp(self):
        self.parent_detail = DetailType.objects.create(
            product_family=None,
            name="Parent Detail",
            designation="PARENT",
            category=DetailType.PRODUCT,
            branch_qty=DetailType.BranchQty.ONE,
            default_comment="Default parent comment"
        )
        self.child_detail = DetailType.objects.create(
            product_family=None,
            name="Child Detail",
            designation="CHILD",
            category=DetailType.DETAIL,
            branch_qty=DetailType.BranchQty.ONE,
            default_comment="Default child comment"
        )
        self.material = Material.objects.create(
            name="Test Material",
            group="Test Group",
            type="A"
        )

    def test_valid_base_composition(self):
        """Проверка успешного создания корректного объекта BaseComposition."""
        bc = BaseComposition.objects.create(
            base_parent=self.parent_detail,
            base_child=self.child_detail,
            position=1,
            count=2
        )
        self.assertIsNotNone(bc.id)

    def test_invalid_same_parent_child(self):
        """Проверка, что базовый элемент не может совпадать с комплектующим."""
        bc = BaseComposition(
            base_parent=self.parent_detail,
            base_child=self.parent_detail,
            position=1,
            count=1
        )
        with self.assertRaises(ValidationError) as context:
            bc.full_clean()
        self.assertIn("Сборка не может содержать саму себя как комплектующий элемент", str(context.exception))

    def test_cycle_detection(self):
        """
        Проверяем, что цикл в связях обнаруживается.
        Создаем сначала связь от parent_detail к child_detail,
        затем пытаемся создать обратную связь, которая приводит к циклу.
        """
        BaseComposition.objects.create(
            base_parent=self.parent_detail,
            base_child=self.child_detail,
            position=1,
            count=1
        )
        bc_cycle = BaseComposition(
            base_parent=self.child_detail,
            base_child=self.parent_detail,
            position=2,
            count=1
        )
        with self.assertRaises(ValidationError) as context:
            bc_cycle.full_clean()
        self.assertIn("Сборка не может содержать своих предков", str(context.exception))

    def test_ordering(self):
        """Проверяем, что объекты BaseComposition упорядочены по полю position."""
        bc1 = BaseComposition.objects.create(
            base_parent=self.parent_detail,
            base_child=self.child_detail,
            position=2,
            count=1
        )
        bc2 = BaseComposition.objects.create(
            base_parent=self.parent_detail,
            base_child=self.child_detail,
            position=1,
            count=1
        )
        qs = BaseComposition.objects.filter(base_parent=self.parent_detail)
        positions = [bc.position for bc in qs]
        self.assertEqual(positions, sorted(positions))

    def test_str_method(self):
        """Проверка корректности строкового представления объекта BaseComposition."""
        bc = BaseComposition.objects.create(
            base_parent=self.parent_detail,
            base_child=self.child_detail,
            position=3,
            count=4
        )
        expected = f"{self.parent_detail}: #3 {self.child_detail} (Кол.: 4)"
        self.assertEqual(str(bc), expected)
