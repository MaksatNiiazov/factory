from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

from django.utils.translation import gettext_lazy as _
from pybarker.django.db.models import ReadableJSONField

from pybarker.contrib.modelshistory.models import HistoryModelTracker

from catalog.choices import (
    MaterialType, FieldTypeChoices, Standard, SeriesNameChoices, PipeDirectionChoices,
    ComponentGroupType, ClampSelectionEntryResult, SelectionType,
)
from catalog.managers import ClampMaterialCoefficientManager, PipeDiameterSoftDeleteManager, PipeDiameterAllObjectsManager
from kernel.mixins import SoftDeleteModelMixin
from ops.marking_compiler import get_jinja2_env


class CatalogMixin(models.Model):
    """
    Базовый класс для всех каталогов.
    """

    class Meta:
        abstract = True

    @property
    def display_name(self):
        return str(self)


class Directory(SoftDeleteModelMixin, models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Название"))
    display_name_template = models.TextField(blank=True, default="", verbose_name=_("Шаблон отображения"))

    class Meta:
        verbose_name = _("Кастомный справочник")
        verbose_name_plural = _("Кастомные справочники")
        default_permissions = ()
        permissions = (
            ("add_directory", _("Может создавать кастомные справочники")),
            ("change_directory", _("Может изменять кастомные справочники")),
            ("delete_directory", _("Может удалять кастомные справочники")),
            ("view_directory", _("Может просматривать кастомные справочники")),
        )

    def save(self, *args, **kwargs):
        old_instance = None

        if self.pk:
            try:
                old_instance = Directory.objects.get(pk=self.pk)
            except Directory.DoesNotExist:
                old_instance = None

        super().save(*args, **kwargs)

        if old_instance and old_instance.display_name_template != self.display_name_template:
            self.refresh_all_entries_display_name()

    def refresh_all_entries_display_name(self):
        for entry in self.entries.all():
            entry.refresh_display_name()

    def __str__(self):
        return self.name


class DirectoryField(SoftDeleteModelMixin, models.Model):
    directory = models.ForeignKey(
        Directory, on_delete=models.CASCADE, related_name="fields", verbose_name=_("Справочник")
    )
    name = models.CharField(max_length=255, verbose_name=_("Название поля"))
    field_type = models.CharField(max_length=10, choices=FieldTypeChoices.choices, verbose_name=_("Тип поля"))

    class Meta:
        verbose_name = _("Поле в кастомном справочнике")
        verbose_name_plural = _("Поля в кастомном справочнике")
        default_permissions = ()
        permissions = (
            ("add_directoryfield", _("Может добавлять поля в кастомный справочник")),
            ("change_directoryfield", _("Может изменять поля в кастомном справочнике")),
            ("delete_directoryfield", _("Может удалять поля в кастомном справочнике")),
            ("view_directoryfield", _("Может просматривать поля в кастомном справочнике")),
        )

    def __str__(self):
        return f'{self.directory.name} -> {self.name} ({self.field_type})'


class DirectoryEntry(SoftDeleteModelMixin, models.Model):
    directory = models.ForeignKey(
        Directory, on_delete=models.CASCADE, related_name="entries", verbose_name=_("Справочник")
    )
    display_name = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("Отображаемое имя")
    )
    display_name_errors = ReadableJSONField(blank=True, default=list, verbose_name=_("Ошибки при генерации имени"))

    class Meta:
        verbose_name = _("Запись в кастомном справочнике")
        verbose_name_plural = _("Записи в кастомном справочнике")
        default_permissions = ()
        permissions = (
            ("add_directoryentry", _("Может добавлять записи в кастомный справочник")),
            ("change_directoryentry", _("Может изменять записи в кастомном справочнике")),
            ("delete_directoryentry", _("Может удалять записи в кастомном справочнике")),
            ("view_directoryentry", _("Может просматривать записи в кастомном справочнике")),
        )

    def refresh_display_name(self):
        env = get_jinja2_env()

        context = {}
        for val_obj in self.values.select_related('directory_field'):
            context[val_obj.directory_field.name] = val_obj.value

        template_str = self.directory.display_name_template or ''
        try:
            template = env.from_string(template_str)
            rendered = template.render(context)
            self.display_name = rendered
            self.display_name_errors = []
        except Exception as e:
            self.display_name = 'ERROR'
            self.display_name_errors = [str(e)]

        self.save(update_fields=['display_name', 'display_name_errors'])

    def __str__(self):
        return f'Запись #{self.id} в {self.directory.name}'


