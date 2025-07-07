import pytz
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate, login as django_login, logout as django_logout
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _, get_language_info
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, NotFound, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from kernel.api.filter_backends import MappedOrderingFilter
from kernel.api.filters import OrganizationFilter, GroupFilter, UserFilter
from kernel.api.permissions import (
    ActionPermission, AuthorizationPermission, CurrentUserInfoPermission, CurrentUserRequiredPermission,
    CurrentUserCanChangePermission
)
from kernel.api.serializers import UserSerializer, LoginSerializer, OrganizationSerializer, ItemTableSerializer, \
    UserLocaleSerializer, UserTimeZoneSerializer, GroupSerializer
from kernel.models import Organization
from ops.models import Attribute

User = get_user_model()


class MeToUserIdMixin:
    """
    Конвертирует `me` в идентификатор текущего пользователя
    """

    def initial(self, request, *args, **kwargs):
        user_id = kwargs.get("pk")

        if user_id == "me" and request.user.is_authenticated:
            self.kwargs["pk"] = request.user.id

        return super().initial(request, *args, **kwargs)


class CustomModelViewSet(ModelViewSet):
    http_method_names = ["get", "post", "patch", "delete"]


class OrganizationViewSet(CustomModelViewSet):
    """
    API для работы с организацией.
    list: Получить список организации
    retrieve: Получить организацию по его идентификатору `id`
    create: Создать новую организацию
    partial_update: Изменить организацию по его идентификатору `id`
    destroy: Удалить организацию по его идентификатору `id`
    """
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter, SearchFilter]
    filterset_class = OrganizationFilter

    ordering_fields = (
        'id', 'name', 'external_id', 'inn', 'kpp', 'payment_bank', 'payment_account', 'bik', 'correspondent_account',
    )
    search_fields = (
        'id', 'name', 'external_id', 'inn', 'kpp', 'payment_bank', 'payment_account', 'bik', 'correspondent_account',
    )


class GroupViewSet(CustomModelViewSet):
    """
    API для работы с группой пользователей.
    list: Возвращает список групп пользователей.
    retrieve: Получить группу пользователя по его идентификатору `id`
    create: Создать нового группу пользователя
    partial_update: Изменить группу пользователя по его идентификатору `id`
    destroy: Удалить группу пользователя по его идентификатору `id`
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter, SearchFilter]
    filterset_class = GroupFilter
    ordering_fields = ['id', 'name']
    search_fields = ['id', 'name']


class UserViewSet(MeToUserIdMixin, CustomModelViewSet):
    """
    API для работы с пользователями.
    list: Возвращает список пользователей
    retrieve: Получить пользователя по его идентификатору `id`
    create: Создать нового пользователя
    partial_update: Изменить пользователя по его идентификатору `id`
    destroy: Удалить пользователя по его идентификатору `id`
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [
        CurrentUserCanChangePermission | CurrentUserRequiredPermission | ActionPermission | AuthorizationPermission
        | CurrentUserInfoPermission
    ]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter, SearchFilter]
    filterset_class = UserFilter

    ordering_fields = [
        'id', 'first_name', 'last_name', 'middle_name', 'email', 'status', 'crm_login', 'date_joined', 'last_login'
    ]
    search_fields = ['id', 'first_name', 'last_name', 'middle_name', 'crm_login', 'email']

    def get_serializer_class(self):
        if self.action == 'login':
            return LoginSerializer
        elif self.action == 'logout':
            return Serializer
        elif self.action == 'set_item_table_columns':
            return ItemTableSerializer
        elif self.action == 'set_locale':
            return UserLocaleSerializer
        elif self.action == 'set_timezone':
            return UserTimeZoneSerializer

        return self.serializer_class

    def perform_create(self, serializer):
        user = User.objects.create_user(**serializer.validated_data)
        serializer.instance = user

    def perform_update(self, serializer):
        instance = serializer.instance
        validated_data = serializer.validated_data

        password = validated_data.pop('password', None)

        if password:
            instance.set_password(password)

        super().perform_update(serializer)

    @action(methods=['POST'], detail=False)
    def login(self, request):
        """
        API-точка для выполнения авторизации по логину и паролю
        """
        serializer_class = self.get_serializer_class()

        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(request, **serializer.data)

        if user:
            request.session.clear()
            django_login(request, user)

            serializer = UserSerializer(user)

            data = serializer.data
            data['token'] = request.session.session_key
            data['token_expired_at'] = request.session.get_expiry_date()

            return Response(data)
        else:
            raise AuthenticationFailed

    @action(methods=["POST"], detail=False)
    def logout(self, request):
        """
        API-точка для выхода из системы
        """
        django_logout(request)
        return Response()

    @action(methods=["POST"], detail=True)
    def set_item_table_columns(self, request, pk):
        """
        Позволяет настраивать столбцы в таблице деталей/изделии.
        """

        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            raise NotFound

        ui_config = user.ui_config

        if not ui_config:
            ui_config = {}

        if 'item_table' not in ui_config:
            ui_config['item_table'] = {}

        serializer_class = self.get_serializer_class()

        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        detail_type_pk = str(data['detail_type'].id)
        attributes = set(data['attributes'])

        available_attributes = {
            'id', 'type', 'variant', 'inner_id', 'name', 'marking', 'weight',
            'material', 'author', 'created', 'modified',
        }
        available_attributes.update(
            set(Attribute.objects.filter(variant__detail_type_id=detail_type_pk).values_list('name', flat=True))
        )

        wrong_attributes = attributes - available_attributes

        if wrong_attributes:
            wrong_attributes = ', '.join(wrong_attributes)
            raise ValidationError(
                {'attributes': _(f'Следующие атрибуты являются не существующими: {wrong_attributes}')}
            )

        if attributes is None:
            ui_config['item_table'].pop(detail_type_pk, None)
        else:
            ui_config['item_table'][detail_type_pk] = list(attributes)

        user.ui_config = ui_config
        user.save()

        serializer = UserSerializer(instance=user)

        return Response(serializer.data)

    @action(methods=["POST"], detail=True)
    def set_locale(self, request, pk):
        """
        Позволяет указать язык интерфейса/приложения для пользователя
        """

        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            raise NotFound

        ui_config = user.ui_config

        if not ui_config:
            ui_config = {}

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ui_config['locale'] = data['locale']

        user.ui_config = ui_config
        user.save()

        serializer = UserSerializer(instance=user)

        return Response(serializer.data)

    @action(methods=["POST"], detail=True)
    def set_timezone(self, request, pk):
        """
        Позволяет указать временную зону пользователя
        """

        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            raise NotFound

        ui_config = user.ui_config

        if not ui_config:
            ui_config = {}

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ui_config['timezone'] = data['timezone']

        user.ui_config = ui_config
        user.save()

        serializer = UserSerializer(instance=user)

        return Response(serializer.data)


class TimeZonesApiView(APIView):
    """
    Получить список доступных временных зон
    """

    def get(self, request, *args, **kwargs):
        timezones = pytz.all_timezones
        timezones = [{
            'code': timezone,
            'title': timezone,
        } for timezone in timezones]

        return Response(timezones)


class LanguagesAPIView(APIView):
    """
    Получить список доступных языков
    """

    def get(self, request, *args, **kwargs):
        language_codes = [lang[0] for lang in settings.LANGUAGES]
        language_codes = [{
            'code': lang[0],
            'title': get_language_info(lang[0])['name_local'],
        } for lang in settings.LANGUAGES]

        return Response(language_codes)
