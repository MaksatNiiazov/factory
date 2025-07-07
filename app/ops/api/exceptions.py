from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import APIException, NotFound
from rest_framework import status


class ItemNotFound(NotFound):
    default_code = 'item_not_found'
    default_detail = _('Изделие/Деталь/Сборочная единица не найдена.')


class ProjectNotFound(NotFound):
    default_code = 'project_not_found'
    default_detail = _('Проект не найден.')


class FormatNotSupported(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Формат файла не поддерживается.')
    default_code = 'format_not_supported'


class ResourceNotFound(NotFound):
    default_code = 'resource_not_found'
    default_detail = _('Ресурс для импорта/экспорта не найден.')


class ERPAPIException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Произошла ошибка при взаимодействии ERP.')
    default_code = 'erp_error'
