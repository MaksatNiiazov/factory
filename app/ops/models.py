import logging
import os
import re
import traceback

from collections import OrderedDict
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from typing import Optional, Tuple, Type

import jinja2.exceptions

from PIL import Image, ImageDraw, ImageFont

from constance import config

from django.contrib.auth import get_user_model

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator

from django.db import models, transaction
from django.db.models import QuerySet, Q

from django.utils.module_loading import import_string
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from django_extensions.db.models import TimeStampedModel
from pybarker.contrib.modelshistory.models import HistoryModelTracker
from pybarker.django.db.models import ReadableJSONField

from ops.cache import get_cached_attributes, get_cached_attributes_with_topological_sort, get_cached_item_children
from ops.exceptions import TopologicalSortException

from catalog.choices import Standard, SeriesNameChoices, ComponentGroupType
from catalog.models import PipeDiameter, Material, Directory, DirectoryEntry, ProductFamily, ComponentGroup

from kernel.fields import AttributeChoiceField
from kernel.mixins import SoftDeleteModelMixin
from kernel.models import Organization

from ops.choices import (
    ERPSyncStatus, ERPSyncLogType, ERPSyncType, EstimatedState, AttributeUsageChoices, AttributeType, AttributeCatalog,
    ProjectStatus, LoadUnit, MoveUnit, TemperatureUnit,
)
from ops.managers import (
    BaseCompositionSoftDeleteManager, BaseCompositionAllObjectsManager, AttributeSoftDeleteManager,
    AttributeAllObjectsManager, ItemManager,
)
from ops.marking_compiler import MarkingCompiler

logger = logging.getLogger(__name__)

User = get_user_model()


class Project(SoftDeleteModelMixin, TimeStampedModel, models.Model):
    number = models.CharField(max_length=255, verbose_name=_('Проект CRM'), unique=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name='projects', null=True, blank=True,
        verbose_name=_('Организация'),
    )
    owner = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='projects', verbose_name=_('Владелец'),
    )
    status = models.CharField(
        max_length=ProjectStatus.get_max_length(), choices=ProjectStatus.choices, default=ProjectStatus.DRAFT,
        verbose_name=_('Статус'),
    )

    # Единицы измерения проекта
    load_unit = models.CharField(
        max_length=LoadUnit.get_max_length(), choices=LoadUnit.choices, verbose_name=_('Единица измерения: Нагрузка'),
    )
    move_unit = models.CharField(
        max_length=MoveUnit.get_max_length(), choices=MoveUnit.choices,
        verbose_name=_('Единица измерения: Перемещение'),
    )
    temperature_unit = models.CharField(
        max_length=TemperatureUnit.get_max_length(), choices=TemperatureUnit.choices,
        verbose_name=_('Единица измерения: Температура'),
    )

    standard = models.PositiveSmallIntegerField(
        choices=Standard.choices, default=Standard.RF, verbose_name=_('Стандарт'),
    )

    # TODO: Подумать что-то на замену.
    historylog = HistoryModelTracker(excluded_fields=('id',), root_model='self', root_id=lambda ins: ins.id)

    class Meta:
        verbose_name = _('Проект')
        verbose_name_plural = _('Проекты')
        permissions = (
            ('add_own_project', _('Может создавать свои проекты')),
            ('change_own_project', _('Может изменить свои проекты')),
            ('delete_own_project', _('Может удалить свои проекты')),
            ('view_own_project', _('Может видеть свои проекты')),
            ('import_project_crm', _('Может импортировать проект с CRM')),
            ('sync_project_erp', _('Может синхронизировать проект в ERP')),
        )

    def __str__(self):
        return str(_(f'Проект #{self.number} пользователя {self.owner}'))


