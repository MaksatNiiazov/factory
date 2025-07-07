import logging

from django.db.models import ProtectedError
from django.utils.translation import gettext_lazy as _
from rest_framework import status

from rest_framework.exceptions import ValidationError, NotFound, AuthenticationFailed, APIException
from rest_framework.response import Response


logger = logging.getLogger(__name__)


class UserNotFound(NotFound):
    default_code = 'user_not_found'
    default_detail = _('Пользователь не найден.')


class UserWithCRMLoginNotFound(NotFound):
    default_code = 'user_with_crm_login_not_found'
    default_detail = _('Пользователь с указанным CRM логином не найден.')


class InvalidToken(AuthenticationFailed):
    default_code = 'invalid_token'
    default_detail = _('Неверный токен.')


class TokenExpired(AuthenticationFailed):
    default_code = 'token_expired'
    default_detail = _('Токен истек.')


class DependentError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = 'dependent_error'
    default_detail = _('Существует зависимые объекты.')


def custom_exception_handler(exc, context):
    """
    Обработчик при исключении для API-точки
    """
    from rest_framework.views import exception_handler

    response = exception_handler(exc, context)

    if response is None:
        data = {
            'detail': str(exc),
            'code': 'internal_server_error',
        }
        response = Response(data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if isinstance(exc, ValidationError):
        fields = response.data
        response.data = {'fields': fields, 'code': 'validation_error'}
    elif isinstance(exc, ProtectedError):
        response.data = {
            'detail': 'Невозможно удалить объект, так как на него есть зависимые данные.',
            'code': 'protected_error',
        }
        response.status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, APIException):
        response.data['code'] = response.data['detail'].code
    else:
        logger.exception("Non-APIException raised")

    response.data['status_code'] = response.status_code

    return response
