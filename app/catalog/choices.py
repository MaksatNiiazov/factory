from django.db.models import TextChoices, IntegerChoices

from django.utils.translation import gettext_lazy as _

from kernel.mixins import MaxLengthMixin


class FieldTypeChoices(TextChoices):
    INT = 'int', _('Целое число')
    FLOAT = 'float', _('Число с плавающей точкой')
    STR = 'str', _('Строка')
    BOOL = 'bool', _('Логическое значение')


class MaterialType(TextChoices):
    A = 'A', _('Аустенитные стали')
    F = 'F', _('Ферритные')
    N = 'N', _('Сплавы на основе никеля')


class Standard(IntegerChoices):
    RF = 1, _('РФ')
    EN = 2, _('EN')


class SeriesNameChoices(MaxLengthMixin, TextChoices):
    STANDARD_SERIES = 'standard_series', _('Standard Series')
    L_SERIES = 'l_series', _('L Series')


class PipeDirectionChoices(MaxLengthMixin, TextChoices):
    X = 'x', 'X'
    Y = 'y', 'Y'
    Z = 'z', 'Z'


class ComponentGroupType(MaxLengthMixin, TextChoices):
    STUDS = "studs", _("Список шпилек")
    COUPLING = "coupling", _("Список муфт")
    FASTENER = "fastener", _("Список крепежа")
    SERIES_SELECTABLE = "series_selectable", _("С выбором серии")


class ClampSelectionEntryResult(MaxLengthMixin, TextChoices):
    UNLIMITED = "unlimited", _("Собирается без ограничений")
    ADAPTER_REQUIRED = "adapter_required", _("Собирается через переходник")
    NOT_POSSIBLE = "not_possible", _("Не собирается")