class ProjectItem(SoftDeleteModelMixin, models.Model):
    """
    Табличная часть проекта.
    В проект можно добавить как готовое изделие, так и произвольную деталь, например, один хомут.
    """
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='items', verbose_name=_('Проект CRM'))
    position_number = models.PositiveSmallIntegerField(verbose_name=_('Номер позиции'), null=True, blank=True)
    original_item = models.ForeignKey(
        'Item', on_delete=models.PROTECT, related_name='+', verbose_name=_('Оригинальное изделие/деталь'),
        null=True, blank=True,
    )

    selection_params = models.JSONField(null=True, blank=True, verbose_name=_('Параметры подбора'))

    # TODO временно сохраним выбранный вариант пружины, так как нет информации по пружинным блокам
    tmp_spring = models.JSONField(verbose_name=_('Выбранная пружина'), blank=True, null=True)

    customer_marking = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Маркировка заказчика'))
    question_list = models.CharField(verbose_name=_('ОЛ заказчика'), max_length=255, null=True, blank=True)
    tag_id = models.CharField(verbose_name=_('Тег номер'), max_length=255, null=True, blank=True)

    count = models.PositiveIntegerField(null=True, blank=True, verbose_name=_('Количество'))

    crm_id = models.IntegerField(null=True, blank=True, unique=True, verbose_name=_('Идентификатор из CRM'))
    crm_mark_cont = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Описание из CRM'))

    MANUFACTURING = 'manufacturing'
    REFINEMENT = 'refinement'
    RESELLING = 'reselling'

    WORK_TYPES = (
        (MANUFACTURING, _('Производство')),
        (REFINEMENT, _('Доработка')),
        (RESELLING, _('Перепродажа')),
    )

    work_type = models.CharField(max_length=13, choices=WORK_TYPES, null=True, blank=True, verbose_name=_('Тип работ'))

    HORIZONTAL = 'horizontal'
    VERTICAL = 'vertical'

    PIPE_LOCATIONS = (
        (HORIZONTAL, _('Горизонтальное')),
        (VERTICAL, _('Вертикальное')),
    )

    X = 'x'
    Y = 'y'
    Z = 'z'
    AT_ANGLE = 'at_angle'

    PIPE_DIRECTIONS = (
        (X, 'X'),
        (Y, 'Y'),
        (Z, 'Z'),
        (AT_ANGLE, _('Под углом')),
    )

    # Нагрузка и перемещения
    load_plus_x = models.FloatField(verbose_name=_('Нагрузка +X'), null=True, blank=True)
    load_plus_y = models.FloatField(verbose_name=_('Нагрузка +Y'), null=True, blank=True)
    load_plus_z = models.FloatField(verbose_name=_('Нагрузка +Z'), null=True, blank=True)

    load_minus_x = models.FloatField(verbose_name=_('Нагрузка -X'), null=True, blank=True)
    load_minus_y = models.FloatField(verbose_name=_('Нагрузка -Y'), null=True, blank=True)
    load_minus_z = models.FloatField(verbose_name=_('Нагрузка -Z'), null=True, blank=True)

    additional_load_x = models.FloatField(
        verbose_name=_('Дополнительная нагрузка (расчетная) X'), null=True, blank=True
    )
    additional_load_y = models.FloatField(
        verbose_name=_('Дополнительная нагрузка (расчетная) Y'), null=True, blank=True
    )
    additional_load_z = models.FloatField(
        verbose_name=_('Дополнительная нагрузка (расчетная) Z'), null=True, blank=True
    )

    test_load_x = models.FloatField(verbose_name=_('Испытательная нагрузка X'), null=True, blank=True)
    test_load_y = models.FloatField(verbose_name=_('Испытательная нагрузка Y'), null=True, blank=True)
    test_load_z = models.FloatField(verbose_name=_('Испытательная нагрузка Z'), null=True, blank=True)

    move_plus_x = models.FloatField(verbose_name=_('Перемещение +X'), null=True, blank=True)
    move_plus_y = models.FloatField(verbose_name=_('Перемещение +Y'), null=True, blank=True)
    move_plus_z = models.FloatField(verbose_name=_('Перемещение +Z'), null=True, blank=True)

    move_minus_x = models.FloatField(verbose_name=_('Перемещение -X'), null=True, blank=True)
    move_minus_y = models.FloatField(verbose_name=_('Перемещение -Y'), null=True, blank=True)
    move_minus_z = models.FloatField(verbose_name=_('Перемещение -Z'), null=True, blank=True)

    estimated_state = models.CharField(
        max_length=EstimatedState.get_max_length(), choices=EstimatedState.choices, default=EstimatedState.COLD_LOAD,
        verbose_name=_('Расчетное состояние'),
    )

    span = models.PositiveSmallIntegerField(verbose_name=_('Расстояние между опорами'), null=True, blank=True)
    chain_height = models.PositiveSmallIntegerField(verbose_name=_('Высота цепи'), null=True, blank=True)

    # Входные параметры пружины
    minimum_spring_travel = models.FloatField(verbose_name=_('Минимальный запас хода пружины'), default=5.0)

    # Данные трубы
    pipe_location = models.CharField(max_length=10, null=True, blank=True, choices=PIPE_LOCATIONS,
                                     verbose_name=_('Расположение трубы'))
    pipe_direction = models.CharField(max_length=8, null=True, blank=True, choices=PIPE_DIRECTIONS,
                                      verbose_name=_('Направление трубы'))
    ambient_temperature = models.IntegerField(null=True, blank=True, verbose_name=_('Температура среды'))

    nominal_diameter = models.ForeignKey(
        PipeDiameter, on_delete=models.PROTECT, null=True, blank=True, related_name='+', verbose_name=_('DN'),
    )
    outer_diameter_special = models.FloatField(null=True, blank=True, verbose_name=_('Нестандартный диаметр'))
    insulation_thickness = models.FloatField(verbose_name=_('Толщина изоляции'), null=True, blank=True)
    clamp_material = models.ForeignKey(
        Material, on_delete=models.PROTECT, null=True, blank=True, related_name='+', verbose_name=_('Материал хомута')
    )
    insert = models.FloatField(verbose_name=_('Вкладыш'), null=True, blank=True)
    pipe_mount = models.ForeignKey(
        'DetailType', on_delete=models.PROTECT, null=True, blank=True,
        related_name='+', verbose_name=_('Крепление к трубе'),
    )
    top_mount = models.ForeignKey(
        'DetailType', on_delete=models.PROTECT, null=True, blank=True,
        related_name='+', verbose_name=_('Верхнee крепление'),
    )
    system_height = models.FloatField(verbose_name=_('Высота системы'), null=True, blank=True)
    comment = models.TextField(null=True, blank=True, verbose_name=_('Комментарий'))

    # Временные поля
    max_temperature = models.IntegerField(null=True, blank=True, verbose_name=_('Макс. температура'))
    min_temperature = models.IntegerField(null=True, blank=True, verbose_name=_('Мин. температура'))
    max_move_z = models.FloatField(null=True, blank=True, verbose_name=_('Макс. перемещение по Z'))
    hot_load = models.FloatField(null=True, blank=True, verbose_name=_('Горячая нагрузка'))
    cold_load = models.FloatField(null=True, blank=True, verbose_name=_('Холодная нагрузка'))
    load_change = models.FloatField(null=True, blank=True, verbose_name=_('Изменение нагрузки'))
    load_adjustment = models.FloatField(null=True, blank=True, verbose_name=_('Регулировка нагрузки'))
    spring_travel_up = models.IntegerField(null=True, blank=True, verbose_name=_('Запас хода пружины вверх'))
    spring_travel_down = models.IntegerField(null=True, blank=True, verbose_name=_('Запас хода пружины вниз'))
    regulation_range_plus = models.IntegerField(null=True, blank=True, verbose_name=_('Диапазон регулировки "+"'))
    regulation_range_minus = models.IntegerField(null=True, blank=True, verbose_name=_('Диапазон регулировки "-"'))
    chain_weight = models.FloatField(null=True, blank=True, verbose_name=_('Вес грузовой цепи'))
    spring_stiffness = models.IntegerField(null=True, blank=True, verbose_name=_('Жесткость пружины'))
    technical_requirements = models.TextField(blank=True, null=True, verbose_name=_('Технические требования'))
    full_technical_requirements = models.TextField(blank=True, null=True, verbose_name=_('Полные технические требования'))


    historylog = HistoryModelTracker(excluded_fields=('id',), root_model='self', root_id=lambda ins: ins.id)

    class Meta:
        verbose_name = _('табличная часть проекта')
        verbose_name_plural = _('табличная часть проекта')

    @property
    def inner_marking(self):
        """
        Маркировка внутренняя
        """
        if self.original_item:
            return self.original_item.marking

        return None

    def display_marking(self):
        """
        Показать маркировку. Если пользователь указал свою (Поле customer_marking), покажем его. Иначе, внутреннюю.
        """
        return self.customer_marking or self.inner_marking

    def __str__(self):
        return f'{self.project}: {self.display_marking()}'

    def generate_technical_requirements(self):
        """
        Формирует технические требования, объединяя общие требования, требования детали и пользовательские
        """
        requirements_list = [config.TECHNICAL_REQUIREMENTS]
        if self.original_item and self.original_item.type.technical_requirements:
            requirements_list.append(self.original_item.type.technical_requirements)
        if self.technical_requirements:
            requirements_list.append(self.technical_requirements)

        combined_text = "\n".join(filter(None, requirements_list))
        self.full_technical_requirements = self._add_numbering_to_requirements(combined_text)
        return combined_text

    def _add_numbering_to_requirements(self, text):
        """
        Добавляет нумерацию к строкам технических требований.
        """
        lines = text.split("\n")
        numbered_lines = []
        counter = 1

        for line in lines:
            stripped_line = line.strip()
            numbered_lines.append(f"{counter}. {stripped_line}")
            counter += 1

        return "\n".join(numbered_lines)

    def save(self, *args, **kwargs):
        """
        Переопределенный метод save для автоматической генерации позиции и сдвига позиций при необходимости.
        """
        from ops.models import ProjectItem

        is_new = self.pk is None
        prev_position = None

        if not is_new:
            prev = ProjectItem.objects.filter(pk=self.pk).first()
            if prev:
                prev_position = prev.position_number

        # Автогенерация позиции
        if self.position_number is None:
            max_pos = (
                ProjectItem.objects.filter(
                    project=self.project
                ).aggregate(models.Max('position_number'))['position_number__max'] or 0
            )
            self.position_number = max_pos + 1

        elif is_new or self.position_number != prev_position:
            # Сдвигаем всё вниз, начиная с позиции, если она уже занята
            with transaction.atomic():
                ProjectItem.objects.filter(
                    project=self.project,
                    position_number__gte=self.position_number,
                ).exclude(pk=self.pk).order_by('-position_number').update(
                    position_number=models.F('position_number') + 1
                )

        self.generate_technical_requirements()
        super().save(*args, **kwargs)


class ProjectItemRevision(SoftDeleteModelMixin, models.Model):
    """
    Ревизия объекта.
    Это версия изделия, одно и то же изделие может быть сохранено с разными параметрами например трубы.
    """
    project_item = models.ForeignKey(
        ProjectItem, on_delete=models.CASCADE, related_name='revisions', verbose_name=_('Элемент табличной части')
    )
    revision_item = models.ForeignKey(
        'Item', on_delete=models.PROTECT, related_name='+', verbose_name=_('Ревизионный объект')
    )

    # TODO: Сортировка по-умолчанию, по очереди добавления. Может другую сортировку сделать?

    historylog = HistoryModelTracker(excluded_fields=('id',), root_model='self', root_id=lambda ins: ins.id)

    class Meta:
        verbose_name = _('ревизия объекта')
        verbose_name_plural = _('ревизии объектов')

    def __str__(self):
        return f'{self.project_item} (#{self.id})'


