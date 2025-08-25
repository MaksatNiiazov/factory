import copy
import logging
from io import BytesIO

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, FileResponse
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound
from rest_framework.filters import SearchFilter
from rest_framework.generics import CreateAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from catalog.choices import ComponentGroupType
from catalog.models import PipeMountingRule, ComponentGroup
from kernel.api.decorators import choices_action
from kernel.api.exceptions import UserWithCRMLoginNotFound, DependentError
from kernel.api.filter_backends import MappedOrderingFilter
from kernel.api.permissions import ActionPermission, AnyOneCanViewChoicesPermission
from kernel.api.views import CustomModelViewSet
from kernel.consumers import send_event_to_all
from kernel.models import Organization
from ops.api.exceptions import ItemNotFound, ResourceNotFound, FormatNotSupported, ProjectNotFound
from ops.api.filters import ProjectFilter, DetailTypeFilter, ItemFilter, VariantFilter, BaseCompositionFilter, \
    AttributeFilter
from ops.api.permissions import (
    OwnActionPermission, ProjectItemPermission, ERPSyncPermission, ImportFromCRMPermission,
    ProjectERPSyncPermission, ClonePermission,
)
from ops.api.serializers import (
    CalculateLoadSerializer, ProjectSerializer, DetailTypeSerializer, ItemSerializer, ProjectItemSerializer,
    ItemChildSerializer, FieldSetSerializer, AttributeSerializer, VariantSerializer, MarkingTemplateSerializer,
    CRMProjectSerializer, ItemExportSerializer, ItemImportSerializer, CRMProjectSyncERPSerializer,
    BaseCompositionSerializer, SelectionParamsSerializer, VariantWithDetailTypeSerializer, ShockCalcSerializer,
    ShockCalcResultSerializer, AvailableTopMountsRequestSerializer, TopMountVariantSerializer, AssemblyLengthSerializer,
    AvailableMountsRequestSerializer, MountingVariantSerializer, ShockSelectionParamsSerializer,
    SpacerSelectionParamsSerializer, GetSketchSerializer,

)
from ops.api.utils import get_extended_range, sum_mounting_sizes
from ops.choices import ERPSyncType, AttributeUsageChoices, AttributeType
from ops.loads.utils import get_suitable_loads
from ops.marking_compiler import get_jinja2_env
from ops.sketch.pdf import render_sketch_pdf
from ops.models import (
    Project, DetailType, Item, ProjectItem, ProjectItemRevision, ItemChild, FieldSet, Attribute,
    Variant, ERPSync, BaseComposition
)
from ops.resources import get_resources_list
from ops.services.clone_utils import get_model_fields_for_clone, generate_unique_copy_name, clone_image_field
from ops.services.product_selection import ProductSelectionAvailableOptions
from ops.services.shock_calc_service import calculate_shock_block
from ops.services.shock_selection import ShockSelectionAvailableOptions
from ops.tasks import task_sync_erp, task_sync_project_to_erp, process_import_task
from ops.utils import render_sketch
from taskmanager.api.serializers import TaskSerializer
from taskmanager.choices import TaskType
from taskmanager.models import Task, TaskAttachment
from ops.services.spacer_selection import SpacerSelectionAvailableOptions
User = get_user_model()

logger = logging.getLogger(__file__)