class DirectoryEntryValue(SoftDeleteModelMixin, models.Model):
    entry = models.ForeignKey(DirectoryEntry, on_delete=models.CASCADE, related_name="values", verbose_name="Запись")
    directory_field = models.ForeignKey(
        DirectoryField, on_delete=models.CASCADE, related_name="values", verbose_name=_("Поле")
    )

    int_value = models.IntegerField(null=True, blank=True, verbose_name=_("Целое число"))
    float_value = models.FloatField(null=True, blank=True, verbose_name=_("Вещественное число"))
    str_value = models.CharField(null=True, blank=True, verbose_name=_("Строка"))
    bool_value = models.BooleanField(null=True, blank=True, verbose_name=_("Логическое значение"))

    class Meta:
        verbose_name = _("Значение поля в записи кастомного справочника")
        verbose_name_plural = _("Значения полей в записях кастомного справочника")
        default_permissions = ()
        permissions = (
            ("add_directoryentryvalue", _("Может добавлять значения полей в записи кастомного справочника")),
            ("change_directoryentryvalue", _("Может изменять значения полей в записи кастомного справочника")),
            ("delete_directoryentryvalue", _("Может удалять значения полей в записи кастомного справочника")),
            ("view_directoryentryvalue", _("Может просматривать значения полей в записи кастомного справочника")),
        )

    def __str__(self):
        return f"{self.entry.display_name} -> {self.directory_field.name} ({self.value})"

    def clean(self):
        super().clean()
        if self.entry.directory_id != self.directory_field.directory_id:
            raise ValidationError('Поле и запись должны относиться к одному и тому же справочнику.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def value(self):
        ftype = self.directory_field.field_type

        if ftype == FieldTypeChoices.INT:
            return self.int_value
        elif ftype == FieldTypeChoices.FLOAT:
            return self.float_value
        elif ftype == FieldTypeChoices.STR:
            return self.str_value
        elif ftype == FieldTypeChoices.BOOL:
            return self.bool_value
        return None

    def set_value(self, new_value):
        ftype = self.directory_field.field_type

        try:
            if ftype == FieldTypeChoices.INT:
                self.int_value = int(new_value) if new_value is not None else None
                self.float_value = None
                self.str_value = None
                self.bool_value = None
            elif ftype == FieldTypeChoices.FLOAT:
                self.int_value = None
                self.float_value = float(new_value) if new_value is not None else None
                self.str_value = None
                self.bool_value = None
            elif ftype == FieldTypeChoices.STR:
                self.int_value = None
                self.float_value = None
                self.str_value = str(new_value) if new_value is not None else None
                self.bool_value = None
            elif ftype == FieldTypeChoices.BOOL:
                self.int_value = None
                self.float_value = None
                self.str_value = None

                if isinstance(new_value, str):
                    if new_value.lower() in ['true', '1']:
                        self.bool_value = True
                    elif new_value.lower() in ['false', '0']:
                        self.bool_value = False
                    else:
                        raise ValidationError(f'Значение "{new_value}" не может быть преобразовано к bool')
                else:
                    self.bool_value = bool(new_value) if new_value is not None else None
            self.save()
            self.entry.refresh_display_name()
        except (ValueError, TypeError) as e:
            raise ValidationError(f'Невозможно преобразовать значение "{new_value}" к типу {ftype}: {e}')


class NominalDiameter(CatalogMixin, SoftDeleteModelMixin, models.Model):
    dn = models.PositiveSmallIntegerField(verbose_name=_("Номинальный диаметр"), unique=True)

    historylog = HistoryModelTracker(excluded_fields=("id",), root_model="self", root_id=lambda ins: ins.id)

    def __str__(self):
        return f"DN{self.dn}"

    class Meta:
        verbose_name = _("Номинальный диаметр")
        verbose_name_plural = _("Номинальные диаметры")
        ordering = ["dn"]
        default_permissions = ()
        permissions = (
            ("add_nominaldiameter", _("Может добавлять записи в справочник номинальных диаметров")),
            ("change_nominaldiameter", _("Может изменять записи в справочник номинальных диаметров")),
            ("delete_nominaldiameter", _("Может удалять записи в справочник номинальных диаметров")),
            ("view_nominaldiameter", _("Может просматривать записи в справочник номинальных диаметров")),
        )

class PipeDiameter(CatalogMixin, SoftDeleteModelMixin, models.Model):
    class Option(models.IntegerChoices):
        DN_A = 1, _("А")
        DN_B = 2, _("Б")
        DN_V = 3, _("В")
        __empty__ = "--------"

    dn = models.ForeignKey(NominalDiameter, verbose_name=_("Номинальный диаметр"), on_delete=models.PROTECT)
    option = models.PositiveSmallIntegerField(
        verbose_name=_("Исполнение"), choices=Option.choices, null=True, blank=True
    )
    standard = models.PositiveSmallIntegerField(verbose_name=_("Стандарт"), choices=Standard.choices)
    size = models.FloatField(verbose_name=_("Фактический размер, мм"), validators=[MinValueValidator(0.0)])

    historylog = HistoryModelTracker(excluded_fields=("id",), root_model="self", root_id=lambda ins: ins.id)

    @property
    def erp_display_name(self):
        return f"{self.dn.dn}{self.get_option_display()}" if self.option else f"{self.dn.dn}"

    def __str__(self):
        return f"DN{self.dn.dn}({self.get_option_display()}) (Размер={self.size} мм)" if self.option else f"DN{self.dn.dn} (Размер={self.size} мм)"

    objects = PipeDiameterSoftDeleteManager()
    all_objects = PipeDiameterAllObjectsManager()

    class Meta:
        verbose_name = _("Номинальный диаметр трубы")
        verbose_name_plural = _("Номинальные диаметры труб")
        ordering = ["standard", "dn"]
        constraints = [
            models.UniqueConstraint(fields=("dn", "option", "standard"), name="unique_pipe_diameter"),
        ]
        default_permissions = ()
        permissions = (
            ("add_pipediameter", _("Может добавлять записи в справочник номинальных диаметров труб")),
            ("change_pipediameter", _("Может изменять записи в справочник номинальных диаметров труб")),
            ("delete_pipediameter", _("Может удалять записи в справочник номинальных диаметров труб")),
            ("view_pipediameter", _("Может просматривать записи в справочник номинальных диаметров труб")),
        )


class LoadGroup(CatalogMixin, SoftDeleteModelMixin, models.Model):
    lgv = models.IntegerField(verbose_name=_("LGV"))
    kn = models.IntegerField(verbose_name=_("kN"))

    historylog = HistoryModelTracker(excluded_fields=("id",), root_model="self", root_id=lambda ins: ins.id)

    class Meta:
        verbose_name = _("Нагрузочная группа")
        verbose_name_plural = _("Нагрузочные группы")
        default_permissions = ()
        permissions = (
            ("add_loadgroup", _("Может добавлять записи в справочник нагрузочных групп")),
            ("change_loadgroup", _("Может изменять записи в справочник нагрузочных групп")),
            ("delete_loadgroup", _("Может удалять записи в справочник нагрузочных групп")),
            ("view_loadgroup", _("Может просматривать записи в справочник нагрузочных групп")),
        )

    def __str__(self):
        return f"LGV={self.lgv} kN={self.kn}"


class Material(CatalogMixin, SoftDeleteModelMixin, models.Model):
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Наименование"))
    group = models.CharField(max_length=32, verbose_name=_("Группа"))

    type = models.CharField(
        max_length=1, choices=MaterialType.choices, null=True, blank=True, verbose_name=_("Тип материала"),
    )

    astm_spec = models.CharField(max_length=36, null=True, blank=True, verbose_name=_("Спецификация по стандарту ASTM"))
    asme_type = models.CharField(
        max_length=36, null=True, blank=True, verbose_name=_("Тип материала по классификации ASME"),
    )
    asme_uns = models.CharField(
        max_length=36, null=True, blank=True, verbose_name=_("Уникальный номер материала по классификации ASME"),
    )

    source = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("Стандарт"))

    min_temp = models.IntegerField(null=True, blank=True, verbose_name=_("Минимальная рабочая температура материала"))
    max_temp = models.IntegerField(null=True, blank=True, verbose_name=_("Максимальная рабочая температура материала"))
    max_exhaust_gas_temp = models.IntegerField(
        null=True, blank=True, verbose_name=_("Максимальная температура выхлопных газов"),
    )

    lz = models.FloatField(null=True, blank=True)

    density = models.FloatField(null=True, blank=True, verbose_name=_("Плотность"))
    spring_constant = models.FloatField(null=True, blank=True, verbose_name=_("Пружинная постоянная"))
    rp0 = models.IntegerField(null=True, blank=True, verbose_name=_("Предел текучести"))

    historylog = HistoryModelTracker(excluded_fields=("id",), root_model="self", root_id=lambda ins: ins.id)

    class Meta:
        verbose_name = _("Материал")
        verbose_name_plural = _("Материалы")
        default_permissions = ()
        permissions = (
            ("add_material", _("Может добавлять записи в справочник материалов")),
            ("change_material", _("Может изменять записи в справочник материалов")),
            ("delete_material", _("Может удалять записи в справочник материалов")),
            ("view_material", _("Может просматривать записи в справочник материалов")),
        )

    def is_stainless_steel(self) -> bool:
        """
        Проверяет, является ли материал нержавеющей сталью.
        """
        return self.type in [MaterialType.A, MaterialType.N]

    def is_black_metal(self) -> bool:
        """
        Проверяет, является ли материал черным металлом.
        """
        return self.type == MaterialType.F

    def clean(self) -> None:
        """
        Переопределяет метод clean для выполнения дополнительной валидации.

        Выполняет проверку, что максимальная рабочая температура (max_temp)
        не меньше минимальной рабочей температуры (min_temp). Если условие
        нарушается, вызывает ошибку валидации.
        """
        super().clean()

        if self.min_temp is not None and self.max_temp is not None:
            if self.max_temp < self.min_temp:
                raise ValidationError({
                    'max_temp': _('Максимальная температура не может быть меньше минимальной температуры.'),
                })

    def __str__(self) -> str:
        return str(self.name)