class DetailType(SoftDeleteModelMixin, models.Model):
    """
    Тип детали/изделия
    """
    DETAIL = 'detail'
    ASSEMBLY_UNIT = 'assembly_unit'
    PRODUCT = 'product'
    BILLET = 'billet'

    CATEGORIES = (
        (DETAIL, _('Деталь')),
        (ASSEMBLY_UNIT, _('Сборочная единица')),
        (PRODUCT, _('Изделие')),
        (BILLET, _('Заготовка')),
    )

    class BranchQty(models.IntegerChoices):
        ONE = 1, _("Одинарный")
        TWO = 2, _("Двойной")

        __empty__ = _("---------")

    product_family = models.ForeignKey(ProductFamily, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='details', verbose_name=_('Семейство изделий'))
    name = models.CharField(max_length=255, verbose_name=_('Полное наименование'))
    designation = models.CharField(max_length=32, verbose_name=_('Обозначение'))
    category = models.CharField(max_length=255, choices=CATEGORIES, verbose_name=_('Категория'))

    short_name_to_erp = models.BooleanField(default=False, blank=True, verbose_name=_('Отправить "Наименование" в ERP'))

    # Нам нужны и True/False/Null, использую Enum, чтобы потом не лепить NullBooleanField в админку
    branch_qty = models.PositiveSmallIntegerField(
        verbose_name=_('Вид'), null=True, blank=True, choices=BranchQty.choices,
    )

    historylog = HistoryModelTracker(excluded_fields=('id',), root_model='self', root_id=lambda ins: ins.id)
    default_comment = models.TextField(blank=True, null=True, verbose_name=_('Комментарий по умолчанию'))
    technical_requirements = models.TextField(blank=True, null=True, verbose_name=_('Технические требования'))

    class Meta:
        verbose_name = _('тип детали/изделия')
        verbose_name_plural = _('типы деталей/изделии')
        constraints = [models.UniqueConstraint(
            fields=['designation', 'category', 'branch_qty', 'deleted_at'], name='unique_detailtype'
        )]

    def __str__(self):
        return f'{self.designation} - {self.name}'

    def get_attributes(self) -> QuerySet:
        """
        Возвращает базовые атрибуты этого типа детали/изделии.

        Атрибуты отбираются по текущему DetailType.
        Это атрибуты, которые заданы на уровне типа детали
        и применяются ко всем исполнениям этого типа.
        """
        return Attribute.objects.for_detail_type(self)

    def get_attributes_dict(self) -> dict[str, 'Attribute']:
        """
        Возвращает словарь атрибутов, где ключом является имя атрибута, а значением - объект Attribute.
        """
        return {attr.name: attr for attr in self.get_attributes()}

    @property
    def erp_modelslug(self) -> str:
        """
        Данные, которые нужно отправить как "modelslug" в ERP.
        Возвращает строковое значение поля name.
        """
        return self.name

    def clean(self):
        if self.category == DetailType.PRODUCT and self.branch_qty is None:
            raise ValidationError(_('Для изделия выберите из (одинарный/двойной) для поля "Вид?"'))

    def get_available_attributes(self, variant=None):
        """
        Возвращает список всех доступных атрибутов для указанного варианта (Variant).
        Данные включают ID, название, тип, категорию, designation и другие поля.
        """
        attributes = []

        lang = get_language()
        attribute_map = OrderedDict()

        for attr in Attribute.objects.filter(detail_type=self, variant__isnull=True):
            attribute_map[attr.name] = attr

        if variant:
            for attr in Attribute.objects.filter(variant=variant):
                attribute_map[attr.name] = attr

        for attr in attribute_map.values():
            attributes.append({
                "id": attr.id,
                "label": getattr(attr, f"label_{lang}", attr.label),
                "name": attr.name,
                "type": attr.type,
                "category": self.category,
                "designation": self.designation,
                "formatted": f"{self.category}_{self.designation}.{attr.name}"
            })

        if variant:
            base_compositions = BaseComposition.objects.filter(
                Q(base_parent=self, base_parent_variant__isnull=True) |
                Q(base_parent_variant=variant)
            )

            for base in base_compositions:
                attr_map = OrderedDict()

                for attr in Attribute.objects.filter(detail_type=base.base_child, variant__isnull=True):
                    attr_map[attr.name] = attr

                if base.base_child_variant:
                    for attr in Attribute.objects.filter(variant=base.base_child_variant):
                        attr_map[attr.name] = attr

                for attr in attr_map.values():
                    attributes.append({
                        "id": attr.id,
                        "label": getattr(attr, f"label_{lang}", attr.label),
                        "name": attr.name,
                        "type": attr.type,
                        "category": base.base_child.category,
                        "designation": base.base_child.designation,
                        "formatted": f"{base.base_child.category}_{base.base_child.designation}.{attr.name}"
                    })
        else:
            variants = self.variants.all()
            base_sets = []

            for var in variants:
                base_children = set(
                    BaseComposition.objects.filter(base_parent_variant=var)
                    .values_list('base_child_id', flat=True)
                )
                base_sets.append(base_children)

            if base_sets:
                common_base_child_ids = set.intersection(*base_sets)

                for base_child_id in common_base_child_ids:
                    base_child = DetailType.objects.get(id=base_child_id)

                    for attr in Attribute.objects.filter(detail_type=base_child, variant__isnull=True):
                        attributes.append({
                            "id": attr.id,
                            "label": getattr(attr, f"label_{lang}", attr.label),
                            "name": attr.name,
                            "type": attr.type,
                            "category": base_child.category,
                            "designation": base_child.designation,
                            "formatted": f"{base_child.category}_{base_child.designation}.{attr.name}"
                        })

        return attributes

    def get_available_attributes_v2(self, variant=None, exclude_composition=False):
        """
        Возвращает список всех доступных атрибутов для указанного варианта (Variant).
        Если передан exclude_composition=True, исключает атрибуты базового состава.
        """
        attributes = []
        lang = get_language()

        # Атрибуты текущего типа и варианта
        self._add_attributes_from(self, variant, lang, attributes)

        if exclude_composition:
            return attributes

        # Атрибуты из BaseComposition по типу (без variant)
        compositions = BaseComposition.objects.filter(base_parent=self, base_parent_variant__isnull=True)
        for comp in compositions:
            self._add_attributes_from(comp.base_child, comp.base_child_variant, lang, attributes, child_id=comp.id)

        # Атрибуты из BaseComposition по конкретному variant
        if variant:
            for comp in BaseComposition.objects.filter(base_parent_variant=variant):
                self._add_attributes_from(comp.base_child, comp.base_child_variant, lang, attributes, child_id=comp.id)
            return attributes

        # Общее множество base_child у всех вариантов
        variants = self.variants.all()
        base_sets = []
        for var in variants:
            base_children = set(
                BaseComposition.objects.filter(base_parent_variant=var)
                .values_list('base_child_id', flat=True)
            )
            base_sets.append(base_children)

        if base_sets:
            common_base_child_ids = set.intersection(*base_sets)
            for base_child_id in common_base_child_ids:
                base_child = DetailType.objects.get(id=base_child_id)
                self._add_attributes_from(base_child, None, lang, attributes)

        return attributes

    @staticmethod
    def _add_attributes_from(detail_type, variant, lang, attributes_list, child_id=None):
        """
        Добавляет базовые и вариативные атрибуты в переданный список.
        Если передан child_id, добавляет его в словарь как "child_id".
        """
        attr_map = OrderedDict()

        # статичные атрибуты
        for attr in Attribute.objects.filter(detail_type=detail_type, variant__isnull=True):
            attr_map[attr.name] = attr

        # вариативные
        if variant:
            for attr in Attribute.objects.filter(variant=variant):
                attr_map[attr.name] = attr

        for attr in attr_map.values():
            entry = {
                "id": attr.id,
                "label": getattr(attr, f"label_{lang}", attr.label),
                "name": attr.name,
                "type": attr.type,
                "category": detail_type.category,
                "designation": detail_type.designation,
                "formatted": f"{detail_type.category}_{detail_type.designation}.{attr.name}",
            }
            # ─── добавлено минимально ───
            if child_id is not None:
                entry["child_id"] = child_id

            attributes_list.append(entry)


