import json
from typing import Optional, Any, Type, Tuple, Dict, List
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.fields import Field
from import_export.resources import ModelDeclarativeMetaclass
from import_export.results import RowResult
from rest_framework.exceptions import ValidationError

from catalog.models import Material
from ops.models import Item, DetailType, Attribute, Variant

User = get_user_model()


def dehydrate_attr(attr: str):
    """
    Возвращает функцию dehydrate, которая сериализует простой атрибут объекта.
    :param attr: Название атрибута модели
    :return: Функция dehydrate
    """

    def dehydrate(self, obj: Any) -> Optional[str]:
        if obj is None:
            return None
        value = getattr(obj, attr, None)
        return str(value) if value is not None else None

    return dehydrate


def dehydrate_attr_name(attr: str):
    """
    Возвращает функцию dehydrate, которая сериализует атрибут-ссылку по имени (например, ForeignKey.name).
    :param attr: Название поля ForeignKey
    :return: Функция dehydrate
    """

    def dehydrate(self, obj: Any) -> Optional[str]:
        if obj is None:
            return None
        value = getattr(obj, attr, None)
        if value is None or not getattr(value, "name", None):
            return None
        return str(value.name)

    return dehydrate


def dehydrate_parameters(parameter: str):
    """
    Возвращает функцию dehydrate, которая сериализует параметр из словаря parameters.
    :param parameter: Ключ параметра в словаре
    :return: Функция dehydrate
    """

    def dehydrate(self, obj: Any) -> Optional[str]:
        if not obj or not hasattr(obj, "parameters") or obj.parameters is None:
            return None
        value = obj.parameters.get(parameter)
        return str(value) if value is not None else None

    return dehydrate


def dehydrate_material_parameter():
    """
    Возвращает функцию dehydrate для поля 'material' из parameters, которая возвращает имя материала по ID.
    :return: Функция dehydrate
    """

    def dehydrate(self, obj: Any) -> Optional[str]:
        if not obj or not hasattr(obj, "parameters") or obj.parameters is None:
            return None
        material_id = obj.parameters.get("material")
        if material_id is None:
            return None
        if not hasattr(self, 'materials_by_id') or self.materials_by_id is None:
            return str(material_id)
        material = self.materials_by_id.get(material_id)
        return str(material.name) if material else str(material_id)

    return dehydrate


def normalize_value(val: Any) -> Optional[str]:
    """
    Нормализует значение:
     - удаляет пробелы
     - парсит JSON, если это строка-словарь
     - приводит к строке
    :return: нормализованная строка или None
    """
    if isinstance(val, str) and val.startswith('{') and val.endswith('}'):
        try:
            val = json.loads(val)
        except Exception:
            pass
    if isinstance(val, str):
        val = val.strip()
    return str(val) if val is not None else None


def is_duplicate(row: Dict[str, Any], instance: Item, fields: List[str],
                 materials_by_id: Dict[int, Material], materials_by_name: Dict[str, Material]) -> bool:
    """
    Проверяет, является ли строка row дубликатом объекта instance по набору полей.
    :param row: Словарь строки из импорта
    :param instance: Существующий объект Item
    :param fields: Список полей для сравнения
    :param materials_by_id: Словарь материалов по ID
    :param materials_by_name: Словарь материалов по имени
    :return: True, если дубликат
    """
    for field in fields:
        if field == 'id':
            continue
        elif field == 'variant':
            row_variant = normalize_value(row.get('variant'))
            inst_variant = normalize_value(instance.variant.name if instance.variant else None)
            if row_variant != inst_variant:
                return False
        elif field.lower() == 'material':
            row_material = row.get(field)
            inst_material = instance.parameters.get(field) if instance.parameters else None

            row_material_id = None
            if row_material:
                try:
                    row_material_id = int(row_material)
                except (ValueError, TypeError):
                    row_material_obj = materials_by_name.get(
                        str(row_material).strip().lower()) if materials_by_name else None
                    row_material_id = row_material_obj.id if row_material_obj else None

            try:
                inst_material_id = int(inst_material) if inst_material is not None else None
            except (ValueError, TypeError):
                inst_material_id = None

            if row_material_id != inst_material_id:
                return False
        else:
            row_value = normalize_value(row.get(field))
            inst_value = normalize_value(instance.parameters.get(field)) if instance.parameters else None
            if row_value != inst_value:
                if inst_value is None:
                    continue
                return False
    return True


