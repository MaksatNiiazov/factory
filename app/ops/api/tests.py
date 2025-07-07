from django.test import TestCase

from catalog.models import LoadGroup, Material
from kernel.api.tests import TestHelper
from ops.models import Project, Variant, DetailType, Item, Attribute, FieldSet


class ProductSelectionTestCase(TestCase):
    def setUp(self):
        self.helper = TestHelper()
        self.user = self.helper.create_user()

    def authenticate(self, email, password=None):
        request_data = {
            'username': email,
            'password': password or 'test123',
        }

        response = self.client.post('/api/users/login/', data=request_data)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        token = data['token']
        headers = {
            'Authorization': f'Bearer {token}',
        }
        return headers

    def test_set_selection(self):
        self.helper.give_permissions(
            self.user,
            ['ops.add_project', 'ops.add_projectitem', 'ops.change_projectitem'],
        )
        headers = self.authenticate(self.user.email)

        # Создаем проект
        request_data = {
            'number': '483946',
            'load_unit': 'kN',
            'move_unit': 'mm',
            'temperature_unit': 'C',
        }
        response = self.client.post('/api/projects/', data=request_data, headers=headers)
        self.assertEqual(response.status_code, 201, msg=response.content.decode('utf-8'))

        response_data = response.json()
        project_id = response_data['id']

        # Создаем табличную часть проекта
        request_data = {}
        response = self.client.post(f'/api/projects/{project_id}/items/', data=request_data, headers=headers)
        self.assertEqual(response.status_code, 201, msg=response.content.decode('utf-8'))

        response_data = response.json()

        project_item_id = response_data['id']

        # selection_params уже должен быть заполнен возможными данными
        selection_params = response_data['selection_params']
        self.assertIsInstance(selection_params, dict)

        # Проверяем что selection_params содержит определенные параметры
        self.assertIn('product_class', selection_params)
        self.assertIsNone(selection_params['product_class'])
        self.assertIn('product_family', selection_params)
        self.assertIsNone(selection_params['product_family'])
        self.assertIn('pipe_options', selection_params)
        self.assertIn('location', selection_params['pipe_options'])
        self.assertEqual(selection_params['pipe_options']['location'], 'horizontal')
        self.assertIn('direction', selection_params['pipe_options'])
        self.assertEqual(selection_params['pipe_options']['direction'], 'x')
        self.assertIn('branch_qty', selection_params['pipe_options'])
        self.assertEqual(selection_params['pipe_options']['branch_qty'], 1)

        self.assertIn('load_and_move', selection_params)
        self.assertIn('load_plus_x', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['load_plus_x'], 0)
        self.assertIn('load_plus_y', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['load_plus_y'], 0)
        self.assertIn('load_plus_z', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['load_plus_z'], 0)
        self.assertIn('load_minus_x', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['load_minus_x'], 0)
        self.assertIn('load_minus_y', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['load_minus_y'], 0)
        self.assertIn('load_minus_z', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['load_minus_z'], 0)
        self.assertIn('additional_load_x', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['additional_load_x'], 0)
        self.assertIn('additional_load_y', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['additional_load_y'], 0)
        self.assertIn('additional_load_z', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['additional_load_z'], 0)
        self.assertIn('test_load_x', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['test_load_x'], 0)
        self.assertIn('test_load_y', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['test_load_y'], 0)
        self.assertIn('test_load_z', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['test_load_z'], 0)
        self.assertIn('move_plus_x', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['move_plus_x'], 0)
        self.assertIn('move_plus_y', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['move_plus_y'], 0)
        self.assertIn('move_plus_z', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['move_plus_z'], 0)
        self.assertIn('move_minus_x', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['move_minus_x'], 0)
        self.assertIn('move_minus_y', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['move_minus_y'], 0)
        self.assertIn('move_minus_z', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['move_minus_z'], 0)
        self.assertIn('estimated_state', selection_params['load_and_move'])
        self.assertEqual(selection_params['load_and_move']['estimated_state'], 'cold')

        self.assertIn('pipe_params', selection_params)
        self.assertIn('temp1', selection_params['pipe_params'])
        self.assertIsNone(selection_params['pipe_params']['temp1'])
        self.assertIn('temp2', selection_params['pipe_params'])
        self.assertIsNone(selection_params['pipe_params']['temp2'])
        self.assertIn('nominal_diameter', selection_params['pipe_params'])
        self.assertIsNone(selection_params['pipe_params']['nominal_diameter'])
        self.assertIn('outer_diameter_special', selection_params['pipe_params'])
        self.assertIsNone(selection_params['pipe_params']['outer_diameter_special'])
        self.assertIn('support_distance', selection_params['pipe_params'])
        self.assertIsNone(selection_params['pipe_params']['support_distance'])
        self.assertIn('support_distance_manual', selection_params['pipe_params'])
        self.assertIsNone(selection_params['pipe_params']['support_distance_manual'])
        self.assertIn('insulation_thickness', selection_params['pipe_params'])
        self.assertIsNone(selection_params['pipe_params']['insulation_thickness'])
        self.assertIn('clamp_material', selection_params['pipe_params'])
        self.assertIsNone(selection_params['pipe_params']['clamp_material'])

        self.assertIn('pipe_clamp', selection_params)
        self.assertIn('pipe_mount', selection_params['pipe_clamp'])
        self.assertIsNone(selection_params['pipe_clamp']['pipe_mount'])
        self.assertIn('top_mount', selection_params['pipe_clamp'])
        self.assertIsNone(selection_params['pipe_clamp']['top_mount'])

        # Попробуем изменить selection_params с текущими данными
        request_data = selection_params
        response = self.client.post(
            f'/api/projects/{project_id}/items/{project_item_id}/set_selection/', data=request_data,
            headers=headers, content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, msg=response.content.decode('utf-8'))

        request_data['load_and_move']['load_plus_z'] = 7
        response = self.client.post(
            f'/api/projects/{project_id}/items/{project_item_id}/set_selection/', data=request_data,
            headers=headers, content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, msg=response.content.decode('utf-8'))

        response_data = response.json()
        self.assertEqual(response_data['selection_params']['load_and_move']['load_plus_z'], 7)

    def test_get_selection_options(self):
        self.helper.give_permissions(
            self.user,
            ['ops.add_project', 'ops.view_projectitem', 'ops.add_projectitem', 'ops.change_projectitem'],
        )
        headers = self.authenticate(self.user.email)

        # Создаем проект
        request_data = {
            'number': '523765',
            'load_unit': 'kN',
            'move_unit': 'mm',
            'temperature_unit': 'C',
        }
        response = self.client.post('/api/projects/', data=request_data, headers=headers)
        self.assertEqual(response.status_code, 201, msg=response.content.decode('utf-8'))

        response_data = response.json()
        project_id = response_data['id']

        # Создаем табличную часть проекта
        request_data = {}
        response = self.client.post(f'/api/projects/{project_id}/items/', data=request_data, headers=headers)
        self.assertEqual(response.status_code, 201, msg=response.content.decode('utf-8'))

        response_data = response.json()

        selection_params = response_data['selection_params']
        project_item_id = response_data['id']

        # Проверяем доступных опции
        request_data = {}
        response = self.client.post(f'/api/projects/{project_id}/items/{project_item_id}/get_selection_options/', data=request_data, headers=headers)
        self.assertEqual(response.status_code, 200, msg=response.content.decode('utf-8'))

        response_data = response.json()
        self.assertListEqual(response_data['pipe_options']['locations'], ['horizontal', 'vertical'])
        self.assertListEqual(response_data['pipe_options']['directions'], ['x', 'y', 'at_angle'])
        self.assertListEqual(response_data['pipe_options']['branch_qty'], [1, 2])

        selection_params['pipe_options']['location'] = 'vertical'
        selection_params['load_and_move']['move_minus_z'] = 5
        selection_params['load_and_move']['load_minus_z'] = 20

        response = self.client.post(f'/api/projects/{project_id}/items/{project_item_id}/set_selection/', data=selection_params, headers=headers, content_type='application/json')
        self.assertEqual(response.status_code, 200, msg=response.content.decode('utf-8'))

        # Проверяем доступных опции
        request_data = {}
        response = self.client.post(
            f'/api/projects/{project_id}/items/{project_item_id}/get_selection_options/',
            data=request_data,
            headers=headers,
        )
        self.assertEqual(response.status_code, 200, msg=response.content.decode('utf-8'))

        response_data = response.json()
        self.assertListEqual(response_data['pipe_options']['locations'], ['horizontal', 'vertical'])
        self.assertListEqual(response_data['pipe_options']['directions'], ['z', 'at_angle'])
        self.assertListEqual(response_data['pipe_options']['branch_qty'], [2])

        print(response_data['spring_choice']['best_load'])

        selection_params['spring_choice']['selected_spring'] = response_data['spring_choice']['best_load']
        response = self.client.post(
            f'/api/projects/{project_id}/items/{project_item_id}/set_selection/',
            data=selection_params, headers=headers, content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, msg=response.content.decode('utf-8'))


