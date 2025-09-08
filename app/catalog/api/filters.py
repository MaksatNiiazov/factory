import django_filters
from auditlog.models import LogEntry
from django.db import models

from catalog.models import (
    PipeDiameter, LoadGroup, Material, NominalDiameter, CoveringType, Covering, SupportDistance,
    ProductFamily, PipeMountingGroup, PipeMountingRule, ComponentGroup, SpringBlockFamilyBinding,
    SSBCatalog, ClampMaterialCoefficient, SSGCatalog
)
from kernel.api import lookups
from kernel.api.filters import create_filterset
from constance import config

NominalDiameterFilter = create_filterset(NominalDiameter, {
    'dn': lookups.INTEGER_LOOKUPS,
})

PipeDiameterFilter = create_filterset(PipeDiameter, {
    'dn': lookups.FOREIGN_KEY_LOOKUPS,
    'option': lookups.CHOICES_LOOKUPS,
    'standard': lookups.CHOICES_LOOKUPS,
})

LoadGroupFilter = create_filterset(LoadGroup, {
    'lgv': lookups.INTEGER_LOOKUPS,
    'kn': lookups.INTEGER_LOOKUPS,
})

DEFAULT_INSULATED_TEMP = 1
MaterialFilter = create_filterset(Material, {
    'name': lookups.STRING_LOOKUPS,
    'name_ru': lookups.STRING_LOOKUPS,
    'name_en': lookups.STRING_LOOKUPS,
    'group': lookups.STRING_LOOKUPS,
    'type': lookups.CHOICES_LOOKUPS,
    'astm_spec': lookups.STRING_LOOKUPS,
    'asme_type': lookups.STRING_LOOKUPS,
    'asme_uns': lookups.STRING_LOOKUPS,
    'source': lookups.STRING_LOOKUPS,
    'min_temp': lookups.INTEGER_LOOKUPS,
    'max_temp': lookups.INTEGER_LOOKUPS,
    'max_exhaust_gas_temp': lookups.INTEGER_LOOKUPS,
    'lz': lookups.FLOAT_LOOKUPS,
    'density': lookups.FLOAT_LOOKUPS,
    'spring_constant': lookups.FLOAT_LOOKUPS,
    'rp0': lookups.INTEGER_LOOKUPS,
})

# Фильтр на наличие изоляции
MaterialFilter.base_filters['has_insulation'] = django_filters.BooleanFilter(method="filter_by_insulation")

# Фильтры для min_temp
MaterialFilter.base_filters['min_temp__lt'] = django_filters.NumberFilter(field_name="min_temp", lookup_expr="lt")
MaterialFilter.base_filters['min_temp__lte'] = django_filters.NumberFilter(field_name="min_temp", lookup_expr="lte")
MaterialFilter.base_filters['min_temp__gt'] = django_filters.NumberFilter(field_name="min_temp", lookup_expr="gt")
MaterialFilter.base_filters['min_temp__gte'] = django_filters.NumberFilter(field_name="min_temp", lookup_expr="gte")

# Фильтры для max_temp
MaterialFilter.base_filters['max_temp__lt'] = django_filters.NumberFilter(field_name="max_temp", lookup_expr="lt")
MaterialFilter.base_filters['max_temp__lte'] = django_filters.NumberFilter(field_name="max_temp", lookup_expr="lte")
MaterialFilter.base_filters['max_temp__gt'] = django_filters.NumberFilter(field_name="max_temp", lookup_expr="gt")
MaterialFilter.base_filters['max_temp__gte'] = django_filters.NumberFilter(field_name="max_temp", lookup_expr="gte")


def filter_by_insulation(self, queryset, name, value):
    """
    Если изоляция есть, игнорируются фильтры для min_temp и max_temp.
    Если изоляции нет, фильтры для min_temp и max_temp применяются как обычно.
    """
    if value:  # Если есть изоляция
        # Применяем фильтрацию по температуре 25°C

        queryset = queryset.filter(min_temp__lte=25, max_temp__gte=25)
    else:
        # Если изоляции нет, применяем фильтры для min_temp и max_temp
        if self.data.get('min_temp__lte'):
            queryset = queryset.filter(min_temp__lte=self.data.get('min_temp__lte'))
        if self.data.get('max_temp__gte'):
            queryset = queryset.filter(max_temp__gte=self.data.get('max_temp__gte'))

    return queryset


MaterialFilter.filter_by_insulation = filter_by_insulation


# Переписываем метод filter_queryset
def filter_queryset(self, queryset):
    """
    - Если изоляция есть, игнорируются фильтры для min_temp и max_temp.
    - Если изоляции нет, фильтры для min_temp и max_temp применяются как обычно.
    """
    has_insulation = self.form.cleaned_data.get('has_insulation')

    if has_insulation:
        # Если изоляция есть, фильтры для температур игнорируются
        for name, value in self.form.cleaned_data.items():
            if 'min_temp' not in name and 'max_temp' not in name:  # Пропускаем фильтры для температур
                queryset = self.filters[name].filter(queryset, value)
        # Фильтруем по температуре 25°C, игнорируя другие температурные фильтры
        queryset = queryset.filter(min_temp__lte=config.TEMPERATURE_WITH_INSULATION,
                                   max_temp__gte=config.TEMPERATURE_WITH_INSULATION)
    else:
        # Если изоляции нет, применяем все фильтры, включая фильтры для температур
        for name, value in self.form.cleaned_data.items():
            queryset = self.filters[name].filter(queryset, value)

    # Проверка, что queryset это все еще QuerySet
    assert isinstance(queryset, models.QuerySet), (
            "Expected '%s.%s' to return a QuerySet, but got a %s instead." % (
        type(self).__name__,
        name,
        type(queryset).__name__,
    )
    )

    return queryset


