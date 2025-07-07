from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError


class DirectoryNotFound(NotFound):
    default_code = 'directory_not_found'
    default_detail = _('Справочник не найден.')


class DirectoryFieldNotFound(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Поле не найдено в справочнике.')
    default_code = 'field_not_found'