#
#
# class ItemAPITestCase(TestCase):
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
#     def authenticate(self, email, password=None):
#         request_data = {
#             'username': email,
#             'password': password or 'test123',
#         }
#
#         response = self.client.post('/api/users/login/', data=request_data)
#         self.assertEqual(response.status_code, 200)
#         data = response.json()
#
#         token = data['token']
#         headers = {
#             'Authorization': f'Bearer {token}',
#         }
#
#         return headers
#
#     def test_marking_from_api(self):
#         """
#         Тестируем что маркировка успешно генерируется при изменении с api
#         """
#         headers = self.authenticate(self.user.email)
#         self.helper.give_permissions(self.user, ['ops.add_detailtype', 'ops.change_detailtype', 'ops.view_detailtype'])
#         self.helper.give_permissions(self.user, ['ops.add_own_item', 'ops.change_own_item', 'ops.view_own_item'])
#
#         # Создаем новый DetailType
#         request_data = {
#             'short_name': 3,
#             'name': 'Тестовый тип детали',
#             'designation': 'TEST',
#             'category': 'detail',
#         }
#         response = self.client.post('/api/detail_types/', data=request_data, headers=headers)
#         self.assertEqual(response.status_code, 201)
#
#         detail_type_id = response.json()['id']
#
#         # Создаем новый Variant
#         # TODO: Создать потом через API
#         variant = Variant.objects.create(
#             detail_type_id=detail_type_id,
#             name=1,
#             marking_template='FHD {{s}}x{{d}}',
#         )
#
#         fieldset = FieldSet.objects.create(
#             name='test',
#         )
#
#         Attribute.objects.create(
#             variant=variant,
#             fieldset=fieldset,
#             type='number',
#             name='s',
#         )
#         Attribute.objects.create(
#             variant=variant,
#             fieldset=fieldset,
#             type='integer',
#             name='d',
#         )
#
#         # Создаем новый Item
#         request_data = {
#             'type': detail_type_id,
#             'variant': variant.id,
#             'name': 'Тестовый деталь',
#             'weight': 1.6,
#             'load_group': self.load_group.id,
#             'parameters': {
#                 's': 6.3,
#                 'd': 12,
#             },
#             'material': self.material.id,
#         }
#         response = self.client.post(
#             '/api/items/', data=request_data, format='json', content_type='application/json', headers=headers
#         )
#         self.assertEqual(response.status_code, 201, msg=response.content.decode('utf8'))
#
#         data = response.json()
#         self.assertEqual(data['marking'], 'FHD 6.3x12')
#
#         item_id = data['id']
#
#         # Изменяем Item
#         request_data = {
#             'parameters': {
#                 's': 99,
#                 'd': 15,
#             }
#         }
#         response = self.client.patch(
#             f'/api/items/{item_id}/', data=request_data, format='json', content_type='application/json',
#             headers=headers,
#         )
#         self.assertEqual(response.status_code, 200, msg=response.content.decode('utf8'))
#
#         data = response.json()
#         self.assertEqual(data['marking'], 'FHD 99.0x15')
#
#         # Создаем еще один новый Item
#         request_data = {
#             'type': detail_type_id,
#             'variant': variant.id,
#             'name': 'Тестовый деталь 2',
#             'weight': 1.8,
#             'load_group': self.load_group.id,
#             'parameters': {
#                 's': 22,
#                 'd': 13,
#             },
#             'material': self.material.id,
#         }
#         response = self.client.post(
#             '/api/items/', data=request_data, format='json', content_type='application/json', headers=headers,
#         )
#         self.assertEqual(response.status_code, 201, msg=response.content.decode('utf8'))
#
#         data = response.json()
#         self.assertEqual(data['marking'], 'FHD 22.0x13')
#
#         item2_id = data['id']
#
#         # Теперь меняем marking_template у DetailType
#         # TODO: Написать api для Variant
#         # request_data = {
#         #     'marking_template': 'Хомут {{d}} {{s}}',
#         # }
#         # response = self.client.patch(
#         #     f'/api/detail_types/{detail_type_id}/', data=request_data, format='json', content_type='application/json',
#         #     headers=headers,
#         # )
#         # self.assertEqual(response.status_code, 200, msg=response.content.decode('utf8'))
#         #
#         # # У двух item'ов должны поменяться marking
#         # response = self.client.get(f'/api/items/{item_id}/', headers=headers)
#         # self.assertEqual(response.status_code, 200)
#         #
#         # data = response.json()
#         # self.assertEqual(data['marking'], 'Хомут 15 99')
#         #
#         # response = self.client.get(f'/api/items/{item2_id}/', headers=headers)
#         # self.assertEqual(response.status_code, 200)
#         #
#         # data = response.json()
#         # self.assertEqual(data['marking'], 'Хомут 13 22')
#
#     def test_check_that_models_clean_method_working_in_api(self):
#         """
#         Проверить что метод clean() у моделей действительно работает во-время валидации с помощью Serializer в api
#         """
#         headers = self.authenticate(self.user.email)
#         self.helper.give_permissions(self.user, ['ops.add_item', 'ops.change_item', 'ops.view_item'])
#
#         # Создаем новый DetailType
#         detail_type = DetailType.objects.create(
#             short_name=DetailType.ItemName.HALF_CLAMP,
#             name='TestName #1',
#             designation='QWE',
#             category=DetailType.DETAIL,
#         )
#
#         # Создаем еще один DetailType
#         detail_type2 = DetailType.objects.create(
#             short_name=DetailType.ItemName.BASE,
#             name='TestName #2',
#             designation='FDF',
#             category=DetailType.DETAIL,
#         )
#
#         # Создаем новый Variant
#         variant2 = Variant.objects.create(
#             detail_type=detail_type2,
#             name=1,
#             marking_template='FDF {{s}}x{{d}}',
#         )
#
#         # Создаем новый Item
#         # Здесь указываем detail_type и variant2 (тип у него detail_type2)
#         # Валидация не должно позволить этому случится
#         # Ранее это все-равно создавался, так как DRF не вызывал clean() у модели, теперь если был исправлен то должна
#         # быть ошибка
#         request_data = {
#             'type': detail_type.id,
#             'variant': variant2.id,
#             'name': 'Тестовый деталь',
#             'weight': 1.6,
#             'load_group': self.load_group.id,
#             'parameters': {
#                 's': 6.3,
#                 'd': 12,
#             },
#             'material': self.material.id,
#         }
#         response = self.client.post(
#             '/api/items/', data=request_data, format='json', content_type='application/json', headers=headers,
#         )
#
#         self.assertEqual(response.status_code, 400, msg=response.content.decode('utf8'))
#
#         content = response.json()
#         self.assertEqual(content['code'], 'validation_error')
#
#
# class ItemChildAPITestCase(TestCase):
#     """
#     Проверяем /api/items/{parent_pk}/children/
#     """
#     def setUp(self):
#         self.helper = TestHelper()
#         self.user = self.helper.create_user()
#
#     def authenticate(self, email, password=None):
#         request_data = {
#             'username': email,
#             'password': password or 'test123',
#         }
#
#         response = self.client.post('/api/users/login/', data=request_data)
#         self.assertEqual(response.status_code, 200)
#         data = response.json()
#
#         token = data['token']
#         headers = {
#             'Authorization': f'Bearer {token}',
#         }
#
#         return headers
#
#     def test_create_item_children(self):
#         headers = self.authenticate(self.user.email)
#         self.helper.give_permissions(self.user, [
#             'ops.add_item', 'ops.change_item', 'ops.view_item',
#             'ops.add_itemchild', 'ops.change_itemchild', 'ops.view_itemchild'
#         ])
#
#         # Создаем новый DetailType
#         detail_type = DetailType.objects.create(
#             short_name=DetailType.ItemName.FIN,
#             name='Тестовый тип детали',
#             designation='TEST',
#             category=DetailType.DETAIL,
#         )
#
#         # Создаем новый Variant
#         variant = Variant.objects.create(
#             detail_type=detail_type,
#             name=1,
#             marking_template='TEST {{s}}x{{d}}',
#         )
#
#         # Создаем новые Item'ы
#         request_data = {
#             'type': detail_type.id,
#             'variant': variant.id,
#             'name': 'Тестовый деталь',
#         }
#         response = self.client.post(
#             '/api/items/', data=request_data, format='json', content_type='application/json', headers=headers,
#         )
#         self.assertEqual(response.status_code, 201, msg=response.content.decode('utf8'))
#
#         item1_id = response.json()['id']
#
#         request_data = {
#             'type': detail_type.id,
#             'variant': variant.id,
#             'name': 'Тестовый деталь 2',
#         }
#         response = self.client.post(
#             '/api/items/', data=request_data, format='json', content_type='application/json', headers=headers,
#         )
#         self.assertEqual(response.status_code, 201, msg=response.content.decode('utf8'))
#
#         item2_id = response.json()['id']
#
#         # Добавим item2 к item1 как child
#         request_data = {
#             'child': item2_id,
#             'position': 1,
#             'count': 1,
#         }
#         response = self.client.post(
#             f'/api/items/{item1_id}/children/',
#             data=request_data,
#             format='json',
#             content_type='application/json',
#             headers=headers,
#         )
#         self.assertEqual(response.status_code, 201, msg=response.content.decode('utf8'))
#
#         item1 = Item.objects.get(id=item1_id)
#         item2 = item1.children.first()
#         self.assertEqual(item2.child_id, item2_id)
#
#
# class ProjectAPITestCase(TestCase):
#     def setUp(self):
#         self.helper = TestHelper()
#         self.user = self.helper.create_user()
#
#     def authenticate(self, email, password=None):
#         request_data = {
#             'username': email,
#             'password': password or 'test123',
#         }
#
#         response = self.client.post('/api/users/login/', data=request_data)
#         self.assertEqual(response.status_code, 200)
#         data = response.json()
#
#         token = data['token']
#         headers = {
#             'Authorization': f'Bearer {token}',
#         }
#
#         return headers
#
#     def test_list(self):
#         headers = self.authenticate(self.user.email)
#         self.helper.give_permissions(self.user, ['ops.view_project'])
#
#         user2 = self.helper.create_user()
#         user3 = self.helper.create_user()
#
#         projects = [
#             Project(number='1', owner=self.user, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='2', owner=self.user, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='3', owner=self.user, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='4', owner=user2, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='5', owner=user2, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='6', owner=user2, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='7', owner=user3, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='8', owner=user3, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='9', owner=user3, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#         ]
#         Project.objects.bulk_create(projects)
#
#         response = self.client.get('/api/projects/', headers=headers)
#         self.assertEqual(response.status_code, 200, msg=response.content.decode('utf8'))
#
#         projects = response.json()['results']
#
#         self.assertEqual(len(projects), 9)
#
#     def test_list_own(self):
#         headers = self.authenticate(self.user.email)
#         self.helper.give_permissions(self.user, ['ops.view_own_project'])
#
#         user2 = self.helper.create_user()
#         user3 = self.helper.create_user()
#
#         projects = [
#             Project(number='1', owner=self.user, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='2', owner=self.user, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='3', owner=self.user, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='4', owner=user2, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='5', owner=user2, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='6', owner=user2, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='7', owner=user3, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='8', owner=user3, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#             Project(number='9', owner=user3, load_unit=Project.kN, move_unit=Project.mm,
#                     temperature_unit=Project.C),
#         ]
#         Project.objects.bulk_create(projects)
#
#         response = self.client.get('/api/projects/', headers=headers)
#         self.assertEqual(response.status_code, 200, msg=response.content.decode('utf8'))
#
#         projects = response.json()['results']
#
#         self.assertEqual(len(projects), 3)
#
#     def test_create_own_project(self):
#         """
#         Проверка создания только своего проекта
#         """
#         headers = self.authenticate(self.user.email)
#         self.helper.give_permissions(self.user, ['ops.view_own_project'])
#
#         # У пользователя отсутствует разрешение
#         # Результат: ошибка permission denied
#         request_data = {
#             'number': 1,
#             'owner': self.user.id,
#             'load_unit': 'kN',
#             'move_unit': 'mm',
#             'temperature_unit': 'C',
#         }
#
#         response = self.client.post('/api/projects/', data=request_data, headers=headers)
#         self.assertEqual(response.status_code, 403)
#
#         response = self.client.get('/api/projects/', headers=headers)
#         self.assertEqual(response.status_code, 200)
#
#         projects = response.json()['results']
#         self.assertEqual(len(projects), 0)
#
#         self.helper.give_permissions(self.user, ['ops.add_own_project'])
#
#         # В owner указываем текущего пользователя
#         # Результат: должно создаться проект
#         request_data = {
#             'number': 1,
#             'owner': self.user.id,
#             'load_unit': 'kN',
#             'move_unit': 'mm',
#             'temperature_unit': 'C',
#         }
#
#         response = self.client.post('/api/projects/', data=request_data, headers=headers)
#         self.assertEqual(response.status_code, 201)
#
#         response = self.client.get('/api/projects/', headers=headers)
#         self.assertEqual(response.status_code, 200)
#
#         projects = response.json()['results']
#         self.assertEqual(len(projects), 1)
#
#         user2 = self.helper.create_user()
#
#         # В owner указываем другого пользователя
#         # Должна быть ошибка permission_denied
#         request_data = {
#             'number': 2,
#             'owner': user2.id,
#             'load_unit': 'kN',
#             'move_unit': 'mm',
#             'temperature_unit': 'C',
#         }
#
#         response = self.client.post('/api/projects/', data=request_data, headers=headers)
#         self.assertEqual(response.status_code, 403, msg=response.content.decode('utf8'))
#
#         code = response.json()['code']
#         self.assertEqual(code, 'permission_denied')
#
#         response = self.client.get('/api/projects/', headers=headers)
#         self.assertEqual(response.status_code, 200)
#
#         projects = response.json()['results']
#         self.assertEqual(len(projects), 1)
#
#         # В owner никого не указываем
#         # owner должен быть автоматически присвоен к текущему пользователю
#         request_data = {
#             'number': 3,
#             'load_unit': 'kN',
#             'move_unit': 'mm',
#             'temperature_unit': 'C',
#         }
#
#         response = self.client.post('/api/projects/', data=request_data, headers=headers)
#         self.assertEqual(response.status_code, 201, msg=response.content.decode('utf8'))
#
#         response = self.client.get('/api/projects/', headers=headers)
#         self.assertEqual(response.status_code, 200)
#
#         projects = response.json()['results']
#         self.assertEqual(len(projects), 2)
#
#     def test_modify_own_project(self):
#         """
#         Проверка на обновление только своего проекта
#         """
#         headers = self.authenticate(self.user.email)
#         self.helper.give_permissions(self.user, ['ops.view_own_project'])
#
#         project = Project.objects.create(
#             number='1',
#             owner=self.user,
#             load_unit='kN',
#             move_unit='mm',
#             temperature_unit='C',
#         )
#
#         # У пользователя отсутствует разрешение
#         # Результат: ошибка permission denied
#         request_data = {
#             'number': 2,
#             'temperature_unit': 'F',
#         }
#
#         url = f'/api/projects/{project.id}/'
#
#         response = self.client.patch(url, data=request_data, format='json', content_type='application/json',
#                                      headers=headers)
#         self.assertEqual(response.status_code, 403)
#
#         code = response.json()['code']
#         self.assertEqual(code, 'permission_denied')
#
#         project = Project.objects.get(id=project.id)
#         self.assertNotEqual(project.number, '2')
#         self.assertNotEqual(project.temperature_unit, 'F')
#
#         self.helper.give_permissions(self.user, ['ops.change_own_project'])
#
#         # У пользователя есть разрешение
#         # Результат: должно произойти изменение
#         response = self.client.patch(url, data=request_data, format='json', content_type='application/json',
#                                      headers=headers)
#         self.assertEqual(response.status_code, 200, msg=response.content.decode('utf8'))
#
#         project = Project.objects.get(id=project.id)
#         self.assertEqual(project.number, '2')
#         self.assertEqual(project.temperature_unit, 'F')
#
#         user2 = self.helper.create_user()
#
#         # Попытка изменить owner
#         # Не должно получиться
#         request_data = {
#             'number': 1,
#             'owner': user2.id,
#             'temperature_unit': 'C',
#         }
#         response = self.client.patch(url, data=request_data, format='json', content_type='application/json',
#                                      headers=headers)
#         self.assertEqual(response.status_code, 403, msg=response.content.decode('utf8'))
#
#         code = response.json()['code']
#         self.assertEqual(code, 'permission_denied')
#
#         project = Project.objects.get(id=project.id)
#         self.assertNotEqual(project.number, '1')
#         self.assertNotEqual(project.owner, user2)
#         self.assertNotEqual(project.temperature_unit, 'C')
#
#         project2 = Project.objects.create(
#             number='3',
#             owner=user2,
#             load_unit='kN',
#             move_unit='mm',
#             temperature_unit='C',
#         )
#
#         # Попытка изменить чужой проект
#         # Не должно получиться
#         request_data = {
#             'number': '4',
#             'temperature_unit': 'F',
#         }
#
#         url = f'/api/projects/{project2.id}/'
#         response = self.client.patch(url, data=request_data, format='json', content_type='application/json',
#                                      headers=headers)
#         self.assertEqual(response.status_code, 404, msg=response.content.decode('utf8'))
#
#         code = response.json()['code']
#         self.assertEqual(code, 'not_found')
#
#         project2 = Project.objects.get(id=project2.id)
#         self.assertEqual(project2.number, '3')
#         self.assertEqual(project2.temperature_unit, 'C')
