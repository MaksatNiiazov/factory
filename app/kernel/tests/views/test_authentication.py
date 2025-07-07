from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from user_sessions.models import Session
from kernel.models import ApiToken
from kernel.api.authentication import BearerAuthentication, ApiTokenAuthentication
from kernel.api.exceptions import UserNotFound, InvalidToken, TokenExpired
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()


class AuthenticationTestCase(APITestCase):
    def setUp(self):
        """Создаем тестового пользователя и получаем токен аутентификации."""
        self.user = User.objects.create_user(email="testuser@example.com", password="testpass", is_active=True)

        # Логинимся и получаем токен
        response = self.client.post(reverse('user-login'), {
            'username': 'testuser@example.com',
            'password': 'testpass'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.content.decode('utf-8'))

        # Сохраняем токен и передаем в заголовки
        self.token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Создаем сессию для BearerAuthentication
        self.session = Session.objects.create(
            user=self.user,
            session_key="valid_session_key",
            expire_date=timezone.now() + timezone.timedelta(days=1)
        )

        # Создаем API-токен для ApiTokenAuthentication
        self.api_token = ApiToken.objects.create(user=self.user, token="valid_api_token")

    ### Тесты BearerAuthentication ###

    def test_bearer_authentication_valid_session(self):
        """Успешная аутентификация по сессионному ключу."""
        auth = BearerAuthentication()
        user, session = auth.authenticate_credentials("valid_session_key")
        self.assertEqual(user, self.user)
        self.assertEqual(session, self.session)

    def test_bearer_authentication_invalid_token(self):
        """Ошибка при неверном session_key."""
        auth = BearerAuthentication()
        with self.assertRaises(InvalidToken):
            auth.authenticate_credentials("invalid_session_key")

    def test_bearer_authentication_expired_session(self):
        """Ошибка при истекшей сессии."""
        self.session.expire_date = timezone.now() - timezone.timedelta(days=1)
        self.session.save()

        auth = BearerAuthentication()
        with self.assertRaises(TokenExpired):
            auth.authenticate_credentials("valid_session_key")

    def test_bearer_authentication_inactive_user(self):
        """Ошибка, если пользователь не активен."""
        self.user.is_active = False
        self.user.save()

        auth = BearerAuthentication()
        with self.assertRaises(UserNotFound):
            auth.authenticate_credentials("valid_session_key")

    def test_bearer_authentication_header(self):
        """Проверка заголовка аутентификации."""
        auth = BearerAuthentication()
        self.assertEqual(auth.authenticate_header(None), "Bearer")

    ### Тесты ApiTokenAuthentication ###

    def test_api_token_authentication_valid_token(self):
        """Успешная аутентификация через API-токен."""
        auth = ApiTokenAuthentication()
        user, token = auth.authenticate_credentials("valid_api_token")
        self.assertEqual(user, self.user)
        self.assertEqual(token, self.api_token)

    def test_api_token_authentication_invalid_token(self):
        """Ошибка при неверном API-токене."""
        auth = ApiTokenAuthentication()
        with self.assertRaises(InvalidToken):
            auth.authenticate_credentials("invalid_api_token")

    def test_api_token_authentication_inactive_user(self):
        """Ошибка, если пользователь деактивирован."""
        self.user.is_active = False
        self.user.save()

        auth = ApiTokenAuthentication()
        with self.assertRaises(UserNotFound):
            auth.authenticate_credentials("valid_api_token")

    def test_api_token_authentication_header(self):
        """Проверка заголовка аутентификации API-токена."""
        auth = ApiTokenAuthentication()
        self.assertEqual(auth.authenticate_header(None), "Token")
