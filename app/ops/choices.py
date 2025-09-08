from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

from kernel.mixins import MaxLengthMixin


class ProjectStatus(MaxLengthMixin, TextChoices):
    """
    Перечисление возможных статусов проекта.
    """
    DRAFT = 'draft', _('Черновик')
    SENT = 'sent', _('Отправлен')
    DELETED = 'deleted', _('Удалён')


class LoadUnit(MaxLengthMixin, TextChoices):
    """
    Единицы измерения нагрузки.
    """
    KN = 'kN', _('kN')


class MoveUnit(MaxLengthMixin, TextChoices):
    """
    Единицы измерения перемещения.
    """
    MM = 'mm', _('mm')


class TemperatureUnit(MaxLengthMixin, TextChoices):
    """
    Единицы измерения температуры.
    """
    CELSIUS = 'C', _('C')
    FAHRENHEIT = 'F', _('F')


class AttributeType(MaxLengthMixin, TextChoices):
    """
    Перечисление типов атрибутов для использования в моделях и формах.
    """
    STRING = 'string', _('Строка')
    INTEGER = 'integer', _('Целое число')
    NUMBER = 'number', _('Число')
    BOOLEAN = 'boolean', _('Да/Нет')
    DATETIME = 'datetime', _('Дата/Время')
    DATE = 'date', _('Дата')
    CATALOG = 'catalog', _('Справочник')


class AttributeCatalog(MaxLengthMixin, TextChoices):
    """
    Перечисление справочных значений для параметров атрибутов.
    """
    NOMINAL_DIAMETER = 'NominalDiameter', _('Номинальный диаметр')
    PIPE_DIAMETER = 'PipeDiameter', _('Диаметр трубы')
    LOAD_GROUP = 'LoadGroup', _('Нагрузочная группа')
    MATERIAL = 'Material', _('Материал')
    COVERING_TYPE = 'CoveringType', _('Тип покрытия')
    COVERING = 'Covering', _('Покрытие')
    SUPPORT_DISTANCE = 'SupportDistance', _('Расстояние между опорами')


class ERPSyncStatus(TextChoices):
    PENDING = 'pending', _('В готовности')
    IN_PROGRESS = 'in_progress', _('Идет')
    SUCCESS = 'success', _('Успешно')
    ERROR = 'error', _('Ошибка')


class ERPSyncType(TextChoices):
    ITEM = 'item', _('Изделие/Деталь/Сборочная единица')
    PROJECT = 'project', _('Проект')


class ERPSyncLogType(TextChoices):
    HTTP_REQUEST = 'http_request', _('HttpRequest')
    DEBUG = 'debug', _('DEBUG')
    EXCEPTION = 'exception', _('Exception')


class EstimatedState(MaxLengthMixin, TextChoices):
    COLD_LOAD = 'cold', _('Холодная нагрузка')
    HOT_LOAD = 'hot', _('Горячая нагрузка')


class AttributeUsageChoices(MaxLengthMixin, TextChoices):
    """
    Справочник использования атрибутов в расчетах и характеристиках изделии.
    """
    CUSTOM = "custom", _("Произвольный атрибут")
    SYSTEM_HEIGHT = "system_height", _("Используется для подсчета высоты системы")
    CONNECTION_SIZE = "connection_size", _("Присоединительный размер")
    MIN_LENGTH = "min_length", _("Минимальная длина")
    SYSTEM_WEIGHT = "system_weight", _("Используется для расчета веса")
    F_INITIAL = "f_initial", _("Усилие, когда пружина полностью разжата")
    E_INITIAL = "e_initial", _("Монтажная длина корпуса в сжатом (рабочем) состоянии")
    DN = "dn", _("DN")
    LOAD_GROUP = "load_group", _("Нагрузочная группа")
    LOAD = "load", _("Нагрузка")
    LENGTH = "length", _("Длина")
    THICKNESS = "thickness", _("Толщина")
    SIZE = "size", _("Типоразмер")
    RATED_STROKE = "rated_stroke", _("Номинальный ход")
    INSTALLATION_SIZE = "installation_size", _("Пролет")
    PIPE_DIAMETER = "pipe_diameter", _("Диаметр трубы")
    CLAMP_LOAD = "clamp_load", _("Нагрузка для хомутов")