class CoveringType(CatalogMixin, SoftDeleteModelMixin, models.Model):
    numeric = models.IntegerField(verbose_name=_('Числовое значение'))
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Наименование'))
    description = models.TextField(null=True, blank=True, verbose_name=_('Описание'))

    historylog = HistoryModelTracker(excluded_fields=('id',), root_model='self', root_id=lambda ins: ins.id)

    class Meta:
        verbose_name = _('Тип покрытия')
        verbose_name_plural = _('Типы покрытий')
        ordering = ('numeric',)
        default_permissions = ()
        permissions = (
            ("add_coveringtype", _("Может добавлять запись в справочник типов покрытий")),
            ("change_coveringtype", _("Может изменять запись в справочник типов покрытий")),
            ("delete_coveringtype", _("Может удалять запись в справочник типов покрытий")),
            ("view_coveringtype", _("Может просматривать записи в справочник типов покрытий")),
        )

    def __str__(self):
        return str(self.name)


class Covering(CatalogMixin, SoftDeleteModelMixin, models.Model):
    name = models.CharField(max_length=255, verbose_name=_('Наименование'))
    description = models.TextField(null=True, blank=True, verbose_name=_('Описание'))

    historylog = HistoryModelTracker(excluded_fields=('id',), root_model='self', root_id=lambda ins: ins.id)

    class Meta:
        verbose_name = _('Покрытие')
        verbose_name_plural = _('Покрытия')
        ordering = ('name',)
        default_permissions = ()
        permissions = (
            ("add_covering", _("Может добавлять запись в справочник покрытий")),
            ("change_covering", _("Может изменять запись в справочник покрытий")),
            ("delete_covering", _("Может удалять запись в справочник покрытий")),
            ("view_covering", _("Может просматривать записи в справочник покрытий")),
        )

    def __str__(self):
        return str(self.name)