def upload_sketch_to(instance, filename):
    return os.path.join(
        'sketches',
        instance.detail_type.designation,
        filename,
    )


class Variant(SoftDeleteModelMixin, models.Model):
    detail_type = models.ForeignKey(
        DetailType, on_delete=models.CASCADE, related_name='variants', verbose_name=_('Тип детали/изделий')
    )
    name = models.CharField(max_length=255, verbose_name=_('Наименование'))

    marking_template = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Шаблон маркировки'))
    sketch = models.ImageField(upload_to=upload_sketch_to, null=True, blank=True, verbose_name=_('Эскиз'))
    sketch_coords = models.JSONField(null=True, blank=True, verbose_name=_('Координаты эскиза'))

    subsketch = models.ImageField(upload_to=upload_sketch_to, null=True, blank=True,
                                  verbose_name=_('Дополнительный эскиз'))
    subsketch_coords = models.JSONField(null=True, blank=True, verbose_name=_('Координаты дополнительного эскиза'))

    series = models.CharField(
        max_length=SeriesNameChoices.get_max_length(), null=True, blank=True, choices=SeriesNameChoices.choices,
        verbose_name=_('Серия'),
    )

    # Формулы для расчета веса и высоты системы
    formula_weight = models.CharField(max_length=512, null=True, blank=True, verbose_name=_('Формула для расчета веса'))
    formula_height = models.CharField(
        max_length=512, null=True, blank=True, verbose_name=_('Формула для расчета высоты')
    )
    formula_chain_weight = models.CharField(
        max_length=512, null=True, blank=True,
        verbose_name=_('Формула расчёта веса грузовой цепи')
    )
    formula_spring_block = models.CharField(
        max_length=512, null=True, blank=True,
        verbose_name=_('Формула расчёта монтажной длины пружинного блока в холодном состоянии')
    )

    historylog = HistoryModelTracker(excluded_fields=('id',), root_model='self', root_id=lambda ins: ins.id)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['deleted_at', 'name', 'detail_type'], name='unique_variant')
        ]
        verbose_name = _('исполнение')
        verbose_name_plural = _('исполнения')
        ordering = ('detail_type', 'name')

    def get_base_compositions(self) -> QuerySet:
        """
        Возвращает базовый состав исполнения.

        Это объекты BaseComposition, связанные с данным исполнением (Variant).
        """
        return BaseComposition.objects.for_variant(self)

    def get_attributes(self, cached=False) -> QuerySet:
        """
        Возвращает базовые атрибуты и конкретные атрибуты этого исполнения.

        Если у исполнения (Variant) и типа детали (DetailType) есть атрибуты с одинаковыми наименованием,
        возвращается атрибут, связанный с исполнением. Атрибуты типа детали в таком случае исключаются.
        """
        if cached:
            return get_cached_attributes(self)
        else:
            return Attribute.objects.for_variant(self)

    def get_attributes_dict(self, cached=False) -> dict[str, 'Attribute']:
        """
        Возвращает словарь атрибутов, где ключом является имя атрибута, а значением - объект Attribute.
        """
        return {attr.name: attr for attr in self.get_attributes(cached=cached)}

    def has_series(self) -> bool:
        return ComponentGroup.objects.filter(
            group_type=ComponentGroupType.SERIES_SELECTABLE,
            detail_types=self.detail_type,
        ).exists()

    def resize_image(self, image, max_width=520, max_height=680):
        img = Image.open(image)
        width, height = img.size
        ratio = width / height

        if width > height and width > max_width:
            new_height = round(max_width / ratio)
            size = (max_width, new_height)
        elif height > width and height > max_height:
            new_width = round(max_height * ratio)
            size = (new_width, max_height)
        else:
            size = (width, height)

        img = img.resize(size, Image.Resampling.LANCZOS)

        image_io = BytesIO()

        # Устанавливаем формат по умолчанию, если он не определен
        img_format = img.format if img.format else 'JPEG'

        # Проверяем формат, если формат 'JPEG', используем 'RGB' mode
        if img_format == 'JPEG' and img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # Сохраняем изображение
        img.save(image_io, format=img_format)

        new_image = ContentFile(image_io.getvalue(), name=image.name)
        return new_image

    def generate_sketch(self, item, field_name='sketch', coords_field_name='sketch_coords'):
        sketch = getattr(self, field_name)

        if not sketch:
            return None

        sketch_image = Image.open(sketch.path)
        sketch_coords = getattr(self, coords_field_name)

        if not sketch_coords:
            return sketch_image

        draw = ImageDraw.Draw(sketch_image)
        font = ImageFont.load_default()

        for coord in sketch_coords:
            attribute_id = coord.get('id')
            child_id = coord.get('child_id')
            x = coord.get('x')
            y = coord.get('y')
            rotation = coord.get('rotation', 0)

            attribute = self.attributes.filter(id=attribute_id).first()

            if not attribute:
                continue

            if child_id:
                item_child = ItemChild.objects.filter(id=child_id).first()

                if not item_for_search:
                    continue

                item_for_search = item_child.item
            else:
                item_for_search = item

            attribute_value = item_for_search.parameters.get(attribute.name)
            if not attribute_value:
                continue

            text = str(attribute_value)

            bbox = draw.textbbox((0, 0), text, font=font)
            text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

            # Создаем текстовое изображение с прозрачным фоном
            padding = 4
            text_image = Image.new('RGBA', (text_width, text_height + padding), (255, 255, 255, 0))
            text_draw = ImageDraw.Draw(text_image)
            text_draw.text((0, 0), text, font=font, fill="black")

            centered_x = int(x - text_width / 2)
            centered_y = int(y - text_height / 2)

            if rotation:
                rotated_text = text_image.rotate(-rotation, expand=1)
                sketch_image.paste(rotated_text, (centered_x, centered_y), rotated_text)
            else:
                sketch_image.paste(text_image, (centered_x, centered_y), text_image)

        return sketch_image

    def __str__(self):
        return f'{self.detail_type}: {self.name}'


class FieldSet(SoftDeleteModelMixin, models.Model):
    """
    Группирование атрибутов
    """
    icon = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Иконка'))
    name = models.CharField(max_length=255, verbose_name=_('Наименование группы'))
    label = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Заголовок группы'))

    historylog = HistoryModelTracker(excluded_fields=('id',), root_model='self', root_id=lambda ins: ins.id)

    class Meta:
        verbose_name = _('группа атрибутов')
        verbose_name_plural = _('группы атрибутов')

    def __str__(self):
        return str(self.label)


