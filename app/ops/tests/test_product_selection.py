from django.test import TestCase
from django.contrib.auth import get_user_model

from catalog.models import PipeMountingGroup, Material
from ops.models import Variant, Attribute, Item, DetailType, FieldSet
from ops.choices import AttributeUsageChoices
from ops.services.product_selection import ProductSelectionAvailableOptions


class ProductSelectionAvailableOptionsTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        self.detail_type = DetailType.objects.create(name='Пружинный блок')
        self.fieldset = FieldSet.objects.create(name='Основные параметры')

        self.variant = Variant.objects.create(
            name='Test Variant',
            detail_type=self.detail_type
        )

        self.size_attr = Attribute.objects.create(
            name='VH',
            usage=AttributeUsageChoices.SIZE,
            variant=self.variant,
            fieldset=self.fieldset,
            position=1
        )

        self.stroke_attr = Attribute.objects.create(
            name='Sn',
            usage=AttributeUsageChoices.RATED_STROKE,
            variant=self.variant,
            fieldset=self.fieldset,
            position=2
        )

    def get_selector(self, size, stroke):
        class MockProjectItem:
            selection_params = {
                'spring_choice': {
                    'selected_spring': {
                        'size': size,
                        'rated_stroke': stroke
                    }
                }
            }
        return ProductSelectionAvailableOptions(MockProjectItem())

    def test_found_single_item(self):
        item = Item.objects.create(
            type=self.detail_type,
            variant=self.variant,
            parameters={'VH': '9', 'Sn': '100'},
            author=self.user
        )
        selector = self.get_selector('9', '100')
        result = selector.get_spring_block_item()
        self.assertEqual(result, item)
        self.assertEqual(len(selector.debug), 0)

    def test_not_found(self):
        selector = self.get_selector('9', '999')  # Неверный параметр
        result = selector.get_spring_block_item()
        self.assertIsNone(result)
        self.assertTrue(any('Не найден' in msg for msg in selector.debug))

    def test_multiple_found(self):
        item1 = Item.objects.create(
            type=self.detail_type,
            variant=self.variant,
            parameters={'VH': '9', 'Sn': '100'},
            author=self.user
        )
        item2 = Item.objects.create(
            type=self.detail_type,
            variant=self.variant,
            parameters={'VH': '9', 'Sn': '100'},
            author=self.user
        )
        selector = self.get_selector('9', '100')
        result = selector.get_spring_block_item()
        self.assertIn(result, [item1, item2])
        self.assertTrue(any('несколько деталей' in msg for msg in selector.debug))

    def test_one_of_two_matches(self):
        item1 = Item.objects.create(
            type=self.detail_type,
            variant=self.variant,
            parameters={'VH': '9', 'Sn': '100'},
            author=self.user
        )
        Item.objects.create(
            type=self.detail_type,
            variant=self.variant,
            parameters={'VH': '10', 'Sn': '999'},
            author=self.user
        )
        selector = self.get_selector('9', '100')
        result = selector.get_spring_block_item()
        self.assertEqual(result, item1)
        self.assertEqual(len(selector.debug), 0)

    def test_selected_spring_is_none(self):
        class MockProjectItem:
            selection_params = {
                'spring_choice': {
                    'selected_spring': None
                }
            }
        selector = ProductSelectionAvailableOptions(MockProjectItem())
        result = selector.get_spring_block_item()
        self.assertIsNone(result)
        self.assertTrue(any('Не выбран пружинный блок' in msg for msg in selector.debug))

    def test_missing_attribute(self):
        self.size_attr.delete()  # Удаляем один нужный атрибут
        item = Item.objects.create(
            type=self.detail_type,
            variant=self.variant,
            parameters={'VH': '9', 'Sn': '100'},
            author=self.user
        )
        selector = self.get_selector('9', '100')
        result = selector.get_spring_block_item()
        self.assertIsNone(result)
        self.assertTrue(any('Не найден' in msg for msg in selector.debug))

    def test_clamp_when_branch_qty_is_more_than_one(self):
        """
        Тестирование когда нужно найти хомута когда количество пружинных блоков больше 1.
        """
        detail_type = DetailType.objects.create(
            name='Хомут',
            designation='MSN',
            category=DetailType.ASSEMBLY_UNIT,
        )
        variant = Variant.objects.create(
            detail_type=detail_type,
            name='Исполнение 1',
            marking_template='MSN',
        )
        pipe_mounting_group = PipeMountingGroup.objects.create(
            name='Хомуты',
        )
        pipe_mounting_group.variants.add(variant)
        material = Material.objects.create(
            name_ru='09Г2С',
            group='16',
        )

        attribute = Attribute.objects.create(

        )

        item = Item.objects.create(
            type=detail_type,
            variant=variant,
            parameters={},
            material=material,
            author=self.user,
        )

        class MockProjectItem:
            selection_params = {
                'pipe_options': {
                    'branch_qty': 1,
                },
                'pipe_params': {
                    'pipe_mounting_group_bottom': pipe_mounting_group.id,
                    'pipe_mounting_group_top': None,
                    'clamp_material': material.id,
                },
                'spring_choice': {
                    'selected_spring': {
                        'load_group_lgv': None,
                    },
                },
            }

        selection = ProductSelectionAvailableOptions(MockProjectItem)
        pipe_clamps = selection.get_pipe_clamps()
        self.assertNotIn(item.id, pipe_clamps)
        print(selection.debug)