class SupportDistance(CatalogMixin, SoftDeleteModelMixin, models.Model):
    """
    Справочник расстояний между опорами.
    """
    name = models.CharField(max_length=255, verbose_name=_("Название"))
    value = models.FloatField(verbose_name=_("Расстояние между опорами, мм"), validators=[MinValueValidator(0.0)])

    class Meta:
        verbose_name = _("Расстояние между опорами")
        verbose_name_plural = _("Расстояния между опорами")
        ordering = ["value"]
        default_permissions = ()
        permissions = (
            ("add_supportdistance", _("Может добавлять записи в справочник расстояний между опорами")),
            ("change_supportdistance", _("Может изменять записи в справочник расстояний между опорами")),
            ("delete_supportdistance", _("Может удалять записи в справочник расстояний между опорами")),
            ("view_supportdistance", _("Может просматривать записи в справочник расстояний между опорами")),
        )

    def __str__(self):
        return f"{self.name} ({self.value} мм)"


class ProductClass(CatalogMixin, SoftDeleteModelMixin, models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Название"))

    class Meta:
        verbose_name = _("Класс изделия")
        verbose_name_plural = _("Классы изделий")
        default_permissions = ()
        permissions = (
            ("add_productclass", _("Может добавлять записи в справочник классов изделий")),
            ("change_productclass", _("Может изменять записи в справочник классов изделий")),
            ("delete_productclass", _("Может удалять записи в справочник классов изделий")),
            ("view_productclass", _("Может просматривать записи в справочник классов изделий")),
        )

    def __str__(self):
        return self.name


class ProductFamily(CatalogMixin, SoftDeleteModelMixin, models.Model):
    """
    Справочник семейства изделий.
    """
    product_class = models.ForeignKey(
        ProductClass, on_delete=models.PROTECT, related_name="product_families", verbose_name=_("Класс изделия"),
    )
    name = models.CharField(max_length=255, unique=True, verbose_name=_("Название семейства"))
    icon = models.ImageField(upload_to="product_families/", null=True, blank=True, verbose_name=_("Иконка"))

    is_upper_mount_selectable = models.BooleanField(
        default=False, blank=True, verbose_name=_("Доступен выбор верхнего крепления"),
    )
    has_rod = models.BooleanField(
        default=False, blank=True, verbose_name=_("Альтернативный расчет высоты за счет регулировки штока"),
    )

    selection_type = models.CharField(
        max_length=SelectionType.get_max_length(), null=True, blank=True, choices=SelectionType.choices,
        verbose_name=_("Тип подбора"),
    )

    class Meta:
        verbose_name = _("Семейство изделий")
        verbose_name_plural = _("Семейства изделий")
        ordering = ["name"]
        default_permissions = ()
        permissions = (
            ("add_productfamily", _("Может добавлять записи в справочник семейств изделий")),
            ("change_productfamily", _("Может изменять записи в справочник семейств изделий")),
            ("delete_productfamily", _("Может удалять записи в справочник семейств изделий")),
            ("view_productfamily", _("Может просматривать записи в справочник семейств изделий")),
        )

    def __str__(self):
        return self.name


class Load(CatalogMixin, SoftDeleteModelMixin, models.Model):
    series_name = models.CharField(
        max_length=SeriesNameChoices.get_max_length(), choices=SeriesNameChoices.choices,
        verbose_name=_("Наименование серии"),
    )
    size = models.PositiveIntegerField(verbose_name=_("Размер"))
    rated_stroke_50 = models.PositiveIntegerField(verbose_name=_("Номинальный ход 50"))
    rated_stroke_100 = models.PositiveIntegerField(verbose_name=_("Номинальный ход 100"))
    rated_stroke_200 = models.PositiveIntegerField(verbose_name=_("Номинальный ход 200"))
    load_group_lgv = models.PositiveIntegerField(verbose_name=_("Группа LGV"))
    design_load = models.FloatField(verbose_name=_("Расчетная нагрузка"))

    class Meta:
        verbose_name = _("Нагрузка")
        verbose_name_plural = _("Нагрузки")
        default_permissions = ()
        permissions = (
            ("add_load", _("Может добавлять записи в справочник нагрузок")),
            ("change_load", _("Может изменять записи в справочник нагрузок")),
            ("delete_load", _("Может удалять записи в справочник нагрузок")),
            ("view_load", _("Может просматривать записи в справочник нагрузок")),
        )

    def __str__(self):
        return f"{self.series_name} | Size {self.size} | Load={self.design_load}"


class SpringStiffness(CatalogMixin, SoftDeleteModelMixin, models.Model):
    series_name = models.CharField(
        max_length=SeriesNameChoices.get_max_length(), choices=SeriesNameChoices.choices,
        verbose_name=_("Наименование серии"),
    )
    size = models.PositiveIntegerField(verbose_name=_("Размер"))
    rated_stroke = models.PositiveIntegerField(verbose_name=_("Номинальный ход"))
    value = models.FloatField(null=True, blank=True, verbose_name=_("Жесткость"))

    class Meta:
        verbose_name = _("Пружинная жесткость")
        verbose_name_plural = _("Пружинные жесткости")
        default_permissions = ()
        permissions = (
            ("add_springstiffness", _("Может добавлять записи в справочник пружинных жесткостей")),
            ("change_springstiffness", _("Может изменять записи в справочник пружинных жесткостей")),
            ("delete_springstiffness", _("Может удалять записи в справочник пружинных жесткостей")),
            ("view_springstiffness", _("Может просматривать записи в справочник пружинных жесткостей")),
        )

    def __str__(self):
        return f"{self.series_name} | Size {self.size} | Stroke={self.rated_stroke} | R{self.value}"


class PipeMountingGroup(CatalogMixin, SoftDeleteModelMixin, models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Наименование"))
    variants = models.ManyToManyField("ops.Variant", blank=True, related_name="+", verbose_name=_("Типы креплений"))
    show_variants = models.BooleanField(default=False, verbose_name=_("Показывать исполнения вместо деталей"))

    class Meta:
        verbose_name = _("Группа креплений к трубе")
        verbose_name_plural = _("Группы креплений к трубе")
        default_permissions = ()
        permissions = (
            ("add_pipemountinggroup", _("Может добавлять записи в справочник групп креплений к трубе")),
            ("change_pipemountinggroup", _("Может изменять записи в справочник групп креплений к трубе")),
            ("delete_pipemountinggroup", _("Может удалять записи в справочник групп креплений к трубе")),
            ("view_pipemountinggroup", _("Может просматривать записи в справочник групп креплений к трубе")),
        )

    def __str__(self):
        return self.name


class PipeMountingRule(CatalogMixin, SoftDeleteModelMixin, models.Model):
    family = models.ForeignKey(
        ProductFamily, on_delete=models.PROTECT, related_name="+", verbose_name=_("Семейство изделия"),
    )
    num_spring_blocks = models.PositiveSmallIntegerField(verbose_name=_("Количество пружинных блоков"))
    pipe_direction = models.CharField(
        max_length=PipeDirectionChoices.get_max_length(), choices=PipeDirectionChoices.choices,
        verbose_name=_("Направление трубы"),
    )
    pipe_mounting_groups_bottom = models.ManyToManyField(
        PipeMountingGroup, blank=True, related_name="+", verbose_name=_("Крепление к трубе (нижнее)"),
    )
    pipe_mounting_groups_top = models.ManyToManyField(
        PipeMountingGroup, blank=True, related_name="+", verbose_name=_("Крепление к металлоконструкции (верхнее)"),
    )

    class Meta:
        verbose_name = _("Правило выбора крепления")
        verbose_name_plural = _("Правила выбора креплений")
        default_permissions = ()
        permissions = (
            ("add_pipemountingrule", _("Может добавлять записи в справочник правил выбора креплений")),
            ("change_pipemountingrule", _("Может изменять записи в справочник правил выбора креплений")),
            ("delete_pipemountingrule", _("Может удалять записи в справочник правил выбора креплений")),
            ("view_pipemountingrule", _("Может просматривать записи в справочник правил выбора креплений")),
        )

    def __str__(self):
        return f"{self.family} | {self.num_spring_blocks} ПБ | Труба {self.pipe_direction}"


class ComponentGroup(CatalogMixin, SoftDeleteModelMixin, models.Model):
    group_type = models.CharField(
        max_length=ComponentGroupType.get_max_length(), choices=ComponentGroupType.choices,
        verbose_name=_('Тип группы'),
    )
    detail_types = models.ManyToManyField(
        'ops.DetailType', blank=True, related_name='+', verbose_name=_('Типы детали/изделии'),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['group_type'], condition=models.Q(deleted_at__isnull=True),
                name='unique_group_type_if_not_deleted'
            )
        ]
        verbose_name = _('Группа компонентов')
        verbose_name_plural = _('Группы компонентов')
        default_permissions = ()
        permissions = (
            ("add_componentgroup", _("Может добавлять записи в справочник групп компонентов")),
            ("change_componentgroup", _("Может изменять записи в справочник групп компонентов")),
            ("delete_componentgroup", _("Может удалять записи в справочник групп компонентов")),
            ("view_componentgroup", _("Может просматривать записи в справочник групп компонентов")),
        )

    def __str__(self):
        return f'{self.get_group_type_display()}'


class SpringBlockFamilyBinding(CatalogMixin, models.Model):
    family = models.OneToOneField(
        ProductFamily, on_delete=models.CASCADE, related_name="+", verbose_name=_("Семейство изделия"),
    )
    spring_block_types = models.ManyToManyField(
        "ops.DetailType", related_name="+", verbose_name=_("Допустимые типы пружинных блоков"),
    )

    class Meta:
        verbose_name = _("Связь семейства с типами пружинных блоков")
        verbose_name_plural = _("Связи семейств с типами пружинных блоков")
        default_permissions = ()
        permissions = (
            ("add_springblockfamilybinding", _("Может добавлять запись в справочник связей семейств с типами пружинных блоков")),
            ("change_springblockfamilybinding", _("Может изменять запись в справочник связей семейств с типами пружинных блоков")),
            ("delete_springblockfamilybinding", _("Может удалять запись в справочник связей семейств с типами пружинных блоков")),
            ("view_springblockfamilybinding", _("Может просматривать записи в справочник связей семейств с типами пружинных блоков")),
        )

    def __str__(self):
        return f"{self.family.name}"


class SSBCatalog(CatalogMixin, models.Model):
    fn = models.PositiveIntegerField(verbose_name=_("Номинальная нагрузка, kH"))
    stroke = models.PositiveIntegerField(verbose_name=_("Ход, мм"))
    f = models.PositiveIntegerField(verbose_name=_("F, мм"))
    l = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("L, мм"))
    l1 = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("L1, мм"))
    l2_min = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("L2 мин., мм"))
    l2_max = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("L2 макс., мм"))
    l3_min = models.PositiveIntegerField(verbose_name=_("L3 мин., мм"))
    l3_max = models.PositiveIntegerField(verbose_name=_("L3 макс., мм"))
    l4 = models.PositiveIntegerField(verbose_name=_("L4, мм"))
    a = models.PositiveIntegerField(verbose_name="A")
    b = models.PositiveIntegerField(verbose_name="B")
    h = models.PositiveIntegerField(verbose_name="H")
    diameter_j = models.PositiveIntegerField(verbose_name="ØJ")

    class Meta:
        verbose_name = _("Гидроамортизатор SSB")
        verbose_name_plural = _("Гидроамортизаторы SSB")
        ordering = ["fn", "stroke", "l"]
        default_permissions = ()
        permissions = (
            ("add_ssbcatalog", _("Может добавлять записи в каталог гидроамортизаторов SSB")),
            ("change_ssbcatalog", _("Может изменять записи в каталог гидроамортизаторов SSB")),
            ("delete_ssbcatalog", _("Может удалять записи в каталог гидроамортизаторов SSB")),
            ("view_ssbcatalog", _("Может просматривать записи в каталог гидроамортизаторов SSB")),
        )

    def __str__(self):
        return f"SSB {self.fn:04d}.?.?"