# Применяем этот метод в MaterialFilter
MaterialFilter.filter_queryset = filter_queryset

CoveringTypeFilter = create_filterset(CoveringType, {
    'numeric': lookups.INTEGER_LOOKUPS,
    'name': lookups.STRING_LOOKUPS,
    'name_ru': lookups.STRING_LOOKUPS,
    'name_en': lookups.STRING_LOOKUPS,
    'description': lookups.STRING_LOOKUPS,
    'description_ru': lookups.STRING_LOOKUPS,
    'description_en': lookups.STRING_LOOKUPS,
})

CoveringFilter = create_filterset(Covering, {
    'name': lookups.STRING_LOOKUPS,
    'name_ru': lookups.STRING_LOOKUPS,
    'name_en': lookups.STRING_LOOKUPS,
    'description': lookups.STRING_LOOKUPS,
    'description_ru': lookups.STRING_LOOKUPS,
    'description_en': lookups.STRING_LOOKUPS,
})

SupportDistanceFilter = create_filterset(SupportDistance, {
    'name': lookups.STRING_LOOKUPS,
    'value': lookups.FLOAT_LOOKUPS,
})

ProductFamilyFilter = create_filterset(ProductFamily, {
    "product_class": lookups.FOREIGN_KEY_LOOKUPS,
    "name": lookups.STRING_LOOKUPS,
    "is_upper_mount_selectable": lookups.BOOLEAN_LOOKUPS,
    "has_rod": lookups.BOOLEAN_LOOKUPS,
    "selection_type": lookups.CHOICES_LOOKUPS,
})


PipeMountingGroupFilter = create_filterset(PipeMountingGroup, {
    "name": lookups.STRING_LOOKUPS,
    "show_variants": lookups.BOOLEAN_LOOKUPS,
    "variants": lookups.ARRAY_LOOKUPS,
})


PipeMountingRuleFilter = create_filterset(PipeMountingRule, {
    'family': lookups.FOREIGN_KEY_LOOKUPS,
    'num_spring_blocks': lookups.INTEGER_LOOKUPS,
    'pipe_direction': lookups.CHOICES_LOOKUPS,
    'pipe_mounting_groups': lookups.ARRAY_LOOKUPS,
    'mounting_groups_b': lookups.ARRAY_LOOKUPS,
})


ComponentGroupFilter = create_filterset(ComponentGroup, {
    'id': lookups.INTEGER_LOOKUPS,
    'group_type': lookups.CHOICES_LOOKUPS,
    'detail_types': lookups.ARRAY_LOOKUPS,
})

SpringBlockFamilyBindingFilter = create_filterset(SpringBlockFamilyBinding, {
    'id': lookups.INTEGER_LOOKUPS,
    'family': lookups.FOREIGN_KEY_LOOKUPS,
    'spring_block_types': lookups.ARRAY_LOOKUPS,
})

SSBCatalogFilter = create_filterset(SSBCatalog, {
    'id': lookups.INTEGER_LOOKUPS,
    'fn': lookups.INTEGER_LOOKUPS,
    'f': lookups.INTEGER_LOOKUPS,
    'l': lookups.INTEGER_LOOKUPS,
    'l1': lookups.INTEGER_LOOKUPS,
    'l2_min': lookups.INTEGER_LOOKUPS,
    'l2_max': lookups.INTEGER_LOOKUPS,
    'l3_min': lookups.INTEGER_LOOKUPS,
    'l3_max': lookups.INTEGER_LOOKUPS,
    'l4': lookups.INTEGER_LOOKUPS,
    'a': lookups.INTEGER_LOOKUPS,
    'b': lookups.INTEGER_LOOKUPS,
    'h': lookups.INTEGER_LOOKUPS,
    'diameter_j': lookups.INTEGER_LOOKUPS,
})


SSGCatalogFilter = create_filterset(SSGCatalog, {
    'id': lookups.INTEGER_LOOKUPS,
    'fn': lookups.INTEGER_LOOKUPS,
    'l_min': lookups.INTEGER_LOOKUPS,
    'l_max': lookups.INTEGER_LOOKUPS,
    'l1': lookups.INTEGER_LOOKUPS,
    'd': lookups.INTEGER_LOOKUPS,
    'd1': lookups.INTEGER_LOOKUPS,
    'r': lookups.INTEGER_LOOKUPS,
    's': lookups.INTEGER_LOOKUPS,
    'sw': lookups.INTEGER_LOOKUPS,
    'regulation': lookups.INTEGER_LOOKUPS,
})


class LogEntryFilter(django_filters.FilterSet):
    model = django_filters.CharFilter(
        field_name='content_type__model', lookup_expr='iexact'
    )
    actor = django_filters.NumberFilter(
        field_name='actor__id'
    )
    timestamp_after = django_filters.IsoDateTimeFilter(
        field_name='timestamp', lookup_expr='gte'
    )
    timestamp_before = django_filters.IsoDateTimeFilter(
        field_name='timestamp', lookup_expr='lte'
    )
    field_changed = django_filters.CharFilter(
        method='filter_field_changed'
    )

    class Meta:
        model = LogEntry
        fields = ['model', 'actor', 'timestamp_after', 'timestamp_before']

    def filter_field_changed(self, queryset, name, value):
        return queryset.filter(changes__contains=value)


ClampMaterialCoefficientFilter = create_filterset(ClampMaterialCoefficient, {
    "id": lookups.INTEGER_LOOKUPS,
    "material_group": lookups.STRING_LOOKUPS,
    "temperature_from": lookups.INTEGER_LOOKUPS,
    "temperature_to": lookups.INTEGER_LOOKUPS,
    "coefficient": lookups.FLOAT_LOOKUPS,
})
