from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

from kernel.mixins import MaxLengthMixin


class TaskType(MaxLengthMixin, TextChoices):
    IMPORT = 'import', _('Импорт')
    EXPORT = 'export', _('Экспорт')


class TaskStatus(MaxLengthMixin, TextChoices):
    NEW = 'new', _('Новый')
    PROCESSING = 'processing', _('В процессе')
    DONE = 'done', _('Завершено')
    ERROR = 'error', _('Ошибка')
    ABORTED = 'aborted', _('Прервано')


class TaskResultType(MaxLengthMixin, TextChoices):
    FILE = 'file', _('Файл')
    TEXT = 'text', _('Текст')
    JSON = 'json', _('JSON')