class SSGCatalog(models.Model):
    """Каталог распорок SSG (номинальная нагрузка, диапазоны длины, тип конструкции и пр.)"""

    fn = models.PositiveIntegerField(verbose_name=_("Номинальная нагрузка, кН"), blank=True, null=True)

    # Диапазон длины
    l_min = models.PositiveIntegerField(verbose_name=_("Мин. длина L, мм"), blank=True, null=True)
    l_max = models.PositiveIntegerField(verbose_name=_("Макс. длина L, мм"), blank=True, null=True)

    # Габариты
    l1 = models.FloatField(verbose_name=_("Размер L1, мм"), blank=True, null=True)
    l2 = models.FloatField(verbose_name=_("Размер L2, мм"), blank=True, null=True)
    d = models.FloatField(verbose_name=_("Диаметр D, мм"), blank=True, null=True)
    d1 = models.FloatField(verbose_name=_("Диаметр D1, мм"), blank=True, null=True)
    r = models.FloatField(verbose_name=_("R (радиус/гиб), мм"), blank=True, null=True)
    s = models.FloatField(verbose_name=_("Толщина S, мм"), blank=True, null=True)
    sw = models.FloatField(verbose_name=_("Размер SW (под ключ), мм"), blank=True, null=True)

    # Поля, встречающиеся только у типа 2
    h = models.FloatField(verbose_name=_("Толщина H, мм"), null=True, blank=True)
    sw1 = models.FloatField(verbose_name=_("Размер SW1 (под ключ), мм"), null=True, blank=True)
    sw2 = models.FloatField(verbose_name=_("Размер SW2 (под ключ), мм"), null=True, blank=True)

    # Дополнительно
    regulation = models.FloatField(verbose_name=_("Регулировка длины, мм"), blank=True, null=True)
    fixed_part = models.FloatField(verbose_name=_("Фиксированная часть, кг"), null=True, blank=True)
    delta_l = models.FloatField(verbose_name=_("ΔL, кг/м"), null=True, blank=True)

    # Тип распорки
    type = models.PositiveSmallIntegerField(
        choices=((1, _("Тип 1")), (2, _("Тип 2"))),
        verbose_name=_("Тип распорки"), blank=True, null=True
    )

    class Meta:
        verbose_name = _("Распорка SSG (каталог)")
        verbose_name_plural = _("Распорки SSG (каталог)")
        ordering = ["type", "fn"]
        constraints = [
            models.UniqueConstraint(fields=["fn", "type", "l_min", "l_max"], name="unique_ssg_variant")
        ]
        default_permissions = ()
        permissions = (
            ("add_ssgcatalog", _("Может добавлять записи в каталог распорок SSG")),
            ("change_ssgcatalog", _("Может изменять записи в каталог распорок SSG")),
            ("delete_ssgcatalog", _("Может удалять записи в каталог распорок SSG")),
            ("view_ssgcatalog", _("Может просматривать записи в каталог распорок SSG")),
        )

    def __str__(self):
        return f"SSG {self.fn} кН (Тип {self.type}, L: {self.l_min}-{self.l_max} мм)"


