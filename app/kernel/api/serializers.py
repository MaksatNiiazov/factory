import pytz
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from rest_flex_fields import FlexFieldsModelSerializer
from rest_framework.exceptions import ValidationError

from kernel.api.base import CleanSerializerMixin, ChoicesSerializer
from kernel.models import Organization
from ops.models import DetailType

User = get_user_model()


class OrganizationSerializer(CleanSerializerMixin, FlexFieldsModelSerializer):
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'external_id',
            'inn', 'kpp', 'payment_bank', 'payment_account', 'bik',
            'correspondent_account', 'file',
        ]


class PermissionSerializer(CleanSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename']


class GroupSerializer(CleanSerializerMixin, FlexFieldsModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class UserSerializer(CleanSerializerMixin, FlexFieldsModelSerializer):
    password = serializers.CharField(write_only=True, required=True, label=_('Пароль'))
    permissions = serializers.SerializerMethodField(read_only=True, label=_('Разрешения'))
    is_active = serializers.BooleanField(required=False, default=True, label=_('Активный'))
    display_name = serializers.SerializerMethodField(label=_('Отображаемое имя'))
    full_name = serializers.SerializerMethodField(label=_('Полное имя'))

    def get_display_name(self, instance):
        return instance.display_name

    def get_full_name(self, instance):
        return instance.full_name

    def get_permissions(self, instance):
        if isinstance(instance, User):
            permissions = instance.get_all_permissions()
        else:
            permissions = []

        return permissions

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'middle_name', 'email',
            'password', 'status', 'crm_login', 'organization',
            'is_staff', 'is_active', 'is_superuser', 'date_joined',
            'last_login', 'permissions', 'ui_config', 'display_name', 'full_name',
        ]
        expandable_fields = {
            'organization': OrganizationSerializer,
            'status': (ChoicesSerializer, {'model': User, 'field_name': 'status'}),
        }


class ItemTableSerializer(serializers.Serializer):
    detail_type = serializers.PrimaryKeyRelatedField(
        queryset=DetailType.objects.all(), required=True, label=_('Тип детали/изделия')
    )
    attributes = serializers.ListField(required=True, allow_null=True, label=_('Список атрибутов'))


def validate_locale(value):
    locales = [lang[0] for lang in settings.LANGUAGES]

    if value not in locales:
        locales_f = ', '.join(locales)
        raise ValidationError(_(f'Язык {value} отсутствует в списке поддерживаемых языков: {locales_f}'))

    return value


def validate_timezone(value):
    all_timezones = pytz.all_timezones

    if value not in all_timezones:
        raise ValidationError(_(f'Временная зона {value} отсутствует в списке временных зон'))

    return value


class UserLocaleSerializer(serializers.Serializer):
    locale = serializers.CharField(required=True, validators=[validate_locale], label=_('Язык'))


class UserTimeZoneSerializer(serializers.Serializer):
    timezone = serializers.CharField(required=True, validators=[validate_timezone], label=_('Временная зона'))


class LoginSerializer(serializers.Serializer):
    """
    Serializer для входа в систему
    """
    username = serializers.CharField(label=_('Логин'), required=True)
    password = serializers.CharField(label=_('Пароль'), required=True)
