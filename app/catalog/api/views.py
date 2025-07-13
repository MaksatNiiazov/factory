from auditlog.models import LogEntry
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from catalog.api.exceptions import DirectoryFieldNotFound
from catalog.api.filters import (
    NominalDiameterFilter, PipeDiameterFilter, LoadGroupFilter, MaterialFilter,
    CoveringTypeFilter, CoveringFilter, SupportDistanceFilter, ProductFamilyFilter, PipeMountingGroupFilter,
    PipeMountingRuleFilter, ComponentGroupFilter, LogEntryFilter, SpringBlockFamilyBindingFilter, SSBCatalogFilter,
    ClampMaterialCoefficientFilter, SSGCatalogFilter,
)
from catalog.api.serializers import (
    PipeDiameterSerializer, LoadGroupSerializer, MaterialSerializer,
    NominalDiameterSerializer, CoveringTypeSerializer, CoveringSerializer, DirectorySerializer,
    DirectoryFieldSerializer, SupportDistanceSerializer, ProductFamilySerializer, ProductClassSerializer,
    LoadSerializer, SpringStiffnessSerializer, PipeMountingGroupSerializer, PipeMountingRuleSerializer,
    ComponentGroupSerializer, LogEntrySerializer, SpringBlockFamilyBindingSerializer, SSBCatalogSerializer,
    ClampMaterialCoefficientSerializer, SSGCatalogSerializer,
)
from catalog.models import (
    PipeDiameter, LoadGroup, Material, NominalDiameter, CoveringType, Covering, Directory,
    DirectoryEntry, DirectoryEntryValue, DirectoryField, SupportDistance, ProductFamily, ProductClass, Load,
    SpringStiffness, PipeMountingGroup, PipeMountingRule, ComponentGroup, SpringBlockFamilyBinding, SSBCatalog,
    SSGCatalog, ClampMaterialCoefficient,
)
from catalog.services.materials import get_materials_by_temperature_service
from catalog.services.pipe_diameter import get_dn_by_diameter_service

from kernel.api.filter_backends import MappedOrderingFilter
from kernel.api.permissions import ActionPermission, AnyOneCanViewPermission
from kernel.api.views import CustomModelViewSet


class DirectoryViewSet(ModelViewSet):
    queryset = Directory.objects.all()
    serializer_class = DirectorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'name']
    permission_classes = [AnyOneCanViewPermission | ActionPermission]


class DirectoryFieldViewSet(ModelViewSet):
    serializer_class = DirectoryFieldSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['id', 'directory', 'name']

    def get_queryset(self):
        directory_id = self.kwargs.get('directory_pk')
        return DirectoryField.objects.filter(directory_id=directory_id)

    def perform_create(self, serializer):
        directory_id = self.kwargs.get('directory_pk')
        directory = get_object_or_404(Directory, id=directory_id)
        serializer.save(directory=directory)


class DirectoryEntryViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    list: Возвращает список записей для указанного справочника.
    retrieve: Возвращает одну запись по его идентификатору.
    create: Создает новую запись в указанном справочнике.
    update: Выполняет полное обновление записи (PUT).
    partial_update: Выполняет частичное обновление записи (PATCH).
    destroy: Удаляет запись из справочника.
    """
    permission_classes = [AnyOneCanViewPermission | ActionPermission]

    def get_queryset(self):
        directory_id = self.kwargs.get('directory_pk')
        return DirectoryEntry.objects.filter(directory_id=directory_id).prefetch_related(
            'values', 'values__directory_field'
        )

    def get_directory(self):
        directory_id = self.kwargs.get('directory_pk')
        return get_object_or_404(Directory, pk=directory_id)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        data = [self._serialize_entry(e) for e in queryset]
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        entry = self.get_object()
        return Response(self._serialize_entry(entry))

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="Словарь, где ключи — названия полей справочника, а значения — данные",
            additional_properties=openapi.Schema(type=openapi.TYPE_STRING)
        ))
    def create(self, request, *args, **kwargs):
        directory = self.get_directory()
        data = request.data
        if not isinstance(data, dict):
            raise ValidationError("Тело запроса должно быть JSON-объектом")

        entry = DirectoryEntry.objects.create(directory=directory)

        try:
            for field_name, raw_value in data.items():
                directory_field = directory.fields.filter(name=field_name).first()
                if not directory_field:
                    # entry.delete()
                    raise DirectoryFieldNotFound(f'Поле "{field_name}" не найдено в справочнике {directory.name}.')

                entry_value = DirectoryEntryValue(entry=entry, directory_field=directory_field)
                entry_value.set_value(raw_value)  # Здесь может возникнуть ошибка

        except ValidationError as e:
            entry.delete()  # Удаляем запись, если была ошибка
            raise DRFValidationError(str(e))  # Преобразуем ошибку для DRF

        response_data = self._serialize_entry(entry)
        return Response(response_data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="Словарь, где ключи — названия полей справочника, а значения — данные",
            additional_properties=openapi.Schema(type=openapi.TYPE_STRING)
        ))
    def update(self, request, *args, **kwargs):
        entry = self.get_object()
        data = request.data
        if not isinstance(data, dict):
            raise ValidationError(_('Тело запроса должно быть JSON-объектом.'))

        directory = entry.directory
        existing_values = {v.directory_field.name: v for v in entry.values.all()}

        for field_name, raw_value in data.items():
            directory_field = entry.directory.fields.filter(name=field_name).first()
            if not directory_field:
                raise DirectoryFieldNotFound(f'Поле "{field_name}" не найдено в справочнике {directory.name}.')

            if field_name in existing_values:
                existing_values[field_name].set_value(raw_value)
            else:
                new_value = DirectoryEntryValue(entry=entry, directory_field=directory_field)
                new_value.set_value(raw_value)

        return Response(self._serialize_entry(entry), status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="Словарь, где ключи — названия полей справочника, а значения — данные",
            additional_properties=openapi.Schema(type=openapi.TYPE_STRING)
        ))
    def partial_update(self, request, *args, **kwargs):
        entry = self.get_object()
        data = request.data
        if not isinstance(data, dict):
            raise ValidationError(_("Тело запроса должно быть JSON-объектом."))

        directory = entry.directory
        existing_values = {v.directory_field.name: v for v in entry.values.all()}

        for field_name, raw_value in data.items():
            directory_field = directory.fields.filter(name=field_name).first()
            if not directory_field:
                raise ValidationError(_(f"Поле '{field_name}' не найдено в справочнике {directory.name}."))

            if field_name in existing_values:
                existing_values[field_name].set_value(raw_value)
            else:
                new_val = DirectoryEntryValue(entry=entry, directory_field=directory_field)
                new_val.set_value(raw_value)

        return Response(self._serialize_entry(entry))

    def destroy(self, request, *args, **kwargs):
        entry = self.get_object()
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _serialize_entry(self, entry) -> dict:
        data = {'id': entry.id, 'display_name': entry.display_name, 'display_name_errors': entry.display_name_errors}
        for value_obj in entry.values.select_related('directory_field'):
            data[value_obj.directory_field.name] = value_obj.value
        return data


class NominalDiameterViewSet(CustomModelViewSet):
    """
    API для работы со справочником "Номинальные диаметры"
    list: Получить список элементов
    retrieve: Получить элемент
    create: Создать новый элемент
    partial_update: Изменить элемент
    destroy: Удалить элемент
    """
    queryset = NominalDiameter.objects.all()
    serializer_class = NominalDiameterSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter, SearchFilter]
    filterset_class = NominalDiameterFilter

    ordering = ('id', 'dn')
    search_fields = ('dn',)


class PipeDiameterViewSet(CustomModelViewSet):
    """
    API для работы со справочником "Диаметры труб"
    list: Получить список элементов
    retrieve: Получить элемент
    create: Создать новый элемент
    partial_update: Изменить элемент
    destroy: Удалить элемент
    """
    queryset = PipeDiameter.objects.all()
    serializer_class = PipeDiameterSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter, SearchFilter]
    filterset_class = PipeDiameterFilter

    ordering = ('id', 'dn', 'option', 'standard', 'size')
    search_fields = ('dn', 'size')

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'size', openapi.IN_QUERY,
                description="Фактический внешний диаметр трубы (в мм). Можно передавать несколько значений через запятую.",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'standard', openapi.IN_QUERY,
                description="Стандарт (1 — РФ, 2 — EN). Можно передавать несколько значений через запятую.",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "size": openapi.Schema(type=openapi.TYPE_NUMBER, description="Размер трубы (мм)"),
                        "standard": openapi.Schema(type=openapi.TYPE_INTEGER, description="Стандарт"),
                        "dn": openapi.Schema(type=openapi.TYPE_INTEGER, description="Номинальный диаметр DN")
                    }
                )
            ),
            400: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "error": openapi.Schema(type=openapi.TYPE_STRING, description="Описание ошибки")
                }
            ),
            404: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "error": openapi.Schema(type=openapi.TYPE_STRING, description="DN не найден")
                }
            ),
        }
    )
    @action(detail=False, methods=['get'], url_path='get-dn-by-diameter')
    def get_dn_by_diameter(self, request):
        """
        Получает DN по списку внешних диаметров и стандартов.
        Можно передавать несколько значений `size` и `standard`, разделяя их запятой.
        """
        size_values = request.query_params.get('size')
        standard_values = request.query_params.get('standard')

        if not standard_values:
            return Response({"error": "Параметр 'standard' обязателен."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            standard_list = [int(s) for s in standard_values.split(',')]
        except ValueError:
            return Response(
                {"error": "Некорректное значение standard. Оно должно содержать числа, разделенные запятой."},
                status=status.HTTP_400_BAD_REQUEST)

        if size_values:
            try:
                size_list = [float(s) for s in size_values.split(',') if float(s) > 0]
            except ValueError:
                return Response({"error": "Некорректное значение size. Оно должно содержать положительные числа, разделенные запятой."},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            size_list = []

        filters = {"standard__in": standard_list}
        if size_list:
            filters["size__in"] = size_list

        pipe_diameters = PipeDiameter.objects.filter(**filters).select_related('dn')

        if pipe_diameters.exists():
            results = [
                {
                    "size": pd.size,
                    "standard": pd.standard,
                    "dn": pd.dn.dn
                } for pd in pipe_diameters
            ]
            return Response(results, status=status.HTTP_200_OK)
        else:
            return Response({"error": "DN не найден"}, status=status.HTTP_404_NOT_FOUND)


class LoadGroupViewSet(CustomModelViewSet):
    """
    API для работы со справочником "Нагрузочные группы"
    list: Получить список элементов
    retrieve: Получить элемент
    create: Создать новый элемент
    partial_update: Изменить элемент
    destroy: Удалить элемент
    """
    queryset = LoadGroup.objects.all()
    serializer_class = LoadGroupSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter, SearchFilter]
    filterset_class = LoadGroupFilter

    ordering = ['id', 'lgv', 'kn']
    search_fields = ['lgv', 'kn']


class MaterialViewSet(CustomModelViewSet):
    """
    API для работы со справочником "Материалы"
    list: Получить список элементов
    retrieve: Получить элемент
    create: Создать новый элемент
    partial_update: Изменить элемент
    destroy: Удалить элемент
    """
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter, SearchFilter]
    filterset_class = MaterialFilter

    ordering = ('id', 'group', 'name')
    search_fields = ('group', 'name',)


class CoveringTypeViewSet(CustomModelViewSet):
    """
    API для работы со справочником "Типы покрытий"
    list: Получить список элементов
    retrieve: Получить элемент
    create: Создать новый элемент
    partial_update: Изменить элемент
    destroy: Удалить элемент
    """
    queryset = CoveringType.objects.all()
    serializer_class = CoveringTypeSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter, SearchFilter]
    filterset_class = CoveringTypeFilter

    ordering = ('id', 'numeric', 'name')
    search_fields = ('name',)


class CoveringViewSet(CustomModelViewSet):
    """
    API для работы со справочником "Покрытий"
    list: Получить список элементов
    retrieve: Получить элемент
    create: Создать новый элемент
    partial_update: Изменить элемент
    destroy: Удалить элемент
    """
    queryset = Covering.objects.all()
    serializer_class = CoveringSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter, SearchFilter]
    filterset_class = CoveringFilter

    ordering = ('id', 'name')
    search_fields = ('name',)


class SupportDistanceViewSet(ModelViewSet):
    """
    API для работы со справочником "Расстояние между опорами".
    list: Получить список расстояний.
    retrieve: Получить расстояние по ID.
    create: Создать новое расстояние.
    update: Полное обновление расстояния.
    partial_update: Частичное обновление расстояния.
    destroy: Удалить расстояние.
    """
    queryset = SupportDistance.objects.all()
    serializer_class = SupportDistanceSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = SupportDistanceFilter

    ordering = ['value']
    search_fields = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        value = self.request.query_params.get("value")

        if value:
            try:
                value = float(value)
            except ValueError:
                raise ValidationError({"value": "Value must be a valid number."})

        return queryset


class ProductClassViewSet(ModelViewSet):
    queryset = ProductClass.objects.all()
    serializer_class = ProductClassSerializer


class ProductFamilyViewSet(ModelViewSet):
    """
    API для работы со справочником "Семейства изделий".
    """
    queryset = ProductFamily.objects.all()
    serializer_class = ProductFamilySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = ProductFamilyFilter

    ordering = ['name']
    search_fields = ['name']


class LoadViewSet(ModelViewSet):
    queryset = Load.objects.all()
    serializer_class = LoadSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]


class SpringStiffnessViewSet(ModelViewSet):
    queryset = SpringStiffness.objects.all()
    serializer_class = SpringStiffnessSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]


class PipeMountingGroupViewSet(ModelViewSet):
    queryset = PipeMountingGroup.objects.all()
    serializer_class = PipeMountingGroupSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter, SearchFilter]
    filterset_class = PipeMountingGroupFilter

    ordering = ['id', 'name']
    search_fields = ['name']


class PipeMountingRuleViewSet(ModelViewSet):
    queryset = PipeMountingRule.objects.all()
    serializer_class = PipeMountingRuleSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter, SearchFilter]
    filterset_class = PipeMountingRuleFilter

    ordering = ['id', 'family', 'num_spring_blocks', 'pipe_direction']
    search_fields = ['variants__detail_type__designation', 'variants__detail_type__name']


class ComponentGroupViewSet(ModelViewSet):
    queryset = ComponentGroup.objects.all()
    serializer_class = ComponentGroupSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter]
    filterset_class = ComponentGroupFilter

    ordering = ['id', 'group_type']


class SpringBlockFamilyBindingViewSet(ModelViewSet):
    """
    Управление связями между семействами изделий и допустимыми типами пружинных блоков.

    ### Методы:
    - `list`: Получить список связей.
    - `retrieve`: Получить связь по ID.
    - `create`: Создать новую связь.
    - `update`: Полное обновление связи.
    - `partial_update`: Частичное обновление связи.
    - `destroy`: Удалить связь.
    """
    queryset = SpringBlockFamilyBinding.objects.all()
    serializer_class = SpringBlockFamilyBindingSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter]
    filterset_class = SpringBlockFamilyBindingFilter

    ordering = ['id', 'family']


class ActionHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    /api/action_history/
    """
    queryset = LogEntry.objects.all().order_by('-timestamp')
    serializer_class = LogEntrySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LogEntryFilter


class UserActionHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    /api/users/{user_id}/action_history/
    Лог всех изменений, совершённых конкретным пользователем.
    """
    serializer_class = LogEntrySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = LogEntryFilter

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        return LogEntry.objects.select_related('actor', 'content_type') \
            .filter(actor_id=user_id)


class SSBCatalogViewSet(ModelViewSet):
    queryset = SSBCatalog.objects.all()
    serializer_class = SSBCatalogSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter]
    filterset_class = SSBCatalogFilter
    ordering = ['id']


class SSGCatalogViewSet(ModelViewSet):
    queryset = SSGCatalog.objects.all()
    serializer_class = SSGCatalogSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter]
    filterset_class = SSGCatalogFilter
    ordering = ['id']


class ClampMaterialCoefficientViewSet(ModelViewSet):
    """
    API для просмотра и фильтрации коэффициентов материалов хомутов по группе материала и температурному диапазону.

    - Любой пользователь может просматривать данные.
    - Дополнительные действия доступны согласно разрешениям.
    - Поддерживается фильтрация и сортировка по полям: id, material_group, temperature_from, temperature_to, coefficient.
    """
    queryset = ClampMaterialCoefficient.objects.all()
    serializer_class = ClampMaterialCoefficientSerializer
    permission_classes = [AnyOneCanViewPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter]
    filterset_class = ClampMaterialCoefficientFilter

    ordering = ["id", "material_group", "temperature_from", "temperature_to", "coefficient"]