class ClampMaterialCoefficient(CatalogMixin, models.Model):
    material_group = models.CharField(max_length=32, verbose_name=_("Группа материала"))
    temperature_from = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("Температура от, °C"))
    temperature_to = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("Температура до, °C"))
    coefficient = models.FloatField(verbose_name=_("Коэффициент материала"))

    objects = ClampMaterialCoefficientManager()

    class Meta:
        verbose_name = _("Коэффициент материала для хомута")
        verbose_name_plural = _("Коэффициенты материалов для хомутов")
        ordering = [
            "material_group",
            models.F("temperature_from").asc(nulls_first=True),
            "temperature_to"
        ]
        default_permissions = ()
        permissions = (
            ("add_clampmaterialcoefficient", _("Может добавлять записи в справочник коэффициентов материалов для хомутов")),
            ("change_clampmaterialcoefficient", _("Может изменять записи в справочник коэффициентов материалов для хомутов")),
            ("delete_clampmaterialcoefficient", _("Может удалять записи в справочник коэффициентов материалов для хомутов")),
            ("view_clampmaterialcoefficient", _("Может просматривать записи в справочник коэффициентов материалов для хомутов")),
        )

    def clean(self):
        super().clean()

        # Проверяем, что хотя бы одна температура указана
        if self.temperature_from is None and self.temperature_to is None:
            raise ValidationError({
                "temperature_from": _("Необходимо указать хотя бы одну температуру."),
                "temperature_to": _("Необходимо указать хотя бы одну температуру."),
            })

        # Проверяем, что если указаны обе температуры, то максимальная не меньше минимальной
        if self.temperature_from is not None and self.temperature_to is not None:
            if self.temperature_to < self.temperature_from:
                raise ValidationError({
                    "temperature_to": _("Максимальная температура не может быть меньше минимальной температуры."),
                })

    def __str__(self):
        return f"{self.material_group} ({self.temperature_from}°C - {self.temperature_to}°C): {self.coefficient}"