class Attribute(SoftDeleteModelMixin, models.Model):
    """
    Свойство детали/изделии
    """
    TYPE_MAPPER = {
        AttributeType.STRING: str,
        AttributeType.INTEGER: int,
        AttributeType.NUMBER: float,
        AttributeType.BOOLEAN: bool,
        AttributeType.DATETIME: datetime,
        AttributeType.DATE: date,
        AttributeType.CATALOG: int,  # Идентификатор объекта
    }

    CATALOG_APIS = {
        AttributeCatalog.NOMINAL_DIAMETER: '/api/nominal_diameters/',
        AttributeCatalog.PIPE_DIAMETER: '/api/pipe_diameters/',
        AttributeCatalog.LOAD_GROUP: '/api/load_groups/',
        AttributeCatalog.MATERIAL: '/api/materials/',
        AttributeCatalog.COVERING_TYPE: '/api/covering_types/',
        AttributeCatalog.COVERING: '/api/coverings/',
        AttributeCatalog.SUPPORT_DISTANCE: '/api/catalog/support-distances/',
    }

    CATALOG_SERIALIZERS = {
        AttributeCatalog.NOMINAL_DIAMETER: 'catalog.api.serializers.NominalDiameterSerializer',
        AttributeCatalog.PIPE_DIAMETER: 'catalog.api.serializers.PipeDiameterSerializer',
        AttributeCatalog.LOAD_GROUP: 'catalog.api.serializers.LoadGroupSerializer',
        AttributeCatalog.MATERIAL: 'catalog.api.serializers.MaterialSerializer',
        AttributeCatalog.COVERING_TYPE: 'catalog.api.serializers.CoveringTypeSerializer',
        AttributeCatalog.COVERING: 'catalog.api.serializers.CoveringSerializer',
        AttributeCatalog.SUPPORT_DISTANCE: 'catalog.api.serializers.SupportDistanceSerializer',
    }

    detail_type = models.ForeignKey(
        DetailType, on_delete=models.CASCADE, null=True, blank=True, related_name='attributes',
        verbose_name=_('Тип детали'),
    )
    variant = models.ForeignKey(
        Variant, on_delete=models.CASCADE, null=True, blank=True,
        related_name='attributes', verbose_name=_('Исполнение'),
    )

    type = models.CharField(
        max_length=AttributeType.get_max_length(), choices=AttributeType.choices, verbose_name=_('Тип поля'),
    )

    usage = models.CharField(
        max_length=AttributeUsageChoices.get_max_length(),
        choices=AttributeUsageChoices.choices,
        default=AttributeUsageChoices.CUSTOM,
        verbose_name=_('Использование атрибута'),
    )

    catalog = models.CharField(
        max_length=AttributeCatalog.get_max_length(), choices=AttributeCatalog.choices, null=True, blank=True,
        verbose_name=_('Справочник'),
    )

    name = models.CharField(
        max_length=255, verbose_name=_('Наименование поля'),
        validators=[RegexValidator(r'^[A-Za-z0-9_]+$', _('Должен содержать только английские буквы, цифры и _'))],
    )
    erp_name = models.JSONField(null=True, blank=True, verbose_name=_('Маппинг полей в ERP'))

    label = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Заголовок поля'))
    description = models.TextField(null=True, blank=True, verbose_name=_('Описание поля'))
    is_required = models.BooleanField(default=False, blank=True, verbose_name=_('Обязательное поле'))
    default = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Значение по-умолчанию'))

    calculated_value = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_('Вычисляемое значение'),
        help_text=_('Если формула вычисления здесь указан, то поле является вычисляемым, и его нельзя будет '
                    'редактировать вручную'),
    )

    choices = AttributeChoiceField(null=True, blank=True, verbose_name=_('Список'))

    # Настройка fieldsets
    fieldset = models.ForeignKey(FieldSet, on_delete=models.PROTECT, related_name='+', verbose_name=_('Группа'))

    position = models.IntegerField(validators=[MinValueValidator(1)], verbose_name=_('Позиция'))

    historylog = HistoryModelTracker(excluded_fields=('id',), root_model='self', root_id=lambda ins: ins.id)

    @property
    def catalog_api(self):
        api_url = self.CATALOG_APIS.get(self.catalog)

        if not api_url:
            return None

        return api_url

    objects = AttributeSoftDeleteManager()
    all_objects = AttributeAllObjectsManager()

    class Meta:
        ordering = ['variant', 'position']
        verbose_name = _('Атрибут')
        verbose_name_plural = _('Атрибуты')

    def convert(self, value, field_name=None):
        current_type = self.TYPE_MAPPER[self.type]

        field_name = field_name or self.name

        if self.type == 'catalog':
            allowed_builtin_catalogues = [item for item in AttributeCatalog]

            if self.catalog not in allowed_builtin_catalogues:
                try:
                    directory_id = int(self.catalog)

                    if not Directory.objects.filter(pk=directory_id).exists():
                        raise ValidationError({
                            field_name: _('Значение должно быть либо допустимым статическим каталогом, либо '
                                          'существующим идентификатором Directory.')
                        })

                    entry = DirectoryEntry.objects.get(id=value, directory_id=directory_id)
                    return entry.id
                except ValueError:
                    raise ValidationError({
                        field_name: _('Значение должно быть либо допустимым статическим каталогом, либо числовым '
                                      'идентификатором Directory.')
                    })
            else:
                package = f'catalog.models.{self.catalog}'
                catalog_model = import_string(package)

                try:
                    instance = catalog_model.objects.get(pk=value)
                    return int(value)
                except catalog_model.DoesNotExist:
                    raise ValidationError(
                        {field_name: f'Не найден объект {repr(catalog_model)} с идентификатором {value}'}
                    )
        if current_type == int:
            try:
                return int(float(value))
            except Exception as exc:
                raise ValidationError(
                    {field_name: f'Не подходящее значение по-умолчанию для типа Целое число: {exc}'},
                )
        elif current_type == float:
            try:
                val = float(value)

                q = Decimal('1.00')
                val = float(Decimal(str(val)).quantize(q, rounding=ROUND_HALF_UP))

                return val
            except Exception as exc:
                raise ValidationError(
                    {field_name: f'Не подходящее значение по-умолчанию для типа Число: {exc}'},
                )
        elif current_type == bool:
            if value == 'true':
                return True
            elif value == 'false':
                return False
            else:
                raise ValidationError(
                    {
                        field_name: f'Не подходящее значение по-умолчанию для типа Да/Нет. Необходимо указать: '
                                    f'true или false',
                    }
                )
        elif current_type == datetime:
            try:
                return datetime.fromisoformat(value)
            except Exception as exc:
                raise ValidationError(
                    {field_name: f'Не подходящее значение по-умолчанию для типа Дата/Время: {exc}'},
                )
        elif current_type == date:
            try:
                return date.fromisoformat(value)
            except Exception as exc:
                raise ValidationError(
                    {field_name: f'Не подходящее значение по-умолчанию для типа Дата: {exc}'},
                )
        return value

    def clean(self):
        if not self.detail_type and not self.variant:
            raise ValidationError({'detail_type': _('Необходимо указать DetailType или Variant.')})

        if self.detail_type and self.variant:
            raise ValidationError({'detail_type': _('Нельзя указать оба DetailType и Variant.')})

        if self.calculated_value:
            errors = {}
            if self.choices:
                errors["choices"] = _('Запрещено указывать список, если поле является вычисляемым')
            if self.default:
                errors["default"] = _('Запрещено указывать значение по-умолчанию, если поле является вычисляемым')
            if self.is_required:
                errors["is_required"] = _('Запрещено указывать обязательность поля, если поле является вычисляемым')
            if errors:
                raise ValidationError(errors)

        if self.type == AttributeType.CATALOG and not self.catalog:
            raise ValidationError({'catalog': _('Необходимо выбрать каталог, если тип "Каталог"')})

        if self.type != AttributeType.CATALOG:
            self.catalog = None

        if self.catalog:
            allowed_builtin_catalogues = [item for item in AttributeCatalog]

            if self.catalog not in allowed_builtin_catalogues:
                try:
                    directory_id = int(self.catalog)

                    if not Directory.objects.filter(pk=directory_id).exists():
                        raise ValidationError({
                            'catalog': _('Значение должно быть либо допустимым статическим каталогом, либо '
                                         'существующим идентификатором Directory.')
                        })
                except ValueError:
                    raise ValidationError({
                        'catalog': _('Значение должно быть либо допустимым статическим каталогом, либо числовым '
                                     'идентификатором Directory.')
                    })

        if self.default:
            self.convert(self.default, field_name='default')

    @classmethod
    def get_catalog_choices(cls):
        """
        Возвращает список доступных каталогов, включающий как статические, так и динамически добавленные каталоги.
        """
        dynamic_catalogues = [(str(d.id), d.name) for d in Directory.objects.all()]
        return list(AttributeCatalog.choices) + dynamic_catalogues

    @classmethod
    def get_catalog_apis(cls):
        """
        Возвращает список API для каталогов, включающий как статические, так и динамически добавленные API.
        """
        dynamic_apis = [(str(d.id), f'/api/directories/{d.id}/entries/') for d in Directory.objects.all()]
        return [(key, value) for key, value in cls.CATALOG_APIS.items()] + dynamic_apis

    def __str__(self):
        return str(self.label) if self.label else str(self.name)