class DehydrateMetaClass(ModelDeclarativeMetaclass):
    """
    Мета-класс, автоматически добавляющий методы dehydrate_* по полям.
    """
    def __new__(cls: Type[ModelDeclarativeMetaclass], name: str, bases: Tuple[type], attrs: Dict[str, Any]):
        new_class = super().__new__(cls, name, bases, attrs)
        for name in attrs.get('fields', {}).keys():
            if name == 'id':
                setattr(new_class, f'dehydrate_{name}', dehydrate_attr(name))
            elif name == 'material':
                setattr(new_class, f'dehydrate_{name}', dehydrate_material_parameter())
            elif name == 'variant':
                setattr(new_class, f'dehydrate_{name}', dehydrate_attr_name(name))
            else:
                setattr(new_class, f'dehydrate_{name}', dehydrate_parameters(name))
        return new_class


class Base(resources.ModelResource, metaclass=DehydrateMetaClass):
    """
    Базовый класс ресурса для импорта/экспорта Items.
    """
    category = None
    designation = None

    def __init__(self, **kwargs):
        self.base_attrs_by_type_id = None
        self.materials_by_name = None
        self.items_by_variant = None
        self.materials_by_id = None
        self.variant_attrs_by_id = None
        self.base_attrs = None
        self.variant_attrs = None
        self.variants_by_name = None
        self.detail_type = None
        self.user: Optional[User] = None
        self.material_warnings: List[Dict[str, Any]] = []
        super().__init__(**kwargs)

    def import_data(self, dataset, dry_run=False, raise_errors=False,
                    use_transactions=None, rollback_on_validation_errors=None,
                    user=None, **kwargs):
        self.user = user
        return super().import_data(
            dataset,
            dry_run=dry_run,
            raise_errors=raise_errors,
            use_transactions=use_transactions,
            rollback_on_validation_errors=rollback_on_validation_errors,
            **kwargs
        )

    def import_row(self, row, instance_loader, **kwargs):
        if all(value is None for value in row.values()):
            row_result = RowResult()
            row_result.import_type = "skip"
            row_result.diff = []
            return row_result
        return super().import_row(row, instance_loader, **kwargs)

    def get_import_id_fields(self) -> List[str]:
        return ['id', 'variant']

    def get_or_init_instance(self, instance_loader: Any, row: Dict[str, Any]) -> Tuple[Item, bool]:
        detail_type = self.detail_type
        item_id = row.get('id')
        if item_id:
            try:
                instance = Item.objects.get(id=item_id)
                return instance, False
            except Item.DoesNotExist:
                pass

        variant_value = row.get('variant')
        variant = self.variants_by_name.get(variant_value) if variant_value else next(iter(self.variants_by_name.values()), None)
        if not variant:
            raise Exception(_(f'Исполнение "{variant_value}" не найдено для типа {detail_type}'))

        compare_fields = ['variant'] + list(self.base_attrs | self.variant_attrs)
        for candidate in self.items_by_variant.get(variant.name, []):
            if is_duplicate(row, candidate, compare_fields, self.materials_by_id, self.materials_by_name):
                return candidate, False

        return Item(type=detail_type, variant=variant, author=self.user), True

    def before_import(self, dataset: Any, **kwargs):
        self.user = self.user or User.objects.filter(is_superuser=True).first()

        if self.category and self.designation:
            try:
                self.detail_type = DetailType.objects.get(category=self.category, designation=self.designation)
            except DetailType.DoesNotExist:
                raise ValidationError(f"DetailType не найден для '{self.category}' и '{self.designation}'")

            self.variants_by_name = {
                v.name: v for v in Variant.objects.filter(deleted_at=None, detail_type=self.detail_type)
            }
            self.variant_attrs = set(
                Attribute.objects.filter(variant__detail_type=self.detail_type).values_list('name', flat=True))
            self.base_attrs = set(
                Attribute.objects.filter(detail_type=self.detail_type, variant__isnull=True).values_list('name',
                                                                                                         flat=True))
            self.materials_by_id = {m.id: m for m in Material.objects.all() if m.id is not None}
            self.materials_by_name = {m.name.strip().lower(): m for m in Material.objects.all() if m.name}
            self.items_by_variant = defaultdict(list)
            for item in Item.objects.filter(type=self.detail_type).select_related('variant'):
                if item.variant:
                    self.items_by_variant[item.variant.name].append(item)

        return super().before_import(dataset, **kwargs)

    def import_field(self, field: Field, obj: Item, data: Dict[str, Any], is_m2m=False, **kwargs):
        column_name = field.column_name
        value = data.get(column_name)
        if obj.parameters is None:
            obj.parameters = {}

        if column_name.lower() == 'material':
            try:
                material = self.materials_by_id.get(int(value))
            except (ValueError, TypeError):
                material = self.materials_by_name.get(str(value).strip().lower())

            if material:
                obj.parameters[column_name] = material.id
            else:
                obj.parameters[column_name] = None
                self.material_warnings.append({
                    'detail_id': getattr(obj, 'inner_id', 'Новый объект'),
                    'material_value': value,
                    'message': f'Материал "{value}" не найден.'
                })
        elif column_name in getattr(self, 'allowed_parameter_fields', set()):
            obj.parameters[column_name] = value

    def after_import(self, dataset: Any, result: Any, using_transactions: bool, dry_run: bool, **kwargs):
        items = Item.objects.select_related('type').filter(Q(name__isnull=True) | Q(name=''))
        for item in items:
            item.name = item.marking
        Item.objects.bulk_update(items, fields=['name'])

    class Meta:
        model = Item
        fields = []
        use_bulk = False
        clean_model_instances = True

    @classmethod
    def get_display_name(cls) -> Optional[str]:
        return f'{cls.category}_{cls.designation}'