class ClampSelectionMatrix(models.Model):
    product_families = models.ManyToManyField(
        ProductFamily, related_name="+", verbose_name=_("Семейства изделий"),
    )
    clamp_detail_types = models.ManyToManyField(
        "ops.DetailType", related_name="+", verbose_name=_("Тип деталей/изделий хомутов"),
    )
    fastener_detail_types = models.ManyToManyField(
        "ops.DetailType", related_name="+", verbose_name=_("Типы деталей/изделий крепежа"),
    )

    class Meta:
        verbose_name = _("Таблица собираемости для хомутов")
        verbose_name_plural = _("Таблицы собираемости для хомутов")

    def __str__(self):
        return f"Таблица собираемости для {', '.join(str(family) for family in self.product_families.all())}"


class ClampSelectionEntry(models.Model):
    matrix = models.ForeignKey(
        ClampSelectionMatrix, on_delete=models.CASCADE, related_name="entries", verbose_name=_("Таблица собираемости"),
    )
    hanger_load_group = models.PositiveIntegerField(verbose_name=_("Нагрузочная группа подвеса"))
    clamp_load_group = models.PositiveIntegerField(verbose_name=_("Нагрузочная группа хомута"))
    result = models.CharField(
        max_length=ClampSelectionEntryResult.get_max_length(), choices=ClampSelectionEntryResult.choices,
        verbose_name=_("Результат подбора"),
    )

    class Meta:
        unique_together = ["matrix", "hanger_load_group", "clamp_load_group"]
        verbose_name = _("Запись таблицы собираемости")
        verbose_name_plural = _("Записи таблицы собираемости")
        ordering = ["matrix", "hanger_load_group", "clamp_load_group"]
        default_permissions = ()
        permissions = (
            ("add_clampselectionentry", _("Может добавлять записи в справочник таблицы собираемости")),
            ("change_clampselectionentry", _("Может изменять записи в справочник таблицы собираемости")),
            ("delete_clampselectionentry", _("Может удалять записи в справочник таблицы собираемости")),
            ("view_clampselectionentry", _("Может просматривать записи в справочник таблицы собираемости")),
        )

    def __str__(self):
        return f"{self.hanger_load_group} ({self.clamp_load_group}) - {self.get_result_display()}"