class Item(SoftDeleteModelMixin, TimeStampedModel, models.Model):
    """
    Изделие/Деталь/Сборочная единица
    """
    type = models.ForeignKey(DetailType, on_delete=models.PROTECT, related_name='+', verbose_name=_('Тип'))
    variant = models.ForeignKey(Variant, on_delete=models.PROTECT, related_name='+', verbose_name=_('Исполнение'))

    inner_id = models.BigIntegerField(
        null=True, blank=True, validators=[MinValueValidator(100000), MaxValueValidator(999999)],
        verbose_name=_('Внутренний идентификатор'),
    )

    name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Наименование'))
    name_manual_changed = models.BooleanField(blank=True, default=False)

    # Маркировка автоматически должен быть сгенерирован на основе шаблона с DetailType
    marking = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Маркировка'))
    marking_errors = ReadableJSONField(null=True, blank=True, verbose_name=_('Ошибки маркировки'))

    comment = models.TextField(null=True, blank=True, verbose_name=_('Комментарий'))

    weight = models.FloatField(null=True, blank=True, verbose_name=_('Вес'))
    weight_errors = ReadableJSONField(null=True, blank=True, verbose_name=_('Ошибки расчета веса'))
    height = models.FloatField(null=True, blank=True, verbose_name=_('Высота'))
    height_errors = ReadableJSONField(null=True, blank=True, verbose_name=_('Ошибки расчета высоты'))

    chain_weight = models.FloatField(null=True, blank=True, verbose_name=_('Вес грузовой цепи'))
    chain_weight_errors = ReadableJSONField(null=True, blank=True, verbose_name=_('Ошибки расчета веса грузовой цепи'))
    spring_block_length = models.FloatField(null=True, blank=True, verbose_name=_('Монтажная длина пружинного блока'))
    spring_block_length_errors = ReadableJSONField(null=True, blank=True,
                                                   verbose_name=_('Ошибки расчета монтажной длины пружинного блока'))

    material = models.ForeignKey(
        Material, on_delete=models.PROTECT, null=True, blank=True, related_name='+', verbose_name=_('Материал')
    )
    parameters = ReadableJSONField(null=True, blank=True, verbose_name=_('Параметры'))
    parameters_errors = ReadableJSONField(null=True, blank=True, verbose_name=_('Ошибки параметров'))
    locked_parameters = ReadableJSONField(null=True, blank=True, verbose_name=_('Заблокированные параметры'))
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name='items', verbose_name=_('Автор'))

    erp_id = models.CharField(null=True, blank=True, verbose_name=_('Идентификатор с ERP'))
    erp_nomspec = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Номер спецификации'))

    historylog = HistoryModelTracker(excluded_fields=('id',), root_model='self', root_id=lambda ins: ins.id)

    objects = ItemManager()

    class Meta:
        verbose_name = _('Изделие/Деталь/Сборочная единица')
        verbose_name_plural = _('Изделия/Детали/Сборочные единицы')
        default_permissions = ('add_item', 'change_item', 'delete_item', 'view_item')
        permissions = (
            ('add_item', 'Может создавать изделия/детали/сборочные единицы всех пользователей'),
            ('change_item', 'Может изменять изделия/детали/сборочные единицы всех пользователей'),
            ('delete_item', 'Может удалять изделия/детали/сборочные единицы всех пользователей'),
            ('view_item', 'Может видеть изделия/детали/сборочные единицы всех пользователей'),
            ('add_own_item', _('Может создавать свои изделия/детали/сборочные единицы')),
            ('change_own_item', _('Может изменить свои изделия/детали/сборочные единицы')),
            ('delete_own_item', _('Может удалить свои изделия/детали/сборочные единицы')),
            ('view_own_item', _('Может видеть свои изделия/детали/сборочные единицы')),
            ('sync_item_erp', _('Может синхронизировать изделия/детали/сборочные единицы в ERP')),
        )
        constraints = [
            models.UniqueConstraint(fields=['inner_id', 'deleted_at'], name='unique_inner_id_not_deleted')
        ]

    def generate_marking(self) -> str:
        """
        Генерирует маркировку для элемента на основе шаблона с использованием класса MarkingCompiler.
        В случае ошибки при компиляции возвращает строку "ERROR".
        """
        compiler = MarkingCompiler(item=self)

        try:
            marking = compiler.compile()
            marking_errors = None
        except Exception as exc:
            marking = "ERROR"
            marking_errors = [str(exc)]

        return marking, marking_errors

    def calculate_weight(self) -> Tuple[Optional[float], Optional[list]]:
        compiler = MarkingCompiler(item=self, marking_template=self.variant.formula_weight, auto_wrap=True)

        try:
            weight = float(compiler.compile())
            weight_errors = None
        except Exception as exc:
            weight = 0
            weight_errors = [str(exc)]

        return weight, weight_errors

    def update_weight(self, commit: bool = True) -> None:
        if not self.variant.formula_weight:
            return

        self.weight, self.weight_errors = self.calculate_weight()

        if commit:
            self.save(update_fields=['weight', 'weight_errors'])

    def calculate_height(self) -> Tuple[Optional[float], Optional[list]]:
        compiler = MarkingCompiler(item=self, marking_template=self.variant.formula_height, auto_wrap=True)

        try:
            height = float(compiler.compile())
            height_errors = None
        except Exception as exc:
            height = 0
            height_errors = [str(exc)]

        return height, height_errors

    def update_height(self, commit: bool = True) -> None:
        if not self.variant.formula_height:
            return

        self.height, self.height_errors = self.calculate_height()

        if commit:
            self.save(update_fields=['height', 'height_errors'])

    def calculate_chain_weight(self) -> Tuple[Optional[float], Optional[list]]:
        """
        Вычисляет вес грузовой цепи по формуле из поля formula_chain_weight (Variant).
        """
        if not self.variant.formula_chain_weight:
            return None, None

        compiler = MarkingCompiler(item=self, marking_template=self.variant.formula_chain_weight, auto_wrap=True)
        try:
            chain_weight = float(compiler.compile())
            errors = None
        except Exception as exc:
            chain_weight = 0
            errors = [str(exc)]
        return chain_weight, errors

    def calculate_spring_block_length(self) -> Tuple[Optional[float], Optional[list]]:
        """
        Вычисляет монтажную длину пружинного блока по формуле из поля formula_spring_block (Variant).
        """
        if not self.variant.formula_spring_block:
            return None, None

        compiler = MarkingCompiler(item=self, marking_template=self.variant.formula_spring_block, auto_wrap=True)
        try:
            spring_block_value = float(compiler.compile())
            errors = None
        except Exception as exc:
            spring_block_value = 0
            errors = [str(exc)]
        return spring_block_value, errors

    def update_chain_weight(self, commit: bool = True) -> None:
        self.chain_weight, self.chain_weight_errors = self.calculate_chain_weight()
        if commit:
            self.save(update_fields=['chain_weight', 'chain_weight_errors'])

    def update_spring_block_length(self, commit: bool = True) -> None:
        self.spring_block_length, self.spring_block_length_errors = self.calculate_spring_block_length()
        if commit:
            self.save(update_fields=['spring_block_length', 'spring_block_length_errors'])

    def generate_name(self) -> str:
        """
        Генерирует наименование элемента на основе сгенерированной маркировки.
        """
        return self.marking

    def get_children(self):
        children = get_cached_item_children(self.id)
        return children

    def calculate_attribute(self, attribute, extra_context=None, children=None):
        errors = {}
        value = None

        our_value = self.parameters.get(attribute.name)
        extra_context = extra_context or {}

        # Если значение атрибута заблокировано, то пропускаем вычисление
        locked = self.locked_parameters
        if locked and attribute.name in locked:
            return our_value, errors

        is_calculable = bool(attribute.calculated_value)

        if is_calculable:
            variables = re.findall(r'\b(Fcold|k)\b', attribute.calculated_value)

            for var in variables:
                if var not in extra_context:
                    errors[attribute.name] = f'Переменная {var} вычисляется во время подбора, пропускаем вычисление.'
                    return None, errors

            compiler = MarkingCompiler(
                item=self, marking_template=attribute.calculated_value, auto_wrap=True, extra_context=extra_context,
                children=children,
            )

            try:
                value = compiler.compile()
            except ObjectDoesNotExist as exc:
                logger.exception('ObjectDoesNotExist occurred while compiling attribute %s in Item.id=%d', attribute.name, self.id)
                errors[attribute.name] = str(exc)
                return None, errors
            except jinja2.exceptions.UndefinedError as exc:
                logger.exception('UndefinedError occurred while compiling attribute %s in Item.id=%d', attribute.name, self.id)
                errors[attribute.name] = str(exc)
                return None, errors
            except Exception as exc:
                logger.exception('Unexpected error occurred while compiling attribute %s in Item.id=%d', attribute.name, self.id)
                errors[attribute.name] = str(exc)
                return None, errors

            try:
                value = attribute.convert(value)
            except ValidationError as exc:
                logger.exception('ValidationError occured while converting attribute %s in Item.id=%d', attribute.name, self.id)
                errors.update({key: str(err) for key, err in exc.error_dict.items()})
                value = None
        else:
            if (isinstance(our_value, str) and not our_value) or our_value is None:
                if attribute.is_required:
                    errors[attribute.name] = str(_(f'Параметр {attribute.name} является обязательным'))
                    value = None
                if attribute.default:
                    try:
                        value = attribute.convert(attribute.default)
                    except ValidationError as exc:
                        logger.exception(
                            'ValidationError occured while converting attribute %s in Item.id=%d',
                            attribute.name, self.id
                        )
                        errors.update({key: str(err) for key, err in exc.error_dict.items()})
                        value = None
                return value, errors

            if attribute.choices:
                choices = [str(item['value']) for item in attribute.choices]

                if str(our_value) not in choices:
                    errors[attribute.name] = str(_(f'Значение {our_value} отсутствует в списке значении'))
                    return None, errors

            try:
                value = attribute.convert(our_value)
            except ValidationError as exc:
                logger.exception(
                    'ValidationError occured while converting attribute %s in Item.id=%d',
                    attribute.name, self.id
                )
                errors.update({key: str(err) for key, err in exc.error_dict.items()})
                value = None

        return value, errors

    def recalculate_parameters(self) -> None:
        """
        Пересчитывает значение атрибутов изделия/детали.
        """
        if not self.variant_id:
            return

        if not self.parameters:
            self.parameters = {}
        if not self.parameters_errors:
            self.parameters_errors = {}

        try:
            attributes = get_cached_attributes_with_topological_sort(self.variant)
        except TopologicalSortException as exc:
            logger.exception("Topological sort failed for attributes in Item.id=%d", self.id)

            for field in exc.fields:
                self.parameters[field] = None
                self.parameters_errors[field] = str(exc)
        else:
            for attribute in attributes:
                value, errors = self.calculate_attribute(attribute)
                self.parameters[attribute.name] = value
                self.parameters_errors.update(**errors)

    def clean(self):
        if self.variant_id and self.type_id != self.variant.detail_type_id:
            raise ValidationError({'variant': _('Исполнение не принадлежит этому типу')})
        
        self.recalculate_parameters()
        self.marking, self.marking_errors = self.generate_marking()

        if not self.name_manual_changed:
            self.name = self.generate_name()

    def _set_default_comment(self):
        self.comment = self.type.default_comment if self.type else ''

    def save(self, *args, **kwargs) -> None:
        """
        Переопределённый метод сохранения объекта.
        Если объект сохраняется впервые (self._state.adding), то генерируется уникальный inner_id.
        Если последний inner_id существует, то новый будет на 1 больше.
        В противном случае устанавливается начальное значение 100000.

        После сохранения объекта маркировка обновляется с помощью метода generate_marking.

        Если наименование не было изменено вручную (name_manual_changed = False), то оно
        генерируется с помощью метода generate_name.
        """
        # Если в первый раз сохраняется, то сгенерируем inner_id этому объекту
        # В случае отсутствия комментария при создании, будет брать комментарий у Типа
        if self._state.adding:
            last_id = Item.objects.all().aggregate(largest=models.Max('inner_id'))['largest']

            if last_id is not None:
                self.inner_id = last_id + 1
            else:
                self.inner_id = 100000
            if not self.comment:
                self._set_default_comment()

        try:
            super().save(*args, **kwargs)
        except TypeError:
            # TypeError: Object of type ValidationError is not JSON serializable
            logger.exception('Error when saving Item')
            logger.info('Item.__dict__: %s', self.__dict__)
            raise

    def __str__(self):
        return str(self.marking)


