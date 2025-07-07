# from django.test import TestCase
#
# from catalog.models import LoadGroup, Material
# from kernel.api.tests import TestHelper
# from ops.forms import SpringChoiceForm
# from ops.loads.standard_series import MAX_SIZE, LOADS, SPRING_STIFFNESS_LIST
# from ops.loads.utils import get_suitable_loads
# from ops.models import DetailType, Item, Variant, Attribute, FieldSet, BaseComposition, ItemChild
#
#
# class GetSuitableLoadsTestCase(TestCase):
#     def setUp(self):
#         self.series_name = 'standard_series'
#         self.movement_plus = 0
#         self.movement_minus = 15
#         self.minimum_spring_travel = 5
#
#     def test_cold_load(self):
#         load_minus = 6.0  # Холодная нагрузка
#         expected_hot_load = 5.6475  # Ожидаемая горячая нагрузка
#
#         best_suitable_load, suitable_loads = get_suitable_loads(
#             series_name=self.series_name,
#             max_size=MAX_SIZE,
#             loads=LOADS,
#             spring_stiffness_list=SPRING_STIFFNESS_LIST,
#             load_minus=load_minus,
#             movement_plus=self.movement_plus,
#             movement_minus=self.movement_minus,
#             minimum_spring_travel=self.minimum_spring_travel,
#             estimated_state='cold',
#         )
#
#         found_load = next((load for load in suitable_loads if load['spring_stiffness'] == 23.5), None)
#         self.assertIsNotNone(found_load)
#         self.assertAlmostEqual(found_load['hot_design_load'], expected_hot_load, places=1)
#
#     def test_hot_load(self):
#         load_minus = 5.64
#         expected_cold_load = 5.9925
#
#         best_suitable_load, suitable_loads = get_suitable_loads(
#             series_name=self.series_name,
#             max_size=MAX_SIZE,
#             loads=LOADS,
#             spring_stiffness_list=SPRING_STIFFNESS_LIST,
#             load_minus=load_minus,
#             movement_plus=self.movement_plus,
#             movement_minus=self.movement_minus,
#             minimum_spring_travel=self.minimum_spring_travel,
#             estimated_state='hot',
#         )
#
#         found_load = next((load for load in suitable_loads if load['spring_stiffness'] == 23.5), None)
#         self.assertIsNotNone(found_load)
#         self.assertAlmostEqual(found_load['load_minus'], expected_cold_load, places=1)
#
#     def test_when_movement_plus_is_null(self):
#         data = {
#             'load_minus_z': 6,
#             'test_load_z': None,
#             'additional_load_z': None,
#             'move_plus_z': None,
#             'move_minus_z': self.movement_minus,
#             'estimated_state': 'cold',
#         }
#
#         form = SpringChoiceForm(data)
#         self.assertTrue(form.is_valid())
#         self.assertIsNotNone(form.cleaned_data['move_plus_z'])
#         self.assertEqual(form.cleaned_data['move_plus_z'], 0)
#
#         load_minus = 6.0  # Холодная нагрузка
#         expected_hot_load = 5.6475  # Ожидаемая горячая нагрузка
#
#         best_suitable_load, suitable_loads = get_suitable_loads(
#             series_name=self.series_name,
#             max_size=MAX_SIZE,
#             loads=LOADS,
#             spring_stiffness_list=SPRING_STIFFNESS_LIST,
#             load_minus=form.cleaned_data['load_minus_z'],
#             movement_plus=form.cleaned_data['move_plus_z'],
#             movement_minus=form.cleaned_data['move_minus_z'],
#             minimum_spring_travel=self.minimum_spring_travel,
#             estimated_state=form.cleaned_data['estimated_state'],
#         )
#
#         found_load = next((load for load in suitable_loads if load['spring_stiffness'] == 23.5), None)
#         self.assertIsNotNone(found_load)
#         self.assertAlmostEqual(found_load['hot_design_load'], expected_hot_load, places=1)
#
#
# class MarkingCompilerTestFCase(TestCase):
#     """
#     Тест-кейсы по компилятору шаблона маркировки
#     """
#
#     def setUp(self):
#         self.helper = TestHelper()
#         self.user = self.helper.create_user()
#         self.load_group = LoadGroup.objects.create(
#             lgv=13,
#             kn=14,
#         )
#         self.material = Material.objects.create(
#             name='FCD 0913',
#         )
#
#     def test_proper_data(self):
#         """
#         Тестируем с присутствующими данными в parameters
#         """
#
#         # Создаем тип детали
#         detail_type = DetailType.objects.create(
#             short_name=DetailType.ItemName.STUD,
#             name='Тестовый тип детали',
#             designation='TEST',
#             category=DetailType.DETAIL,
#         )
#
#         # Создание исполнение
#         variant = Variant.objects.create(
#             detail_type=detail_type,
#             name='1',
#             marking_template='FHD {{ s }}x{{ d }}',
#         )
#
#         fieldset = FieldSet.objects.create(
#             name='test',
#         )
#
#         Attribute.objects.create(
#             variant=variant,
#             fieldset=fieldset,
#             position=1,
#             type='number',
#             name='s',
#         )
#         Attribute.objects.create(
#             variant=variant,
#             fieldset=fieldset,
#             position=2,
#             type='integer',
#             name='d',
#         )
#         Attribute.objects.create(
#             variant=variant,
#             fieldset=fieldset,
#             position=3,
#             type='catalog',
#             catalog='LoadGroup',
#             name='load_group',
#         )
#
#         # Создаем деталь
#         item = Item.objects.create(
#             type=detail_type,
#             variant=variant,
#             name='Наименование детали',
#             weight=1.5,
#             material=self.material,
#             parameters={
#                 's': 16.3,
#                 'd': 12,
#                 'load_group': self.load_group.id,
#             },
#             author=self.user,
#         )
#
#         # Проверяем, что маркировка успешно установлено
#         self.assertEqual(item.marking, 'FHD 16.3x12')
#
#     def test_with_inner_id(self):
#         """
#         Тестируем, включая inner_id в шаблон
#         """
#
#         # Создаем тип детали
#         detail_type = DetailType.objects.create(
#             short_name=DetailType.ItemName.STUD,
#             name='Тестовый тип детали',
#             designation='TEST',
#             category=DetailType.DETAIL,
#         )
#
#         # Создаем исполнение
#         variant = Variant.objects.create(
#             detail_type=detail_type,
#             name='1',
#             marking_template='FHD {{ s }}x{{ d }} ({{ inner_id }})',
#         )
#
#         fieldset = FieldSet.objects.create(
#             name='test',
#         )
#
#         Attribute.objects.create(
#             variant=variant,
#             fieldset=fieldset,
#             position=1,
#             type='number',
#             name='s',
#         )
#         Attribute.objects.create(
#             variant=variant,
#             fieldset=fieldset,
#             position=2,
#             type='integer',
#             name='d',
#         )
#         Attribute.objects.create(
#             variant=variant,
#             fieldset=fieldset,
#             position=3,
#             type='catalog',
#             catalog='LoadGroup',
#             name='load_group',
#         )
#
#         # Создаем деталь
#         item = Item.objects.create(
#             type=detail_type,
#             variant=variant,
#             name='Наименование детали',
#             weight=1.5,
#             material=self.material,
#             parameters={
#                 's': 16.3,
#                 'd': 12,
#                 'load_group': self.load_group.id,
#             },
#             author=self.user,
#         )
#         inner_id = item.inner_id
#
#         # Проверяем, что маркировка успешно установлено
#         self.assertEqual(item.marking, f'FHD 16.3x12 ({inner_id})')
#
#     def test_with_base_composition(self):
#         """
#         Тестируем генерацию маркировки, когда у DetailType есть базовый состав (BaseComposition) с дочерними элеменатми.
#         """
#         # Создаем родительский тип детали
#         parent_detail_type = DetailType.objects.create(
#             name='Фланец',
#             designation='FRF',
#             category=DetailType.PRODUCT,
#         )
#
#         # Создаем вариант для родителя
#         parent_variant = Variant.objects.create(
#             detail_type=parent_detail_type,
#             name='Witzenmann',
#             marking_template='Фланец FRF {{ s }}x{{ s + detail_LUG.s }} ({{ x }})'
#         )
#
#         fieldset = FieldSet.objects.create(name='geometry', label_ru='Геометрия')
#
#         # Атрибуты родителя
#         Attribute.objects.create(
#             variant=parent_variant,
#             fieldset=fieldset,
#             position=1,
#             type='number',
#             name='s',
#             label_ru='S',
#         )
#
#         Attribute.objects.create(
#             variant=parent_variant,
#             fieldset=fieldset,
#             position=2,
#             type='number',
#             name='x',
#             label_ru='X',
#             calculated_value='{{ s + detail_LUG.s }}',
#         )
#
#         parent_item = Item.objects.create(
#             type=parent_detail_type,
#             variant=parent_variant,
#             weight=10.0,
#             material=self.material,
#             parameters={
#                 's': 5,
#             },
#             author=self.user,
#         )
#         parent_item.clean()
#         parent_item.save()
#
#         parent_item = Item.objects.get(id=parent_item.id)
#         print(parent_item.marking)
#         print(parent_item.marking_errors)
#         print(parent_item.parameters)
#         print(parent_item.parameters_errors)
#
#         child_detail_type = DetailType.objects.create(
#             name='Втулка',
#             designation='LUG',
#             category=DetailType.DETAIL,
#         )
#         child_variant = Variant.objects.create(
#             detail_type=child_detail_type,
#             name='1',
#             marking_template='Втулка {{ s }}',
#         )
#
#         Attribute.objects.create(
#             variant=child_variant,
#             fieldset=fieldset,
#             position=1,
#             type='number',
#             name='s',
#         )
#
#         BaseComposition.objects.create(
#             base_parent=parent_detail_type,
#             base_child=child_detail_type,
#             position=1,
#             material=self.material,
#             count=1,
#         )
#
#         child_item = Item.objects.create(
#             type=child_detail_type,
#             variant=child_variant,
#             weight=1.0,
#             material=self.material,
#             parameters={'s': 9},
#             author=self.user,
#         )
#
#         ItemChild.objects.create(
#             parent=parent_item,
#             child=child_item,
#             position=1,
#             count=1,
#         )
#
#         parent_item = Item.objects.get(id=parent_item.id)
#         parent_item.clean()
#         parent_item.save()
#
#         parent_item = Item.objects.get(id=parent_item.id)
#         print(parent_item.marking)
#         print(parent_item.marking_errors)
#         print(parent_item.parameters)
#         print(parent_item.parameters_errors)