class ProjectViewSet(CustomModelViewSet):
    """
    API для работы с проектами.
    list: Получить список проектов
    retrieve: Получить проект по его идентификатору `id`
    create: Создать новый проект
    partial_update: Изменить проект по его идентификатору `id`
    destroy: Удалить проект по его идентификатору `id`
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [ImportFromCRMPermission | ProjectERPSyncPermission | OwnActionPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter, SearchFilter]
    filterset_class = ProjectFilter
    ordering_fields = (
        'id', 'number', 'organization', 'owner', 'status', 'load_unit', 'move_unit', 'temperature_unit', 'created',
        'modified',
    )
    search_fields = (
        'id', 'number', 'organization__name', 'owner__email', 'owner__last_name', 'owner__first_name',
        'owner__middle_name',
    )

    def get_serializer_class(self):
        if self.action == 'sync_to_erp':
            return CRMProjectSyncERPSerializer
        if self.action == 'import_from_crm':
            return CRMProjectSerializer

        return ProjectSerializer

    def create(self, request, *args, **kwargs):
        data = copy.copy(request.data)
        serializer = ProjectSerializer(data=data)

        if 'owner' not in serializer.initial_data:
            serializer.initial_data['owner'] = request.user.id

        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not self.request.user.has_perm('ops.add_project'):
            if data['owner'] != self.request.user:
                raise PermissionDenied

        serializer.save()
        data = serializer.data

        return Response(data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()

        serializer = ProjectSerializer(data=request.data, instance=instance, partial=True)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        owner = data.get('owner', request.user)

        if owner != request.user:
            raise PermissionDenied

        serializer.save()
        data = serializer.data

        return Response(data)

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.user.has_perm("ops.view_project"):
            return queryset
        elif self.request.user.has_perm("ops.view_own_project"):
            return queryset.filter(owner=self.request.user)

        return Project.objects.none()

    @action(methods=['POST'], detail=False)
    def sync_to_erp(self, request, *args, **kwargs):
        """
        Начать запуск выгрузки в ERP номенклатуру.
        """
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data)

        serializer.is_valid(raise_exception=True)

        data = serializer.data

        try:
            project = Project.objects.get(number=data['number'])
        except Project.DoesNotExist:
            raise ProjectNotFound

        erp_sync = ERPSync.objects.create(author=request.user, type=ERPSyncType.PROJECT, project=project)
        send_event_to_all('sync_erp', erp_sync.to_json())

        task_sync_project_to_erp.delay(erp_sync.id)

        return Response(erp_sync.to_json())

    @action(methods=['POST'], detail=False)
    def import_from_crm(self, request, *args, **kwargs):
        """
        Импорт проекта из CRM.

        Этот метод будет вызван CRM для передачи JSON-данных, которые будут использоваться
        для создания нового проекта или редактирования существующего проекта и его табличной части.
        """
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data)

        serializer.is_valid(raise_exception=True)

        data = serializer.data

        user = User.objects.filter(crm_login=data['crm_login']).first()

        if not user:
            raise UserWithCRMLoginNotFound

        contragent = data['contragent']

        organization = Organization.objects.filter(name=contragent).first()

        if not organization:
            organization = Organization.objects.create(name=contragent)

        project = Project.objects.filter(number=data['number']).first()

        if not project:
            project = Project(number=data['number'])

        project.organization = organization
        project.owner = user
        project.save()

        work_type_mapping = {
            'Пр-во': ProjectItem.MANUFACTURING,
            'Дораб': ProjectItem.REFINEMENT,
            'Перепр': ProjectItem.RESELLING,
        }

        existing_item_ids = []

        for item in data['project_items']:
            try:
                project_item = ProjectItem.objects.get(
                    crm_id=item['id']
                )
            except ProjectItem.DoesNotExist:
                project_item = ProjectItem(
                    crm_id=item['id']
                )

            project_item.project = project
            project_item.position_number = item['number']
            project_item.count = item['quantity']
            project_item.work_type = work_type_mapping[item['working_type']]
            project_item.customer_marking = item['mark_cont']
            project_item.crm_mark_cont = item['mark_cont']

            # TODO: Фейковые данные
            # Чтобы создавался
            project_item.pipe_location = ProjectItem.HORIZONTAL
            project_item.pipe_direction = ProjectItem.X
            project_item.ambient_temperature = 0

            project_item.save()
            existing_item_ids.append(project_item.id)

        # Удаленные позиции из CRM должны будут удалиться
        non_existing_items = ProjectItem.objects.filter(project=project).exclude(id__in=existing_item_ids)
        non_existing_items.delete()

        project_serializer = ProjectSerializer(project)

        return Response(project_serializer.data)


class ProjectItemViewSet(CustomModelViewSet):
    """
    API для работы с табличной частью проекта
    list: Получить список элементов табличной части
    retrieve: Получить элемент табличной части
    create: Создать новый элемент табличной части
    partial_update: Изменить элемент табличной части
    destroy: Удалить элемент табличной части
    """
    permission_classes = [ProjectItemPermission]

    def get_serializer_class(self):
        if self.action in ["set_selection", "calculate", "update_item"]:
            return Serializer
        if self.action in ["get_sketch", "get_subsketch"]:
            return GetSketchSerializer

        return ProjectItemSerializer

    def get_queryset(self):
        qs = ProjectItem.objects.all()

        if "project_pk" in self.kwargs:
            project_pk = self.kwargs["project_pk"]
            qs = qs.filter(project_id=project_pk)

        return qs

    def perform_create(self, serializer):
        serializer.save(project_id=self.kwargs["project_pk"])

    @action(methods=['GET'], detail=True)
    def selection_params(self, request, project_pk, pk):
        project_item = ProjectItem.objects.get(project_id=project_pk, pk=pk)

        selection_type = request.query_params.get('selection_type', 'product_selection')

        if selection_type not in ['product_selection', 'shock_selection', 'ssg_selection']:
            return Response({
                'detail': f'Некорректный selection_type: {selection_type}'
            }, status=400)

        if project_item.selection_params:
            return Response(project_item.selection_params)

        if selection_type == 'product_selection':
            params = ProductSelectionAvailableOptions.get_default_params()
        elif selection_type == 'ssg_selection':
            params = SpacerSelectionAvailableOptions.get_default_params()
        else:
            params = ShockSelectionAvailableOptions.get_default_params()

        return Response(params)

    @action(methods=['POST'], detail=True)
    def set_selection(self, request, project_pk, pk) -> Response:
        data = request.data

        project_item = ProjectItem.objects.get(project_id=project_pk, pk=pk)

        selection_type = request.query_params.get('selection_type', 'product_selection')

        if selection_type not in ['product_selection', 'shock_selection', 'ssg_selection']:
            return Response({
                'detail': f'Некорретный selection_type: {selection_type}'
            }, status=400)

        if selection_type == 'product_selection':
            selection_params_serializer = SelectionParamsSerializer(data=data)
            selection_params_serializer.is_valid(raise_exception=True)
        elif selection_type == 'ssg_selection':
            selection_params_serializer = SpacerSelectionParamsSerializer(data=data)
            selection_params_serializer.is_valid(raise_exception=True)
        else:
            selection_params_serializer = ShockSelectionParamsSerializer(data=data)
            selection_params_serializer.is_valid(raise_exception=True)

        project_item.selection_params = selection_params_serializer.data
        project_item.save()

        serializer = ProjectItemSerializer(project_item)
        data = serializer.data

        return Response(data)

    @action(methods=['POST'], detail=True)
    def get_selection_options(self, request, project_pk, pk):
        selection_type = request.query_params.get('selection_type', 'product_selection')

        if selection_type not in ['product_selection', 'shock_selection', 'ssg_selection']:
            return Response({
                'detail': f'Некорретный selection_type: {selection_type}'
            }, status=400)

        project_item = ProjectItem.objects.get(project_id=project_pk, pk=pk)

        if selection_type == 'product_selection':
            available_options = ProductSelectionAvailableOptions(project_item).get_available_options()
        elif selection_type == 'ssg_selection':
            available_options = SpacerSelectionAvailableOptions(project_item).get_available_options()
        else:
            available_options = ShockSelectionAvailableOptions(project_item).get_available_options()

        return Response(available_options)

    @action(methods=['POST'], detail=True)
    def update_item(self, request: Request, project_pk: int, pk: int) -> Response:
        """
        Создает или обновляет Item (изделие) для табличной части проекта.
        """
        selection_type = request.query_params.get('selection_type', 'product_selection')

        if selection_type not in ['product_selection', 'shock_selection']:
            return Response({
                'detail': f'Некорретный selection_type: {selection_type}'
            }, status=400)
        
        project_item = ProjectItem.objects.get(project_id=project_pk, pk=pk)

        if selection_type == 'product_selection':
            selection = ProductSelectionAvailableOptions(project_item)
        else:
            selection = ShockSelectionAvailableOptions(project_item)
        
        available_options = selection.get_available_options()
        specifications = available_options.get('specification', [])
        parameters, locked_parameters = selection.get_parameters(available_options)

        if project_item.original_item:
            item = selection.update_item(request.user, project_item.original_item, parameters, locked_parameters, specifications)
        else:
            item = selection.create_item(request.user, parameters, locked_parameters, specifications)
        
        project_item.original_item = item
        project_item.save()

        serializer = ProjectItemSerializer(project_item)

        return Response(serializer.data)

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Файл с эксизом (SVG или PDF)",
                schema=openapi.Schema(type=openapi.TYPE_FILE)
            )
        },
    )
    @action(methods=['POST'], detail=True)
    def get_sketch(self, request: Request, project_pk: int, pk: int) -> FileResponse:
        """
        Генерирует SVG или PDF-эскиз для элемента проекта и возвращает его как файл.
        """
        project_item = ProjectItem.objects.get(pk=pk, deleted_at__isnull=True)

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        export_format = serializer.validated_data.get('format', 'svg').lower()

        if export_format == "svg":
            content_type = "image/svg+xml"
            try:
                output, filename = render_sketch(request, project_item, composition_type="specification")
            except Exception as exc:
                raise ValidationError(str(exc))
        elif export_format == "pdf":
            content_type = "application/pdf"
            try:
                output, filename = render_sketch_pdf(project_item, request.user)
            except Exception as exc:
                raise ValidationError(str(exc))
        else:
            raise FormatNotSupported(f"Формат {export_format} не поддерживается. Доступные форматы: svg, pdf.")

        buffer = BytesIO(output)
        response = FileResponse(buffer, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    @action(methods=['POST'], detail=True)
    def get_subsketch(self, request: Request, project_pk: int, pk: int) -> FileResponse:
        """
        Генерирует дополнительный SVG или PDF эскиз для элемента проекта и возвращает его как файл.
        """
        project_item = ProjectItem.objects.get(pk=pk)

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        export_format = serializer.validated_data.get("format", "svg").lower()

        if export_format == "svg":
            content_type = "image/svg+xml"
            try:
                output, filename = render_sketch(
                    request, project_item, composition_type="specification",
                    field_name="subsketch",
                    coords_field_name="subsketch_coords",
                )
            except Exception as exc:
                raise ValidationError(str(exc))
        elif export_format == "pdf":
            content_type = "application/pdf"
            try:
                output, filename = render_sketch_pdf(
                    project_item, request.user, field_name="subsketch",
                    coords_field_name="subsketch_coords",
                )
            except Exception as exc:
                raise ValidationError(str(exc))
        else:
            raise FormatNotSupported(f"Формат {export_format} не поддерживается. Доступные форматы: svg, pdf.")

        buffer = BytesIO(output)
        response = FileResponse(buffer, content_type=content_type)
        response["Content-Disposition"] = f"attachment; filename=\"{filename}\""
        return response

    @action(methods=['POST'], detail=True)
    @transaction.atomic
    def save_as(self, request, project_pk, pk):
        project_item = ProjectItem.objects.get(id=pk, project_id=project_pk)

        # При "Сохранить как", нужно клонировать не только сам объект, но и так же спецификацию
        original_item_id = project_item.original_item.id

        # Клонируем сам Item
        item = project_item.original_item
        item.id = None
        item.inner_id = None
        item._state.adding = True  # Нужно, чтобы в методе save(), присваивался новый inner_id
        item.save()

        # Клонируем спецификацию ItemChild
        children = ItemChild.objects.filter(parent_id=original_item_id)

        for child in children:
            child.id = None
            child.parent = item

        ItemChild.objects.bulk_create(children)

        ProjectItemRevision.objects.create(
            project_item=project_item,
            revision_item=item,
        )

        return Response(ProjectItemSerializer(project_item).data)


class DetailTypeViewSet(CustomModelViewSet):
    """
    API для работы с типами деталей/изделии.
    list: Получить список типов
    retrieve: Получить тип по его идентификатору `id`
    create: Создать новый тип
    partial_update: Изменить тип по его идентификатору `id`
    destroy: Удалить тип по его идентификатору `id`
    """
    queryset = DetailType.objects.all()
    serializer_class = DetailTypeSerializer
    permission_classes = [AnyOneCanViewChoicesPermission | ClonePermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter, SearchFilter]
    filterset_class = DetailTypeFilter

    ordering_fields = ('id', 'product_family', 'name', 'designation')
    search_fields = ('id', 'name', 'designation')

    def get_serializer_class(self):
        if self.action == 'clone':
            return Serializer

        return DetailTypeSerializer

    @action(['POST'], detail=True)
    @transaction.atomic
    def clone(self, request: Request, pk: int) -> Response:
        """
        Клонирует объект DetailType вместе с его связанными сущностями
        (исполнениями, атрибутами и комплектующими базового состава).
        """
        try:
            detail_type = DetailType.objects.get(id=pk)
        except DetailType.DoesNotExist:
            raise NotFound

        # Клонирование DetailType
        cloned_detail_type = copy.deepcopy(detail_type)
        cloned_detail_type.id = None

        cloned_detail_type.designation = detail_type.designation + '_Cloned'

        if detail_type.name:
            cloned_detail_type.name = detail_type.name + ' (Клонированнный)'

        counter = 2
        while DetailType.objects.filter(designation=cloned_detail_type.designation).exists():
            cloned_detail_type.designation = detail_type.designation + f'_Cloned_{counter}'

            if detail_type.name:
                cloned_detail_type.name = detail_type.name + f' (Клонированный {counter})'

            counter += 1

        cloned_detail_type.save()

        # Клонирование Attribute
        attributes = Attribute.objects.filter(detail_type=detail_type)

        cloned_attributes = []
        for attribute in attributes:
            cloned_attribute = copy.deepcopy(attribute)
            cloned_attribute.id = None
            cloned_attribute.detail_type = cloned_detail_type
            cloned_attributes.append(cloned_attribute)

        Attribute.objects.bulk_create(cloned_attributes)

        # Клонирование BaseComposition
        base_compositions = BaseComposition.objects.filter(base_parent=detail_type, base_parent_variant__isnull=True)

        cloned_base_compositions = []
        for base_composition in base_compositions:
            cloned_base_composition = copy.deepcopy(base_composition)
            cloned_base_composition.id = None
            cloned_base_composition.base_parent = cloned_detail_type
            cloned_base_compositions.append(cloned_base_composition)

        BaseComposition.objects.bulk_create(cloned_base_compositions)

        # Клонирование Variant
        for variant in detail_type.variants.all():
            cloned_variant = copy.deepcopy(variant)
            cloned_variant.id = None
            cloned_variant.detail_type = cloned_detail_type

            cloned_variant.save()

            # Клонирование Attribute у Variant
            attributes = Attribute.objects.filter(variant=variant)
            cloned_attributes = []

            for attribute in attributes:
                cloned_attribute = copy.deepcopy(attribute)
                cloned_attribute.id = None
                cloned_attribute.variant = cloned_variant
                cloned_attributes.append(cloned_attribute)

            Attribute.objects.bulk_create(cloned_attributes)

            basecomp_fields = get_model_fields_for_clone(BaseComposition, exclude=['historylog', 'base_parent'])
            base_compositions = BaseComposition.objects.filter(base_parent_variant=variant)

            cloned_compositions = []
            for bc in base_compositions:
                data = {f: getattr(bc, f) for f in basecomp_fields}
                data['base_parent_variant'] = cloned_variant
                data['base_parent'] = cloned_detail_type
                cloned_compositions.append(BaseComposition(**data))

            print(cloned_compositions)

            BaseComposition.objects.bulk_create(cloned_compositions)
        serializer = DetailTypeSerializer(instance=cloned_detail_type)
        data = serializer.data

        return Response(data)

    @action(detail=True, methods=['get'], url_path='available_attributes')
    def available_attributes(self, request, pk):
        """
        Старый
        API для получения списка доступных атрибутов для указанного варианта.
        """
        try:
            detail_type = DetailType.objects.get(pk=pk)
        except DetailType.DoesNotExist:
            return Response({"error": "Тип детали не найден"}, status=404)

        attributes = detail_type.get_available_attributes()

        return Response(attributes)

    @action(detail=True, methods=['get'], url_path='get_available_attributes')
    def get_available_attributes(self, request, pk):
        """
        Старый
        API для получения списка доступных атрибутов:
        - Без параметра ?variant_id — только базовые атрибуты и состав без варианта.
        - С параметром ?variant_id — добавляются атрибуты исполнения и атрибуты дочерних исполнений в составе.
        """
        try:
            detail_type = DetailType.objects.get(pk=pk)
        except DetailType.DoesNotExist:
            return Response({"error": "Тип детали не найден"}, status=404)

        variant_id = request.query_params.get("variant_id")
        variant = None

        if variant_id:
            try:
                variant = Variant.objects.get(pk=variant_id, detail_type=detail_type)
            except Variant.DoesNotExist:
                return Response({"error": "Исполнение не найдено или не относится к этому типу"}, status=404)

        attributes = detail_type.new_get_available_attributes(variant=variant)
        return Response(attributes)

    @action(detail=True, methods=['get'], url_path='available_attributes_v2')
    def available_attributes_v2(self, request, pk=None):
        """
        Актуальный API. Поддерживает параметры: - variant_id: ID исполнения, - exclude_composition=true|false
        Новый API для получения атрибутов с возможностью исключения атрибутов из базового состава.

        """
        try:
            detail_type = self.get_object()
        except DetailType.DoesNotExist:
            return Response({"error": "Тип детали не найден"}, status=status.HTTP_404_NOT_FOUND)

        # Получаем параметры
        variant_id = request.query_params.get("variant_id")
        exclude_composition_param = request.query_params.get("exclude_composition", "false").lower()
        exclude_composition = exclude_composition_param in ["true", "1", "yes"]

        variant = None
        if variant_id:
            try:
                variant = detail_type.variants.get(id=variant_id)
            except detail_type.variants.model.DoesNotExist:
                return Response({"error": "Вариант не найден"}, status=status.HTTP_404_NOT_FOUND)

        # Получаем атрибуты с учетом логики
        attributes = detail_type.get_available_attributes_v2(
            variant=variant,
            exclude_composition=exclude_composition
        )

        return Response(attributes)

    @choices_action()
    def category(self, request):
        return Response([{
            'value': choice[0],
            'verbose_name': choice[1],
        } for choice in DetailType.CATEGORIES])

    @choices_action()
    def branch_qty(self, request):
        return Response([{
            'value': choice[0],
            'verbose_name': choice[1]
        } for choice in DetailType.BranchQty.choices])

    @choices_action()
    def designation(self, request):
        """
        Возвращает список уникальных обозначений (designation) с учетом категории, если она указана.
        Пример: /detail_types/choices/designation/?category=assembly_unit
        """
        category = request.query_params.get('category')

        queryset = DetailType.objects.all()
        if category:
            queryset = queryset.filter(category=category)

        designations = queryset.values_list('designation', flat=True).distinct()

        return Response([{
            'value': designation,
            'verbose_name': designation,
        } for designation in designations])


class BaseCompositionViewSet(CustomModelViewSet):
    """
    API для работы с комплектующими базового состава.
    list: Получение списка элементов базового состава.
    retrieve: Получение элемента базового состава по его идентификатору.
    create: Добавление элемента в базовый состав.
    partial_update: Частичное обновление элемента базового состава.
    destroy: Удаление элемента из базового состава.
    """
    queryset = BaseComposition.objects.all()
    serializer_class = BaseCompositionSerializer
    permission_classes = [ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter]
    filterset_class = BaseCompositionFilter
    ordering_fields = [
        'id', 'base_parent_detail_type', 'base_parent', 'base_child_detail_type', 'base_child', 'position', 'count',
    ]


class FieldSetViewSet(ReadOnlyModelViewSet):
    """
    API для работы с группами атрибутов
    list: Получить список групп
    retrieve: Получить группу
    """
    queryset = FieldSet.objects.all()
    serializer_class = FieldSetSerializer
    permission_classes = [IsAuthenticated]


class VariantViewSet(CustomModelViewSet):
    """
    API для работы с исполнениями
    list: Получить список исполнений
    retrieve: Получить исполнение
    create: Создать исполнение
    partial_update: Изменить исполнение по его идентификатору `id`
    """
    permission_classes = [ActionPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_class = VariantFilter

    def get_serializer_class(self):
        if 'detail_type_pk' in self.kwargs:
            return VariantSerializer
        else:
            return VariantWithDetailTypeSerializer

    def get_queryset(self):
        qs = Variant.objects.all()

        show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'

        if not show_deleted:
            qs = qs.filter(deleted_at__isnull=True)

        if 'detail_type_pk' in self.kwargs:
            detail_type_pk = self.kwargs['detail_type_pk']
            qs = qs.filter(detail_type_id=detail_type_pk)

        return qs

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(['POST'], detail=True)
    def check_delete(self, request, detail_type_pk, pk):
        """
        Проверяет можно ли удалить объект безопасно.
        """
        try:
            variant = Variant.objects.get(pk=pk)
        except Variant.DoesNotExist:
            raise NotFound

        items = Item.objects.filter(variant=variant)

        if items.exists():
            raise DependentError(
                detail=_(f'Существует {items.count()} деталей/изделии которые зависит от этого исполнения.'),
            )

        return Response()

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def clone(self, request, pk=None):
        """
        Клонирует исполнение с его атрибутами и базовым составом.
        """
        try:
            original = Variant.objects.get(pk=pk)
        except Variant.DoesNotExist:
            raise NotFound(_('Оригинальное исполнение не найдено'))

        # === Копирование Variant ===
        variant_fields = get_model_fields_for_clone(Variant, exclude=['deleted_at', 'created', 'modified'])
        variant_data = {f: getattr(original, f) for f in variant_fields}

        existing_names = set(
            Variant.objects.filter(detail_type_id=original.detail_type_id)
            .values_list('name', flat=True)
        )
        variant_data['name'] = generate_unique_copy_name(original.name, existing_names, number_separator='-')
        variant_data['detail_type_id'] = original.detail_type_id

        for field in ['sketch', 'subsketch']:
            content = clone_image_field(field, original)
            if content:
                variant_data[field] = content

        cloned_variant = Variant.objects.create(**variant_data)

        # === Копирование Attribute ===
        attribute_fields = get_model_fields_for_clone(Attribute, exclude=['historylog'])
        attributes = Attribute.objects.filter(variant=original)

        cloned_attributes = []
        for attr in attributes:
            data = {f: getattr(attr, f) for f in attribute_fields}
            data['name'] = attr.name
            data['label'] = attr.label
            data['variant'] = cloned_variant
            data['detail_type'] = None
            cloned_attributes.append(Attribute(**data))

        Attribute.objects.bulk_create(cloned_attributes)

        # === Копирование BaseComposition ===
        basecomp_fields = get_model_fields_for_clone(BaseComposition, exclude=['historylog'])
        base_compositions = BaseComposition.objects.filter(base_parent_variant=original)

        cloned_compositions = []
        for bc in base_compositions:
            data = {f: getattr(bc, f) for f in basecomp_fields}
            data['base_parent_variant'] = cloned_variant
            cloned_compositions.append(BaseComposition(**data))

        BaseComposition.objects.bulk_create(cloned_compositions)

        return Response(VariantSerializer(cloned_variant).data, status=status.HTTP_201_CREATED)

    def create(self, request, *args, **kwargs):
        data = copy.copy(request.data)

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=data)

        if 'detail_type_pk' in self.kwargs:
            serializer.initial_data['detail_type'] = self.kwargs['detail_type_pk']

        serializer.is_valid(raise_exception=True)

        instance = Variant(**serializer.validated_data)

        if 'detail_type_pk' in self.kwargs:
            instance.detail_type_id = self.kwargs['detail_type_pk']

        instance.save()

        serializer = serializer_class(instance=instance)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(data=request.data, instance=instance, partial=True)
        serializer.is_valid(raise_exception=True)

        serializer.save()
        data = serializer.data

        return Response(data)

    @action(detail=True, methods=['get'], url_path='available_attributes')
    def available_attributes(self, request, detail_type_pk=None, pk=None):
        """
        Старый
        API для получения списка доступных атрибутов для указанного варианта.
        """
        try:
            detail_type = DetailType.objects.get(pk=detail_type_pk)
            variant = Variant.objects.get(pk=pk, detail_type=detail_type)
        except DetailType.DoesNotExist:
            return Response({"error": "Тип детали не найден"}, status=404)
        except Variant.DoesNotExist:
            return Response({"error": "Вариант не найден"}, status=404)

        attributes = detail_type.get_available_attributes(variant)

        return Response(attributes)


class AttributeViewSet(CustomModelViewSet):
    """
    API для работы с атрибутами
    list: Получить список атрибутов
    retrieve: Получить атрибут
    create: Создать атрибут
    partial_update: Изменить атрибут по его идентификатору `id`
    """
    queryset = Attribute.objects.all()
    serializer_class = AttributeSerializer
    permission_classes = [AnyOneCanViewChoicesPermission | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter]
    filterset_class = AttributeFilter
    ordering_fields = ['id', 'detail_type', 'variant', 'name']

    @choices_action()
    def types(self, request):
        """
        Возвращает список доступных типов атрибутов.
        """
        return Response([{
            'value': choice[0],
            'verbose_name': choice[1],
        } for choice in AttributeType.choices])

    @choices_action()
    def usages(self, request):
        """
        Возвращает список доступных вариантов использования атрибутов.
        """
        return Response([{
            'value': choice[0],
            'verbose_name': choice[1],
        } for choice in AttributeUsageChoices.choices])

    @choices_action()
    def catalogues(self, request):
        """
        Возвращает список доступных каталогов атрибутов.
        """
        return Response([{
            'value': choice[0],
            'verbose_name': choice[1],
        } for choice in Attribute.get_catalog_choices()])

    @choices_action()
    def catalog_apis(self, request):
        """
        Возвращает список доступных API для каталогов атрибутов.
        """
        return Response([{
            'value': choice[0],
            'verbose_name': choice[1],
        } for choice in Attribute.get_catalog_apis()])

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def clone(self, request, pk=None):
        """
        Клонирует атрибут, создавая уникальные name и label.
        """
        try:
            original = Attribute.objects.get(pk=pk)
        except Attribute.DoesNotExist:
            raise NotFound(_('Оригинальный атрибут не найден'))

        # === Копирование полей атрибута ===
        attribute_fields = get_model_fields_for_clone(Attribute, exclude=['historylog'])
        attribute_data = {f: getattr(original, f) for f in attribute_fields}

        # === Генерация уникального name и label ===
        base_name = original.name
        existing_names = set(
            Attribute.objects.filter(variant=original.variant, detail_type=original.detail_type)
            .values_list('name', flat=True)
        )
        attribute_data['name'] = generate_unique_copy_name(base_name, existing_names, suffix='_copy', sep='_')

        if original.label:
            base_label = original.label
            existing_labels = set(
                Attribute.objects.filter(variant=original.variant, detail_type=original.detail_type)
                .values_list('label', flat=True)
            )
            attribute_data['label'] = generate_unique_copy_name(base_label, existing_labels)
        else:
            attribute_data['label'] = None

        attribute_data['variant'] = original.variant
        attribute_data['detail_type'] = original.detail_type

        cloned = Attribute.objects.create(**attribute_data)

        return Response(AttributeSerializer(cloned).data, status=status.HTTP_201_CREATED)


class ItemViewSet(CustomModelViewSet):
    """
    API для работы с изделиями/деталями/сборочными единицами.
    list: Получить список изделий/деталей/сборочных единиц
    retrieve: Получить изделие/деталь/сборочную единицу по его идентификатору `id`
    create: Создать новое изделие/деталь/сборочную единицу
    partial_update: Изменить изделие/деталь/сборочную единицу по его идентификатору `id`
    destroy: Удалить изделие/деталь/сборочную единицу по его идентификатору `id`
    """
    queryset = Item.objects.all()
    # permission_classes = [ERPSyncPermission | OwnActionPermission.build(owner_field='author') | ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter, SearchFilter]
    filterset_class = ItemFilter

    ordering_fields = (
        'id', 'type', 'variant', 'inner_id', 'name', 'marking', 'weight', 'material', 'author',
        'created', 'modified',
    )
    search_fields = (
        'id', 'type__name', 'type__designation', 'variant__name', 'inner_id', 'name', 'marking',
        'weight', 'material__name', 'author__email', 'author__last_name', 'author__first_name',
        'author__middle_name',
    )

    def get_serializer_class(self):
        if self.action in ['sync_erp', 'sync_specifications_erp']:
            return Serializer
        if self.action in ['export']:
            return ItemExportSerializer
        if self.action in ['import_data']:
            return ItemImportSerializer

        return ItemSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # TODO: Временное решение, потом найти другую библиотеку или хороший способ встроить в текущую библиотеку
        parameters_filters = None
        for key, value in request.GET.items():
            if key.startswith('parameters.'):
                parts = key.split('.')
                filter_param = '__'.join(parts)
                found = False

                if value in ('true', 'false'):
                    pythonic_value = True if value == 'true' else False
                    key_filter = Q(**{filter_param: str(value)}) | Q(**{filter_param: pythonic_value})
                    found = True

                if not found:
                    try:
                        pythonic_value = int(value)
                        key_filter = Q(**{filter_param: pythonic_value})
                        found = True
                    except ValueError:
                        try:
                            pythonic_value = float(value)
                            key_filter = Q(**{filter_param: pythonic_value})
                            found = True
                        except ValueError:
                            pass

                if not found:
                    key_filter = Q(**{filter_param: str(value)})

                if parameters_filters is None:
                    parameters_filters = key_filter
                else:
                    parameters_filters &= key_filter

        if parameters_filters:
            queryset = queryset.filter(parameters_filters)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        data = copy.copy(request.data)
        serializer = ItemSerializer(data=data)

        if 'author' not in serializer.initial_data:
            serializer.initial_data['author'] = request.user.id

        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not self.request.user.has_perm('ops.add_item'):
            if data['author'] != self.request.user:
                raise PermissionDenied(
                    _('Пользователь не может создавать детали/изделия от имени другого пользователя')
                )

        serializer.save()
        data = serializer.data

        return Response(data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()

        serializer = ItemSerializer(data=request.data, instance=instance, partial=True)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        author = data.get('author', request.user)

        if not self.request.user.has_perm('ops.change_item') and author != request.user:
            raise PermissionDenied(_('Пользователь не может изменить детали/изделия от имени другого пользователя'))

        serializer.save()
        data = serializer.data

        return Response(data)

    @action(methods=['POST'], detail=True)
    def sync_erp(self, request, pk, *args, **kwargs):
        """
        Начать запуск выгрузки в ERP номенклатуру и спецификацию
        """
        try:
            item = Item.objects.get(pk=pk)
        except Item.DoesNotExist:
            raise ItemNotFound

        erp_sync = ERPSync.objects.create(author=request.user, type=ERPSyncType.ITEM, item=item)
        send_event_to_all("sync_erp", erp_sync.to_json())

        task_sync_erp.delay(erp_sync.id)

        return Response(erp_sync.to_json())

    @action(methods=['POST'], detail=False)
    def import_data(self, request: Request, *args, **kwargs) -> Response:
        """
        Асинхронно запускает импорт данных из CSV/XLSX файла.

        Валидация входных данных производится через сериализатор.
        В зависимости от флага 'is_dry_run':
            - Если True, импорт выполняется как dry-run (тип задачи: DryRunImport);
            - Если False,выполняется реальный импорт (тип задачи: Import);

        Файл, переданный в поле 'file', сохраняется в модели TaskAttachment с полем slug равным 'imported_file'.
        Остальные параметры (например, category, designation, type файла, is_dry_run) сохраняются
        в поле parameters модели Task.

        Создаётся Task с начальным статусом 'New', после чего задача отправляется на обработку
        в celery. Во время выполнения celery-задача обновит статус на 'Processing' и по результатам
        импорта - либо на 'Done', либо, в случае ошибки, на 'Error' с сохранением traceback в status_details.
        """

        serializer_class = self.get_serializer_class()

        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        file_format = data['type']
        category = data['category']
        designation = data['designation']
        uploaded_file = data['file']
        is_dry_run = data['is_dry_run']

        if file_format not in ['xlsx', 'csv']:
            raise FormatNotSupported

        resources = get_resources_list()
        resource = next((resource for resource in resources if resource.__name__ == f'{category}_{designation}'), None)

        if not resource:
            raise ResourceNotFound

        parameters = {
            'category': category,
            'designation': designation,
            'file_format': file_format,
        }

        task = Task.objects.create(
            owner=request.user,
            type=TaskType.IMPORT,
            dry_run=is_dry_run,
            parameters=parameters,
        )

        TaskAttachment.objects.create(task=task, slug='imported_file', file=uploaded_file)

        serializer = TaskSerializer(task)
        data = serializer.data

        process_import_task(task.id)

        return Response(data, status=status.HTTP_201_CREATED)

    @action(methods=['POST'], detail=False)
    def export(self, request, *args, **kwargs):
        """
        Экспортировать данные в csv/xlsx
        """

        serializer_class = self.get_serializer_class()

        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.data

        file_type = data['type']
        category = data['category']
        designation = data['designation']
        is_empty = data['is_empty']

        if file_type not in ['xlsx', 'csv']:
            raise FormatNotSupported

        resources = get_resources_list()
        resource = next((resource for resource in resources if resource.__name__ == f'{category}_{designation}'), None)

        if not resource:
            raise ResourceNotFound

        if is_empty:
            dataset = resource().export(queryset=Item.objects.none())
        else:
            dataset = resource().export(
                queryset=Item.objects.filter(type__category=category, type__designation=designation)
            )

        content_types = {
            'csv': 'text/csv',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }

        response = HttpResponse(getattr(dataset, file_type), content_type=content_types[file_type])
        response['Content-Disposition'] = f'attachment; filename="{designation}.{file_type}"'
        return response

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.user.has_perm("ops.view_item"):
            return queryset
        elif self.request.user.has_perm("ops.view_own_item"):
            return queryset.filter(author=self.request.user)

        return Item.objects.none()


class ItemChildViewSet(CustomModelViewSet):
    """
    API для работы со составом детали/изделия
    list: Получить список элементов состава
    retrieve: Получить элемент состава
    create: Добавить элемент состава
    partial_update: Изменить элемент состава
    destroy: Удалить элемент состава
    """
    serializer_class = ItemChildSerializer
    permission_classes = [OwnActionPermission.build('parent__owner') | ActionPermission]

    def get_queryset(self):
        qs = ItemChild.objects.all()

        if 'parent_pk' in self.kwargs:
            parent_pk = self.kwargs['parent_pk']
            qs = qs.filter(parent_id=parent_pk)

        return qs

    def perform_create(self, serializer):
        serializer.save(parent_id=self.kwargs['parent_pk'])


class MarkingTemplateCompileAPIView(CreateAPIView):
    serializer_class = MarkingTemplateSerializer
    permission_classes = (AllowAny,)  # TODO: Это небезопасно, но это пока временно

    def create(self, request, *args, **kwargs):
        serializer_class = self.get_serializer_class()

        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.data

        marking_template = data['marking_template']
        parameters = data['parameters']

        # TODO: Надо изучить, чтобы jinja2-шаблоны были максимально безопасными
        template = get_jinja2_env().from_string(marking_template)
        rendered_template = template.render(**parameters)

        return Response({
            'result': rendered_template,
        })


class CalculateLoadAPIView(CreateAPIView):
    serializer_class = CalculateLoadSerializer
    permission_classes = (IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        """
        Вычислять наиболее оптимальную нагрузку
        """
        serializer_class = self.get_serializer_class()

        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.data

        load_minus = data.get('load_minus')
        movement_plus = data.get('movement_plus')
        movement_minus = data.get('movement_minus')
        minimum_spring_travel = data.get('minimum_spring_travel')
        standard_series = data.get('standard_series')
        l_series = data.get('l_series')

        final_loads = []
        final_best_load = None

        if standard_series:
            from ops.loads.standard_series import MAX_SIZE

            best_load, loads = get_suitable_loads(
                'standard_series', MAX_SIZE, load_minus, movement_plus, movement_minus, minimum_spring_travel,
            )
            final_loads.extend(loads)
            final_best_load = best_load
        if l_series:
            from ops.loads.l_series import MAX_SIZE

            best_load, loads = get_suitable_loads(
                'l_series', MAX_SIZE, load_minus, movement_plus, movement_minus, minimum_spring_travel,
            )
            final_loads.extend(loads)
            final_best_load = best_load

        return Response({
            'loads': final_loads,
            'best_load': final_best_load,
        })


class ShockCalcAPIView(APIView):
    @swagger_auto_schema(
        operation_summary="Расчет SSB гидроамортизатора",
        request_body=ShockCalcSerializer,
        responses={
            200: openapi.Response("Успешный ответ", ShockCalcResultSerializer),
            400: 'Bad Request',
            404: 'Not Found'
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = ShockCalcSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            result = calculate_shock_block(data, request.user)
            return Response(result, status=200)
        except ValidationError as exc:
            return Response({"detail": str(exc.detail)}, status=400)


class AvailableMountsAPIView(APIView):
    @swagger_auto_schema(
        operation_summary="Список допустимых нижних креплений (A) для SSB",
        request_body=AvailableMountsRequestSerializer,
        responses={200: MountingVariantSerializer(many=True), 400: 'Bad Request', 404: 'Not Found'}
    )
    def post(self, request, *args, **kwargs):
        ser = AvailableMountsRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        item = get_object_or_404(Item, id=data['item_id'])

        rule = PipeMountingRule.objects.filter(
            family=item.type.product_family,
            num_spring_blocks=data['branch_qty'],
            pipe_direction=data['pipe_direction']
        ).first()
        if not rule:
            return Response([], status=200)

        variant_ids = rule.pipe_mounting_groups.values_list('variants__id', flat=True)
        variants = Variant.objects.filter(id__in=variant_ids).distinct()

        result = []
        for v in variants:
            attr = v.get_attributes().filter(name=AttributeUsageChoices.INSTALLATION_SIZE).first()
            size = 0.0
            if attr and attr.default is not None:
                try:
                    size = float(attr.default)
                except (TypeError, ValueError):
                    pass
            result.append({"id": v.id, "name": v.name, "mounting_size": size})

        return Response(result, status=200)


class AvailableTopMountsAPIView(APIView):
    @swagger_auto_schema(
        operation_summary="Список допустимых верхних креплений (B) для SSB",
        request_body=AvailableTopMountsRequestSerializer,
        responses={200: TopMountVariantSerializer(many=True), 400: 'Bad Request', 404: 'Not Found'}
    )
    def post(self, request, *args, **kwargs):
        ser = AvailableTopMountsRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        item = get_object_or_404(Item, id=data['item_id'])
        # если выбор верхнего крепления не разрешён
        if not item.type.product_family.is_upper_mount_selectable:
            return Response([], status=200)

        # ищем группу "SERIES_SELECTABLE" для этого detail_type
        group = ComponentGroup.objects.filter(
            group_type=ComponentGroupType.SERIES_SELECTABLE,
            detail_types=item.type
        ).first()
        if not group:
            return Response([], status=200)

        # все варианты variant под этой группой
        variant_ids = group.detail_types.values_list('variants__id', flat=True)
        variants = Variant.objects.filter(id__in=variant_ids).distinct()

        result = []
        for v in variants:
            attr = v.get_attributes().filter(name=AttributeUsageChoices.INSTALLATION_SIZE).first()
            size = 0.0
            if attr and attr.default is not None:
                try:
                    size = float(attr.default)
                except (TypeError, ValueError):
                    pass
            result.append({"id": v.id, "name": v.name, "mounting_size": size})

        return Response(result, status=200)


class AssemblyLengthAPIView(APIView):
    @swagger_auto_schema(
        operation_summary="Расчет полной длины системы SSB + крепления",
        request_body=AssemblyLengthSerializer,
        responses={
            200: openapi.Response("Успешный ответ"),
            400: 'Bad Request',
            404: 'Not Found'
        }
    )
    def post(self, request, *args, **kwargs):
        # 1. Валидация входных данных
        serializer = AssemblyLengthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # 2. Расчёт блока через сервис
        try:
            shock_data = calculate_shock_block({
                "item_id": data["item_id"],
                "load_type": data["load_type"],
                "load_value": data["load_value"],
                "sn": data["sn"],
                "branch_qty": data["branch_qty"],
                "pipe_direction": data["pipe_direction"],
                "use_extra_margin": data["use_extra_margin"],
                "mounting_length_full": None,  # в этом API не используется
                "mounting_variants": data["mounting_variants"]
            }, request.user)
        except ValidationError as exc:
            return Response({"detail": str(exc.detail)}, status=400)

        # 3. Получение Item
        item = get_object_or_404(Item, id=data["item_id"])

        # 4. Сумма монтажных размеров (нижнее и верхнее крепления)
        sum_A = sum_mounting_sizes(item, data["mounting_variants"])
        sum_B = sum_mounting_sizes(item, data["top_mount_variants"])

        # 5. Расчёт итоговой длины системы
        center = shock_data["L2_req"]
        system_length = center + sum_A + sum_B

        # 6. Ответ
        return Response({
            "block_code": shock_data["result"],
            "system_length": round(system_length, 3),
            "components": {
                "block_center": round(center, 3),
                "mounting_A": round(sum_A, 3),
                "mounting_B": round(sum_B, 3)
            }
        }, status=status.HTTP_200_OK)