class ERPSync(SoftDeleteModelMixin, models.Model):
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+', verbose_name=_('Автор'))
    type = models.CharField(max_length=7, choices=ERPSyncType.choices, verbose_name=_('Тип'))

    item = models.ForeignKey(
        Item, on_delete=models.CASCADE, null=True, blank=True, related_name='+',
        verbose_name=_('Изделие/Деталь/Сборочная единица'),
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, null=True, blank=True, related_name='+',
        verbose_name=_('Проект'),
    )

    status = models.CharField(
        max_length=11, choices=ERPSyncStatus.choices, default=ERPSyncStatus.PENDING, verbose_name=_('Статус'),
    )
    comment = models.TextField(null=True, blank=True, verbose_name=_('Комментарии'))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))

    start_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Дата начала'))
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Дата завершения'))

    class Meta:
        verbose_name = _('ERP синхронизация')
        verbose_name_plural = _('ERP синхронизации')
        ordering = ['-created_at']

    def get_instance(self):
        if self.type == ERPSyncType.ITEM:
            return self.item
        elif self.type == ERPSyncType.PROJECT:
            return self.project

        return None

    def get_instance_id(self):
        instance = self.get_instance()

        if instance:
            return instance.id

        return None

    def to_json(self):
        return {
            'id': self.id,
            'type': self.type,
            'instance': self.get_instance_id(),
            'status': self.status,
            'comment': self.comment,
        }

    def add_log(self, log_type, request=None, response=None):
        if isinstance(response, Exception):
            response = traceback.format_exc()

        ERPSyncLog.objects.create(
            erp_sync=self,
            log_type=log_type,
            request=request,
            response=response,
        )

    def __str__(self):
        instance = self.get_instance()
        return f'ERP Sync {self.id} -{instance} - {self.get_status_display()}'