def get_resources_list() -> List[Type[Base]]:
    classes = []
    cats_and_desigs = DetailType.objects.values_list('category', 'designation').distinct()
    all_attrs = Attribute.objects.select_related('variant__detail_type', 'detail_type')

    variant_attrs_map = defaultdict(set)
    base_attrs_map = defaultdict(set)

    for attr in all_attrs:
        detail_type = attr.detail_type or (attr.variant.detail_type if attr.variant else None)
        if not detail_type:
            continue
        key = (detail_type.category, detail_type.designation)
        if attr.variant_id:
            variant_attrs_map[key].add(attr.name)
        else:
            base_attrs_map[key].add(attr.name)

    for category, designation in cats_and_desigs:
        standard_fields = ['id', 'variant']
        variant_attrs = sorted(variant_attrs_map.get((category, designation), []))
        base_attrs = sorted(base_attrs_map.get((category, designation), []))
        all_fields = standard_fields + base_attrs + variant_attrs

        class_name = f'{category}_{designation}'
        class_attributes = {
            'category': category,
            'designation': designation,
            'allowed_parameter_fields': set(all_fields) - {'id', 'variant'},
            **{f: Field() for f in all_fields}
        }

        MetaClass = type('Meta', (Base.Meta,), {
            'model': Item,
            'fields': all_fields,
            'use_bulk': False,
        })
        class_attributes['Meta'] = MetaClass
        klazz = type(class_name, (Base,), class_attributes)
        classes.append(klazz)

    return classes
