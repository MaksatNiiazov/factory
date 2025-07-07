from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from rest_framework.authentication import TokenAuthentication, BaseAuthentication

from user_sessions.models import Session

from kernel.api.exceptions import InvalidToken, TokenExpired, UserNotFound
from kernel.models import ApiToken


class LoginAPINoAuthentication(BaseAuthentication):
    """
    Для /api/users/login/, сделаем чтобы не была проверка на Bearer токен,
    иначе будут различные исключения с BearerAuthentication.
    """

    def authenticate(self, request):
        if request.path == "/api/users/login/":
            return AnonymousUser(), None


class BearerAuthentication(TokenAuthentication):
    """
    Авторизация через ключ сессии

    Authorization: Bearer session_key
    """
    keyword = 'Bearer'
    model = Session

    def authenticate_credentials(self, key):
        model = self.get_model()

        try:
            session = model.objects.select_related('user').get(session_key=key)
        except model.DoesNotExist:
            raise InvalidToken

        current_datetime = timezone.now()

        if session.expire_date < current_datetime:
            raise TokenExpired

        if not session.user.is_active:
            raise UserNotFound

        return session.user, session

    def authenticate_header(self, request):
        return self.keyword


class ApiTokenAuthentication(TokenAuthentication):
    """
    Авторизация через ApiToken пользователя

    Authorization: Token token
    """

    keyword = 'Token'
    model = ApiToken

    def authenticate_credentials(self, key):
        model = self.get_model()

        try:
            token = model.objects.select_related('user').get(token=key)
        except model.DoesNotExist:
            raise InvalidToken

        if not token.user.is_active:
            raise UserNotFound

        return token.user, token

    def authenticate_header(self, request):
        return self.keyword
