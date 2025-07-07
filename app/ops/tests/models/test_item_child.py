from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from ops.models import Item, DetailType, Variant, ItemChild

User = get_user_model()


class ItemChildModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='password')

        self.detail_type = DetailType.objects.create(
            product_family=None,
            name="Test DetailType",
            designation="TD",
            category=DetailType.DETAIL,
            branch_qty=DetailType.BranchQty.ONE,
            default_comment="Default comment"
        )

        self.variant = Variant.objects.create(
            detail_type=self.detail_type,
            name="Test Variant",
            marking_template="Test Marking"
        )

        self.parent_item = Item.objects.create(
            type=self.detail_type,
            variant=self.variant,
            author=self.user
        )
        self.child_item = Item.objects.create(
            type=self.detail_type,
            variant=self.variant,
            author=self.user
        )

    def test_string_representation(self):
        """Проверка корректности строкового представления объекта ItemChild."""
        item_child = ItemChild.objects.create(
            parent=self.parent_item,
            child=self.child_item,
            position=1,
            count=5
        )
        expected_str = f"{self.parent_item}: #1 {self.child_item} (Кол.: 5)"
        self.assertEqual(str(item_child), expected_str)

    def test_clean_parent_equals_child(self):
        """Проверка, что создание ItemChild с одинаковыми parent и child вызывает ValidationError."""
        item_child = ItemChild(
            parent=self.parent_item,
            child=self.parent_item,
            position=1,
            count=1
        )
        with self.assertRaises(ValidationError) as context:
            item_child.full_clean()
        self.assertIn("Родитель и дочерний элемент не могут быть одинаковыми", str(context.exception))

    def test_clean_cycle_detection(self):
        """Проверка обнаружения циклической зависимости в связях ItemChild."""
        ItemChild.objects.create(
            parent=self.parent_item,
            child=self.child_item,
            position=1,
            count=1
        )
        cyclic_child = ItemChild(
            parent=self.child_item,
            child=self.parent_item,
            position=2,
            count=1
        )
        with self.assertRaises(ValidationError) as context:
            cyclic_child.full_clean()
        self.assertIn("Нельзя добавлять родителя в качестве дочернего элемента", str(context.exception))

    def test_valid_creation(self):
        """Проверка успешного создания корректного объекта ItemChild."""
        item_child = ItemChild.objects.create(
            parent=self.parent_item,
            child=self.child_item,
            position=2,
            count=3
        )
        self.assertIsNotNone(item_child.id)

    def test_ordering(self):
        """Проверка сортировки объектов ItemChild по полю position (при одном родителе)."""
        ItemChild.objects.create(
            parent=self.parent_item,
            child=self.child_item,
            position=2,
            count=1
        )
        ItemChild.objects.create(
            parent=self.parent_item,
            child=self.child_item,
            position=1,
            count=1
        )
        qs = ItemChild.objects.filter(parent=self.parent_item)
        positions = [child.position for child in qs]
        self.assertEqual(positions, sorted(positions))
