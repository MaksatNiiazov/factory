from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory

from faker import Faker

User = get_user_model()
faker = Faker()


class TestHelper:
    """
    Класс-помощник для теста
    """

    def give_permissions(self, user, permissions):
        """
        Дать разрешение пользователю
        """
        from django.contrib.auth.models import Permission

        for permission in permissions:
            app, codename = permission.split('.')
            permission = Permission.objects.get(
                content_type__app_label=app,
                codename=codename,
            )
            user.user_permissions.add(permission)

    def get_auth_token(self, user):
        from django.contrib.auth import login
        from user_sessions.models import Session

        factory = RequestFactory()
        request = factory.get('/')

        login(request, user)

        session = Session.objects.filter(user=user).first()
        return session.key

    def create_user(self):
        last_name = faker.last_name()
        first_name = faker.first_name()

        user = User(
            email=f'{last_name}.{first_name}@example.com'.lower(),
            last_name=last_name,
            first_name=first_name,
            status=User.INTERNAL_USER,
        )
        user.set_password('test123')
        user.save()

        return user
#
#
# class UserAPITestCase(TestCase):
#     """
#     Тест-кейсы по API для работы с пользователем.
#     """
#
#     def setUp(self):
#         self.helper = TestHelper()
#         self.user = self.helper.create_user()
#
#     def authenticate(self, email, password=None):
#         # Авторизуем пользователя
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
#         """
#         Проверка /api/users/ (GET) для получения списка пользователей.
#         """
#
#         # Попробуем получить списка пользователей без авторизации
#         # Результат: Не должно получиться
#         response = self.client.get('/api/users/')
#         self.assertEqual(response.status_code, 403)
#
#         code = response.json()['code']
#         self.assertEqual(code, 'not_authenticated')
#
#         # Попробуем получить список пользователей с авторизации
#         # Результат: Не должно получиться, у пользователя нет прав на это
#         headers = self.authenticate(self.user.email)
#         response = self.client.get('/api/users/', headers=headers)
#         self.assertEqual(response.status_code, 403)
#
#         code = response.json()['code']
#         self.assertEqual(code, 'permission_denied')
#
#         # Попробуем получить список пользователей (есть права)
#         # Результат: Есть один пользователь в списке
#         self.helper.give_permissions(self.user, ['kernel.view_user'])
#         response = self.client.get('/api/users/', headers=headers)
#         self.assertEqual(response.status_code, 200)
#
#         users = response.json()['results']
#         self.assertEqual(len(users), 1)
#
#         user = users[0]
#         self.assertEqual(user['email'], self.user.email)
#         self.assertEqual(user['last_name'], self.user.last_name)
#         self.assertEqual(user['first_name'], self.user.first_name)
#         self.assertIn('kernel.view_user', user['permissions'])
#
#         # Создаем еще одного пользователя
#         self.helper.create_user()
#         response = self.client.get('/api/users/', headers=headers)
#         self.assertEqual(response.status_code, 200)
#
#         users = response.json()['results']
#         self.assertEqual(len(users), 2)
#
#     def test_login_failed(self):
#         # Попробуем авторизоваться без правильного пароля
#         request_data = {
#             'username': self.user.email,
#             'password': 'wrong_password',
#         }
#
#         response = self.client.post('/api/users/login/', data=request_data)
#         self.assertEqual(response.status_code, 403)
#         code = response.json()['code']
#         self.assertEqual(code, 'authentication_failed')
#
#     def test_logout(self):
#         """
#         Проверка /api/users/logout/, выход из системы
#         """
#         response = self.client.get('/api/users/me/')
#         self.assertEqual(response.status_code, 403)
#         code = response.json()['code']
#         self.assertEqual(code, 'not_authenticated')
#
#         response = self.client.post('/api/users/logout/')
#         self.assertEqual(response.status_code, 403)
#         code = response.json()['code']
#         self.assertEqual(code, 'not_authenticated')
#
#         headers = self.authenticate(self.user.email)
#
#         response = self.client.get('/api/users/me/', headers=headers)
#         self.assertEqual(response.status_code, 200)
#         user = response.json()
#         self.assertEqual(user['email'], self.user.email)
#
#         response = self.client.post('/api/users/logout/', headers=headers)
#         self.assertEqual(response.status_code, 200, msg=response.content.decode('utf8'))
#
#         response = self.client.get('/api/users/me/', headers=headers)
#         self.assertEqual(response.status_code, 403)
#         code = response.json()['code']
#         self.assertEqual(code, 'authentication_failed')
#
#     def test_create_user(self):
#         """
#         Проверка /api/users/ (POST) для создания нового пользователя
#         """
#         request_data = {
#             'email': 'test.user@example.com',
#             'last_name': 'Test',
#             'first_name': 'User',
#             'status': 'external',
#             'password': 'test321',
#         }
#
#         # Попробуем создать пользователя без авторизации
#         response = self.client.post('/api/users/', data=request_data)
#         self.assertEqual(response.status_code, 403)
#
#         code = response.json()['code']
#         self.assertEqual(code, 'not_authenticated')
#
#         # Попробуем создать пользователя с авторизацией, но без прав
#         headers = self.authenticate(self.user.email)
#         response = self.client.post('/api/users/', data=request_data, headers=headers)
#         self.assertEqual(response.status_code, 403)
#
#         code = response.json()['code']
#         self.assertEqual(code, 'permission_denied')
#
#         # Попробуем создать пользователя с правами
#         self.helper.give_permissions(self.user, ['kernel.add_user', 'kernel.view_user'])
#         response = self.client.post('/api/users/', data=request_data, headers=headers)
#         self.assertEqual(response.status_code, 201, msg=response.content.decode('utf8'))
#
#         user = response.json()
#         self.assertEqual(user['email'], 'test.user@example.com')
#         self.assertEqual(user['last_name'], 'Test')
#         self.assertEqual(user['first_name'], 'User')
#         self.assertIsNone(user['middle_name'])
#
#         # Попробуем авторизоваться этим пользователем, чтобы проверить что пароль верный
#         request_data = {
#             'username': 'test.user@example.com',
#             'password': 'test321',
#         }
#         response = self.client.post('/api/users/login/', data=request_data)
#         self.assertEqual(response.status_code, 200, msg=response.content.decode('utf8'))
#
#         # Проверим что будет с неправильным паролем
#         request_data = {
#             'username': 'test.user@example.com',
#             'password': 'test123',
#         }
#         response = self.client.post('/api/users/login/', data=request_data)
#         self.assertEqual(response.status_code, 403)
#
#         code = response.json()['code']
#         self.assertEqual(code, 'authentication_failed')
#
#     def test_update_user(self):
#         """
#         Проверка /api/users/{id}/ (POST) для изменения пользователя
#         """
#         user2 = self.helper.create_user()
#
#         change_data_1 = {
#             'last_name': 'Test',
#         }
#
#         change_data_2 = {
#             'last_name': 'Test2',
#             'first_name': 'User1',
#         }
#
#         change_data_3 = {
#             'last_name': 'Test3',
#             'first_name': 'User2',
#             'password': 'test234',
#         }
#
#         change_data_4 = {
#             'password': 'test345',
#         }
#
#         # Попробуем изменить пользователя без авторизации
#         url = f'/api/users/{user2.id}/'
#         response = self.client.post(url, data=change_data_1)
#         self.assertEqual(response.status_code, 403)
#         code = response.json()['code']
#         self.assertEqual(code, 'not_authenticated')
#
#         # Попробуем изменить пользователя с авторизацией, но без прав
#         headers = self.authenticate(self.user.email)
#         response = self.client.patch(url, data=change_data_1, format='json', headers=headers)
#         self.assertEqual(response.status_code, 403, msg=response.content.decode('utf8'))
#         code = response.json()['code']
#         self.assertEqual(code, 'permission_denied')
#
#         # Попробуем изменить пользователя с правами
#         self.helper.give_permissions(self.user, ['kernel.change_user', 'kernel.view_user'])
#         response = self.client.patch(url, data=change_data_1, content_type='application/json', headers=headers)
#         self.assertEqual(response.status_code, 200, msg=response.content.decode('utf8'))
#
#         user = response.json()
#         self.assertEqual(user['last_name'], 'Test')
#         self.assertEqual(user['first_name'], user2.first_name)
#
#         response = self.client.get(url, headers=headers)
#         self.assertEqual(response.status_code, 200)
#
#         user = response.json()
#         self.assertEqual(user['last_name'], 'Test')
#         self.assertEqual(user['first_name'], user2.first_name)
#
#         # Попробуем войти старым паролем
#         request_data = {
#             'username': user2.email,
#             'password': 'test123',
#         }
#         self.client.cookies.clear()
#         response = self.client.post('/api/users/login/', data=request_data)
#         self.assertEqual(response.status_code, 200, msg=response.content.decode('utf8'))
#
#         # Меняем еще раз
#         response = self.client.patch(url, data=change_data_2, content_type='application/json', headers=headers)
#         self.assertEqual(response.status_code, 200, msg=response.content.decode('utf8'))
#
#         user = response.json()
#         self.assertEqual(user['last_name'], 'Test2')
#         self.assertEqual(user['first_name'], 'User1')
#
#         response = self.client.get(url, headers=headers)
#         self.assertEqual(response.status_code, 200)
#
#         user = response.json()
#         self.assertEqual(user['last_name'], 'Test2')
#         self.assertEqual(user['first_name'], 'User1')
#
#         # Попробуем войти старым паролем
#         request_data = {
#             'username': user2.email,
#             'password': 'test123',
#         }
#         self.client.cookies.clear()
#         response = self.client.post('/api/users/login/', data=request_data)
#         self.assertEqual(response.status_code, 200, msg=response.content.decode('utf8'))
#
#         # Меняем еще раз
#         response = self.client.patch(url, data=change_data_3, content_type='application/json', headers=headers)
#         self.assertEqual(response.status_code, 200)
#
#         user = response.json()
#         self.assertEqual(user['last_name'], 'Test3')
#         self.assertEqual(user['first_name'], 'User2')
#
#         response = self.client.get(url, headers=headers)
#         self.assertEqual(response.status_code, 200)
#
#         user = response.json()
#         self.assertEqual(user['last_name'], 'Test3')
#         self.assertEqual(user['first_name'], 'User2')
#
#         # Попробуем войти старым паролем
#         request_data = {
#             'username': user2.email,
#             'password': 'test123',
#         }
#         response = self.client.post('/api/users/login/', data=request_data)
#         self.assertEqual(response.status_code, 403, msg=response.content.decode('utf8'))
#
#         # Попробуем войти новым паролем
#         request_data = {
#             'username': user2.email,
#             'password': 'test234',
#         }
#         self.client.cookies.clear()
#         response = self.client.post('/api/users/login/', data=request_data)
#         self.assertEqual(response.status_code, 200, msg=response.content.decode('utf8'))
#
#         # Меняем еще раз
#         response = self.client.patch(url, data=change_data_4, content_type='application/json', headers=headers)
#         self.assertEqual(response.status_code, 200)
#
#         user = response.json()
#         self.assertEqual(user['last_name'], 'Test3')
#         self.assertEqual(user['first_name'], 'User2')
#
#         response = self.client.get(url, headers=headers)
#         self.assertEqual(response.status_code, 200)
#
#         user = response.json()
#         self.assertEqual(user['last_name'], 'Test3')
#         self.assertEqual(user['first_name'], 'User2')
#
#         # Попробуем войти старым паролем
#         request_data = {
#             'username': user2.email,
#             'password': 'test234',
#         }
#         response = self.client.post('/api/users/login/', data=request_data)
#         self.assertEqual(response.status_code, 403, msg=response.content.decode('utf8'))
#
#         # Попробуем войти новым паролем
#         request_data = {
#             'username': user2.email,
#             'password': 'test345',
#         }
#         response = self.client.post('/api/users/login/', data=request_data)
#         self.assertEqual(response.status_code, 200, msg=response.content.decode('utf8'))