class ERPSyncLog(SoftDeleteModelMixin, models.Model):
    erp_sync = models.ForeignKey(
        ERPSync, on_delete=models.CASCADE, related_name='logs', verbose_name=_('ERP синхронизация'),
    )
    log_type = models.CharField(max_length=12, choices=ERPSyncLogType.choices, verbose_name=_('Тип лога'))

    request = models.TextField(null=True, blank=True, verbose_name=_('Запрос'))
    response = models.TextField(null=True, blank=True, verbose_name=_('Ответ'))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))

    class Meta:
        verbose_name = _('Лог ERP синхронизации')
        verbose_name_plural = _('Логи ERP синхронизации')
        ordering = ['erp_sync', 'created_at']

    def __str__(self):
        return f'Log {self.id} for ERP Sync {self.erp_sync.id} - {self.get_log_type_display()}'


class ItemChild(SoftDeleteModelMixin, models.Model):
    parent = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='children', verbose_name=_('Родитель'))
    child = models.ForeignKey(
        Item, on_delete=models.PROTECT, related_name='parents', verbose_name=_('Дочерний элемент')
    )
    position = models.PositiveSmallIntegerField(verbose_name=_('Позиция'))
    count = models.PositiveSmallIntegerField(verbose_name=_('Количество'))

    historylog = HistoryModelTracker(excluded_fields=('id',), root_model='self', root_id=lambda ins: ins.id)

    class Meta:
        verbose_name = _('Спецификация')
        verbose_name_plural = _('Спепцификации')
        ordering = ('parent', 'position')
        permissions = (
            ('add_own_itemchild', _('Может создавать свою спецификацию')),
            ('change_own_itemchild', _('Может изменить свою спецификацию')),
            ('delete_own_itemchild', _('Может удалить свою спецификацию')),
            ('view_own_itemchild', _('Может видеть свою спецификацию')),
        )

    def clean(self):
        if self.parent == self.child:
            raise ValidationError(_('Родитель и дочерний элемент не могут быть одинаковыми.'))

        ancestor = self.parent
        while ancestor:
            if ancestor == self.child:
                raise ValidationError(_('Нельзя добавлять родителя в качестве дочернего элемента.'))
            ancestor_child_link = ItemChild.objects.filter(child=ancestor).first()
            ancestor = ancestor_child_link.parent if ancestor_child_link else None

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.parent}: #{self.position} {self.child} (Кол.: {self.count})'


class BaseComposition(SoftDeleteModelMixin, models.Model):
    base_parent = models.ForeignKey(
        DetailType, on_delete=models.PROTECT, related_name='base_parent', verbose_name=_('Сборка'),
        limit_choices_to=(Q(category=DetailType.PRODUCT) | Q(category=DetailType.ASSEMBLY_UNIT)),
    )
    base_parent_variant = models.ForeignKey(
        Variant, on_delete=models.PROTECT, related_name='base_parent', verbose_name=_('Сборка (Исполнение)'),
        null=True, blank=True,
    )
    base_child = models.ForeignKey(
        DetailType, on_delete=models.PROTECT, related_name='base_children',
        verbose_name=_('Комплектующий узел или деталь'),
        limit_choices_to=(Q(category=DetailType.ASSEMBLY_UNIT) | Q(category=DetailType.DETAIL)),
    )
    base_child_variant = models.ForeignKey(
        Variant, on_delete=models.PROTECT, related_name='base_children', null=True, blank=True,
        verbose_name=_('Комплектующий узел или деталь (Исполнение)'),
    )
    position = models.PositiveSmallIntegerField(verbose_name=_('Позиция'))
    count = models.PositiveSmallIntegerField(verbose_name=_('Количество'))

    historylog = HistoryModelTracker(excluded_fields=('id',), root_model='self', root_id=lambda ins: ins.id)

    objects = BaseCompositionSoftDeleteManager()
    all_objects = BaseCompositionAllObjectsManager()

    class Meta:
        verbose_name = _('Комплектующая базового состава')
        verbose_name_plural = _('Комплектующие базового состава')
        ordering = ('base_parent', 'position')

    def clean(self):
        if self.base_parent_variant and self.base_parent_variant.detail_type_id != self.base_parent_id:
            raise ValidationError(_('Исполнение не принадлежит типу детали'))

        if self.base_child_variant and self.base_child_variant.detail_type_id != self.base_child_id:
            raise ValidationError(_('Исполнение не принадлежит типу детали'))

        # TODO: Проверить с тем что поменялся в полях (добавился base_parent_detail_type и base_child_detail_type)
        if self.base_parent == self.base_child:
            raise ValidationError(_('Сборка не может содержать саму себя как комплектующий элемент.'))

        if self.base_parent_variant or self.base_child_variant:
            if self.base_parent_variant == self.base_child_variant:
                raise ValidationError(_('Сборка не может содержать саму себя как комплектующий элемент.'))

        ancestor = self.base_parent
        while ancestor:
            if ancestor == self.base_child:
                raise ValidationError(_('Сборка не может содержать своих предков в качестве комплектующих.'))
            ancestor_composition = BaseComposition.objects.filter(base_child=ancestor).first()
            ancestor = ancestor_composition.base_parent if ancestor_composition else None

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.base_parent}: #{self.position} {self.base_child} (Кол.: {self.count})'


class TmpCompositionManager(models.Manager):
    def add_tmp_composition(self, item):
        base_composition = BaseComposition.objects.filter(base_parent=item.variant)
        for part in base_composition:
            self.create(
                tmp_parent=item, tmp_child=part.base_child.detail_type, position=part.position, material=part.material,
                count=part.count
            )


# Это временный состав изделия Item, который требуется для заполнения эскизов, и потом его надо будет удалить
class TemporaryComposition(SoftDeleteModelMixin, models.Model):
    tmp_parent = models.ForeignKey(
        Item, verbose_name=_('Сборка'),
        limit_choices_to=(Q(type__category=DetailType.PRODUCT) | Q(type__category=DetailType.ASSEMBLY_UNIT)),
        on_delete=models.PROTECT, related_name='tmp_parent'
    )
    tmp_child = models.ForeignKey(
        DetailType, verbose_name=_('Комплектующий узел или деталь'),
        limit_choices_to=(Q(category=DetailType.ASSEMBLY_UNIT) | Q(category=DetailType.DETAIL)),
        on_delete=models.PROTECT, related_name='tmp_children',
    )
    position = models.PositiveSmallIntegerField(verbose_name=_('Позиция'))
    material = models.ForeignKey(Material, verbose_name=_('Материал'), null=True, blank=True, on_delete=models.PROTECT)
    count = models.PositiveSmallIntegerField(verbose_name=_('Количество'))

    # Временные поля
    tag_id = models.CharField(max_length=100, null=True, blank=True, verbose_name=_('Тег номер'))
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Наименование'))
    lgv = models.CharField(max_length=100, null=True, blank=True, verbose_name=_('LGV'))
    weight = models.FloatField(null=True, blank=True, verbose_name=_('Вес детали'))

    historylog = HistoryModelTracker(excluded_fields=('id',), root_model='self', root_id=lambda ins: ins.id)

    objects = TmpCompositionManager()

    class Meta:
        verbose_name = _('Временный состав изделия')
        verbose_name_plural = _('Временный состав изделия')
        ordering = ('tmp_parent', 'position')

    def __str__(self):
        return f'{self.tmp_parent}: #{self.position} {self.tmp_child} (Кол.: {self.count})'
