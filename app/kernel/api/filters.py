from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import FieldDoesNotExist

from django.db import models

from django_filters import rest_framework as filters

from . import lookups
from ..models import Organization

User = get_user_model()


def resolve_field(model, field_path):
    parts = field_path.split('__')
    current_model = model
    for index, part in enumerate(parts):
        field = current_model._meta.get_field(part)
        if index < len(parts) - 1:
            if not getattr(field, 'remote_field', None):
                raise FieldDoesNotExist()
            current_model = field.remote_field.model
        else:
            return field

def create_filterset(model, fields):
    filter_fields = {}
    for field_path, lookups_list in fields.items():
        try:
            django_field = resolve_field(model, field_path)
        except FieldDoesNotExist:
            continue
        for lookup in lookups_list:
            filter_name = f"{field_path}__{lookup}"
            filter_class = None
            if lookup == 'exact':
                if isinstance(django_field, (models.CharField, models.TextField)):
                    filter_class = filters.CharFilter
                elif isinstance(django_field, models.IntegerField):
                    filter_class = filters.NumberFilter
                elif isinstance(django_field, models.DateField):
                    filter_class = filters.DateFilter
                elif isinstance(django_field, models.BooleanField):
                    filter_class = filters.BooleanFilter
                elif isinstance(django_field, (models.ForeignKey, models.OneToOneField)):
                    related_model = django_field.remote_field.model
                    filter_class = filters.ModelChoiceFilter
                    filter_fields[filter_name] = filter_class(
                        field_name=field_path,
                        lookup_expr=lookup,
                        queryset=related_model.objects.all()
                    )
                    filter_fields[field_path] = filter_class(
                        field_name=field_path,
                        lookup_expr=lookup,
                        queryset=related_model.objects.all()
                    )
                    continue
            elif lookup == 'isnull':
                filter_class = filters.BooleanFilter
            elif lookup == 'regex':
                filter_class = filters.CharFilter
            elif lookup == 'in':
                filter_class = filters.BaseInFilter
            elif lookup in ['istartswith', 'iendswith', 'icontains']:
                filter_class = filters.CharFilter
            elif lookup == 'range':
                if isinstance(django_field, (models.DateField, models.DateTimeField)):
                    filter_class = filters.DateFromToRangeFilter
            elif lookup in ['lt', 'lte', 'gt', 'gte']:
                if isinstance(django_field, (models.DateField, models.DateTimeField)):
                    filter_class = filters.DateFilter
            elif lookup in ['day', 'week_day', 'month', 'year']:
                if isinstance(django_field, (models.DateField, models.DateTimeField)):
                    filter_class = filters.NumberFilter
            if not filter_class:
                continue
            filter_fields[filter_name] = filter_class(
                field_name=field_path,
                lookup_expr=lookup
            )
            if lookup == 'exact':
                filter_fields[field_path] = filter_class(
                    field_name=field_path,
                    lookup_expr='exact'
                )
    meta_class = type("Meta", (), {
        "model": model,
        "fields": {
            field_name: ['exact']
            for field_name, lookups_list in fields.items()
            if 'exact' in lookups_list
        }
    })
    DynamicFilterSet = type(
        "DynamicFilterSet",
        (filters.FilterSet,),
        {"Meta": meta_class, **filter_fields},
    )
    return DynamicFilterSet


OrganizationFilter = create_filterset(Organization, {
    'name': lookups.STRING_LOOKUPS,
    'external_id': lookups.STRING_LOOKUPS,
    'inn': lookups.STRING_LOOKUPS,
    'kpp': lookups.STRING_LOOKUPS,
    'payment_bank': lookups.STRING_LOOKUPS,
    'payment_account': lookups.STRING_LOOKUPS,
    'bik': lookups.STRING_LOOKUPS,
    'correspondent_account': lookups.STRING_LOOKUPS,
})

GroupFilter = create_filterset(Group, {
    'name': lookups.STRING_LOOKUPS,
})

UserFilter = create_filterset(User, {
    'first_name': lookups.STRING_LOOKUPS,
    'last_name': lookups.STRING_LOOKUPS,
    'middle_name': lookups.STRING_LOOKUPS,
    'email': lookups.STRING_LOOKUPS,
    'status': lookups.CHOICES_LOOKUPS,
    'crm_login': lookups.STRING_LOOKUPS,
    'is_staff': lookups.BOOLEAN_LOOKUPS,
    'is_active': lookups.BOOLEAN_LOOKUPS,
    'is_superuser': lookups.BOOLEAN_LOOKUPS,
    'date_joined': lookups.DATE_LOOKUPS,
    'last_login': lookups.DATE_LOOKUPS,
    'organization': lookups.FOREIGN_KEY_LOOKUPS,
})