# TODO
'''
class WVDCatalog(CatalogMixin, models.Model):
    """Каталог демпферов для хранения параметров расчета в проекте."""
    Sh = models.PositiveIntegerField(verbose_name=_("Номинальный горизонтальный ход, мм"), blank=True, null=True)
    Sv = models.PositiveIntegerField(verbose_name=_("Номинальный вертикальный ход, мм"), blank=True, null=True)
    Sa = models.PositiveIntegerField(verbose_name=_("Номинальный угловой ход, град"), blank=True, null=True)
    Fh = models.FloatField(verbose_name=_("Номинальная горизонтальная нагрузка, кН"), blank=True, null=True)
    Fv = models.FloatField(verbose_name=_("Номинальная вертикальная нагрузка, кН"), blank=True, null=True)

    # TODO
    # m = models.FloatField(verbose_name=_("Вес, кг"), blank=True, null=True)

    # Монтажная высота E
    # Допуск монтажная высота E1
    # Габарит основания A1
    # Допуск габарит основания A1
    # Присоединительный размер B
    # Допуск присоединительный размер B1
    # Диаметр отверстия d
    # Допуск диаметр отверстия d1
    # Толщина основания s
    # Допуск толщина основания s1

    class Meta:
        verbose_name = _("Демпфер WVD")
        verbose_name_plural = _("Демпферы WVD")
        # ordering = ['fn', 'stroke', 'l']

    def __str__(self):
        return f"WVD {self.pk}"
        # return f"SSG {self.fn} кН (Тип {self.type}, L: {self.l_min}-{self.l_max} мм)"
'''
