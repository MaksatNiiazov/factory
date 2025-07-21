from django.utils.translation import gettext_lazy as _

from rest_flex_fields import FlexFieldsModelSerializer

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from catalog.api.serializers import MaterialSerializer, PipeDiameterSerializer, ProductFamilySerializer, \
    PipeMountingGroupSerializer
from catalog.choices import PipeDirectionChoices
from catalog.models import PipeDiameter, Material, ProductClass, ProductFamily, SupportDistance, PipeMountingGroup
from kernel.api.base import TranslatorSerializerMixin, CleanSerializerMixin, ChoicesSerializer

from kernel.api.serializers import UserSerializer, OrganizationSerializer
from ops.api.constants import LOAD_FACTORS

from ops.models import (
    Project, DetailType, Item, ProjectItem, ProjectItemRevision, ItemChild, FieldSet, Attribute, Variant,
    BaseComposition,
)


class PipeOptionsSerializer(serializers.Serializer):
    location = serializers.CharField(required=True)
    direction = serializers.CharField(required=True)
    branch_qty = serializers.IntegerField(required=True, min_value=1, max_value=4)
    without_pipe_clamp = serializers.BooleanField(required=True)


class LoadAndMoveSerializer(serializers.Serializer):
    load_plus_x = serializers.FloatField(required=True)
    load_plus_y = serializers.FloatField(required=True)
    load_plus_z = serializers.FloatField(required=True)

    load_minus_x = serializers.FloatField(required=True)
    load_minus_y = serializers.FloatField(required=True)
    load_minus_z = serializers.FloatField(required=True)

    additional_load_x = serializers.FloatField(required=True)
    additional_load_y = serializers.FloatField(required=True)
    additional_load_z = serializers.FloatField(required=True)

    test_load_x = serializers.FloatField(required=True)
    test_load_y = serializers.FloatField(required=True)
    test_load_z = serializers.FloatField(required=True)

    move_plus_x = serializers.FloatField(required=True)
    move_plus_y = serializers.FloatField(required=True)
    move_plus_z = serializers.FloatField(required=True)

    move_minus_x = serializers.FloatField(required=True)
    move_minus_y = serializers.FloatField(required=True)
    move_minus_z = serializers.FloatField(required=True)

    estimated_state = serializers.ChoiceField(choices=["cold", "hot"], required=True)


class SpringChoiceSerializer(serializers.Serializer):
    minimum_spring_travel = serializers.FloatField(required=True)
    selected_spring = serializers.DictField(required=True, allow_null=True)


class PipeParamsSerializer(serializers.Serializer):
    temp1 = serializers.FloatField(required=True, allow_null=True)
    temp2 = serializers.FloatField(required=True, allow_null=True)
    nominal_diameter = serializers.PrimaryKeyRelatedField(
        queryset=PipeDiameter.objects.all(), required=True, allow_null=True,
    )
    outer_diameter_special = serializers.FloatField(required=True, allow_null=True)
    support_distance = serializers.PrimaryKeyRelatedField(
        queryset=SupportDistance.objects.all(), required=True, allow_null=True,
    )
    support_distance_manual = serializers.FloatField(required=True, allow_null=True)
    insulation_thickness = serializers.FloatField(required=True, allow_null=True)
    outer_insulation_thickness = serializers.FloatField(required=True, allow_null=True)
    clamp_material = serializers.PrimaryKeyRelatedField(
        queryset=Material.objects.all(), required=True, allow_null=True,
    )
    pipe_mounting_group = serializers.PrimaryKeyRelatedField(
        queryset=PipeMountingGroup.objects.all(), required=True, allow_null=True, label='Тип крепления к трубе',
    )
    add_to_specification = serializers.BooleanField(required=True)


class PipeClampSerializer(serializers.Serializer):
    pipe_mount = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), required=True, allow_null=True, label='Выбор крепления к трубе',
    )
    top_mount = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), required=True, allow_null=True, label='Выбор верхнего соединения',
    )


class SystemSettingsSerializer(serializers.Serializer):
    system_height = serializers.FloatField(required=True, allow_null=True)
    connection_height = serializers.FloatField(required=True, allow_null=True)
    suspension = serializers.FloatField(required=True, allow_null=True)
    pipe_axis_height = serializers.FloatField(required=True, allow_null=True)


class SelectionParamsSerializer(serializers.Serializer):
    product_class = serializers.PrimaryKeyRelatedField(
        queryset=ProductClass.objects.all(), required=True, allow_null=True,
    )
    product_family = serializers.PrimaryKeyRelatedField(
        queryset=ProductFamily.objects.all(), required=True, allow_null=True,
    )
    pipe_options = PipeOptionsSerializer(required=True)
    load_and_move = LoadAndMoveSerializer(required=True)
    spring_choice = SpringChoiceSerializer(required=True)
    pipe_params = PipeParamsSerializer(required=True)
    pipe_clamp = PipeClampSerializer(required=True)
    system_settings = SystemSettingsSerializer(required=True)
    variant = serializers.PrimaryKeyRelatedField(
        queryset=Variant.objects.all(), required=True, allow_null=True,
    )


class ProjectItemRevisionSerializer(CleanSerializerMixin, FlexFieldsModelSerializer):
    class Meta:
        model = ProjectItemRevision
        fields = ('id', 'revision_item')
        expandable_fields = {
            'revision_item': 'ops.api.serializers.ItemSerializer',
        }


class ProjectItemSerializer(CleanSerializerMixin, FlexFieldsModelSerializer):
    original_item = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), required=False, label=_('Оригинальное изделие/деталь'),
    )

    class Meta:
        model = ProjectItem
        fields = (
            'id', 'position_number', 'original_item', 'customer_marking', 'count', 'revisions',
            'load_plus_x', 'load_plus_y', 'load_plus_z', 'load_minus_x', 'load_minus_y', 'load_minus_z',
            'additional_load_x', 'additional_load_y', 'additional_load_z',
            'move_plus_x', 'move_plus_y', 'move_plus_z', 'move_minus_x', 'move_minus_y', 'move_minus_z',
            'estimated_state', 'minimum_spring_travel', 'pipe_location', 'pipe_direction', 'ambient_temperature',
            'nominal_diameter', 'outer_diameter_special', 'insulation_thickness',
            'span', 'clamp_material', 'insert',
            'crm_mark_cont', 'work_type', 'selection_params',
            'system_height', 'comment',
        )
        extra_kwargs = {
            'revisions': {'read_only': True},
        }
        expandable_fields = {
            'original_item': 'ops.api.serializers.ItemSerializer',
            'revisions': ('ops.api.serializers.ProjectItemRevisionSerializer', {'many': True}),
            'nominal_diameter': PipeDiameterSerializer,
            'outer_diameter': PipeDiameterSerializer,
            'clamp_material': MaterialSerializer,
            'pipe_mount': 'ops.api.serializers.DetailTypeSerializer',
            'top_mount': 'ops.api.serializers.DetailTypeSerializer',
        }


class ProjectSerializer(CleanSerializerMixin, FlexFieldsModelSerializer):
    class Meta:
        model = Project
        fields = (
            'id', 'number', 'organization', 'owner', 'status', 'load_unit', 'move_unit', 'temperature_unit', 'created',
            'modified', 'standard',
        )
        expandable_fields = {
            'organization': OrganizationSerializer,
            'owner': UserSerializer,
        }


class CRMProjectItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True, label=_('Идентификатор'))
    product_type = serializers.CharField(required=True)
    quantity = serializers.IntegerField(required=True, label=_('Количество'))
    working_type = serializers.CharField(required=True)
    mark_cont = serializers.CharField(required=True)
    number = serializers.IntegerField(required=True)
    wicad_id = serializers.CharField(required=False, allow_null=True)


class CRMProjectSerializer(serializers.Serializer):
    crm_login = serializers.CharField(required=True, label=_('Логин пользователя'))
    contragent = serializers.CharField(required=True, label=_('Контрагент'))
    datetime = serializers.DateTimeField(required=True, label=_('Дата и время'))
    number = serializers.CharField(required=True, label=_('Номер проекта'))
    project_url = serializers.URLField(required=True, label=_('URL-адрес проекта'))
    product_asking_date = serializers.DateField(required=False, allow_null=True)
    product_calc_date = serializers.DateField(required=False, allow_null=True)
    project_items = CRMProjectItemSerializer(many=True)


class CRMProjectSyncERPSerializer(serializers.Serializer):
    number = serializers.CharField(required=True, label=_('Номер проекта'))


class VariantSerializer(CleanSerializerMixin, FlexFieldsModelSerializer):
    class Meta:
        model = Variant
        fields = (
            'id', 'name', 'marking_template', 'sketch', 'sketch_coords',
            'subsketch', 'subsketch_coords', 'attributes', 'deleted_at',
            'formula_weight', 'formula_height', 'series',
        )
        read_only_fields = ('attributes',)
        expandable_fields = {
            'attributes': ('ops.api.serializers.AttributeSerializer', {'many': True}),
        }


class VariantWithDetailTypeSerializer(VariantSerializer):
    class Meta(VariantSerializer.Meta):
        fields = VariantSerializer.Meta.fields + ('detail_type',)
        read_only_fields = VariantSerializer.Meta.read_only_fields + ('detail_type',)
        expandable_fields = VariantSerializer.Meta.expandable_fields.copy()
        expandable_fields.update({
            'detail_type': 'ops.api.serializers.DetailTypeSerializer',
        })


class DetailTypeSerializer(CleanSerializerMixin, FlexFieldsModelSerializer):
    class Meta:
        model = DetailType
        fields = (
            'id', 'product_family', 'name', 'designation', 'category', 'variants', 'branch_qty',
        )
        extra_kwargs = {
            'variants': {'read_only': True},
        }
        expandable_fields = {
            'product_family': ProductFamilySerializer,
            'variants': (VariantSerializer, {'many': True}),
            'category': (ChoicesSerializer, {'model': DetailType, 'field_name': 'category'}),
            'branch_qty': (ChoicesSerializer, {'model': DetailType, 'field_name': 'branch_qty'}),
        }


class BaseCompositionSerializer(CleanSerializerMixin, FlexFieldsModelSerializer):
    class Meta:
        model = BaseComposition
        fields = [
            'id', 'base_parent', 'base_parent_variant', 'base_child', 'base_child_variant', 'position', 'count',
        ]
        expandable_fields = {
            'base_parent': DetailTypeSerializer,
            'base_parent_variant': VariantSerializer,
            'base_child': DetailTypeSerializer,
            'base_child_variant': VariantSerializer,
        }


class FieldSetSerializer(CleanSerializerMixin, TranslatorSerializerMixin, FlexFieldsModelSerializer):
    class Meta:
        model = FieldSet
        fields = ('id', 'icon', 'name', 'label')
        translated_fields = ('label',)


class AttributeSerializer(CleanSerializerMixin, TranslatorSerializerMixin, FlexFieldsModelSerializer):
    choices = serializers.JSONField(required=False, label=_('Список'))

    class Meta:
        model = Attribute
        fields = (
            'id', 'detail_type', 'variant', 'name', 'label', 'type', 'usage', 'catalog', 'catalog_api', 'description',
            'is_required', 'default', 'choices', 'fieldset', 'position', 'calculated_value',
        )
        translated_fields = ('label', 'description')
        expandable_fields = {
            'detail_type': DetailTypeSerializer,
            'variant': VariantSerializer,
            'fieldset': FieldSetSerializer,
        }


class ItemSerializer(CleanSerializerMixin, FlexFieldsModelSerializer):
    class Meta:
        model = Item
        fields = (
            'id', 'type', 'variant', 'inner_id', 'name', 'marking', 'marking_errors', 'comment',
            'weight', 'weight_errors', 'height', 'height_errors', 'parameters', 'parameters_errors',
            'locked_parameters',
            'material', 'author', 'erp_id', 'created', 'modified',
        )
        extra_kwargs = {
            'inner_id': {'read_only': True},
            'marking': {'read_only': True},
            'marking_errors': {'read_only': True},
            'parameters_errors': {'read_only': True},
            'locked_parameters': {'read_only': True},
            'erp_id': {'read_only': True},
            'weight_errors': {'read_only': True},
            'height_errors': {'read_only': True},
        }
        expandable_fields = {
            'type': DetailTypeSerializer,
            'variant': VariantSerializer,
            'author': UserSerializer,
            'material': MaterialSerializer,
        }


class ItemExportSerializer(serializers.Serializer):
    type = serializers.CharField(required=True)
    category = serializers.CharField(required=True)
    designation = serializers.CharField(required=True)
    is_empty = serializers.BooleanField(default=False)


class ItemImportSerializer(serializers.Serializer):
    type = serializers.CharField(required=True)
    category = serializers.CharField(required=True)
    designation = serializers.CharField(required=True)
    file = serializers.FileField(required=True)
    is_dry_run = serializers.BooleanField(default=False)


class ItemChildSerializer(CleanSerializerMixin, FlexFieldsModelSerializer):
    def validate(self, data):
        parent_pk = self.context['view'].kwargs['parent_pk']
        data['parent_id'] = parent_pk
        return super().validate(data)

    class Meta:
        model = ItemChild
        fields = ('id', 'child', 'position', 'count')
        expandable_fields = {
            'child': ItemSerializer,
        }


class DetailSerializer(CleanSerializerMixin, FlexFieldsModelSerializer):
    class Meta:
        model = Item
        fields = (
            'id', 'type', 'variant', 'inner_id', 'name', 'marking', 'children',
            'material', 'author', 'created', 'modified',
        )


class MarkingTemplateSerializer(serializers.Serializer):
    parameters = serializers.JSONField(required=True, label=_('JSON-параметры'))
    marking_template = serializers.CharField(required=True, label=_('Шаблон маркировки'))


class CalculateLoadSerializer(serializers.Serializer):
    load_minus = serializers.FloatField(required=True, label=_('Нагрузка (-)'))
    movement_plus = serializers.FloatField(required=False, label=_('Перемещение (+)'))
    movement_minus = serializers.FloatField(required=False, label=_('Перемещение (-)'))
    minimum_spring_travel = serializers.FloatField(required=True, initial=5, label=_('Минимальный запас хода'))
    standard_series = serializers.BooleanField(required=False, initial=True, label=_('W-серия'))
    l_series = serializers.BooleanField(required=False, label=_('L-серия'))

    def validate(self, data):
        movement_plus = data.get('movement_plus')
        movement_minus = data.get('movement_minus')

        if movement_plus is not None and movement_minus is not None:
            raise ValidationError({'movement_plus': _('Нельзя указать оба перемещения')})

        if movement_plus is None and movement_minus is None:
            raise ValidationError({'movement_plus': _('Необходимо выбрать один из перемещении')})

        standardSeries = data.get('standard_series')
        lSeries = data.get('l_series')

        if not standardSeries and not lSeries:
            raise ValidationError({'l_series': _('Укажите хотя бы одну из серии')})

        return super().validate(data)


class ShockSelectionLoadAndMoveSerializer(serializers.Serializer):
    installation_length = serializers.IntegerField(required=True, allow_null=True)
    move = serializers.FloatField(required=True, allow_null=True)
    load = serializers.IntegerField(required=True, allow_null=True)
    load_type = serializers.CharField(required=True, allow_null=True)


class ShockSelectionPipeOptionsSerializer(serializers.Serializer):
    location = serializers.CharField(required=True, allow_null=True)
    shock_counts = serializers.IntegerField(required=True, allow_null=True)


class ShockSelectionPipeParamsSerializer(serializers.Serializer):
    temperature = serializers.FloatField(required=True, allow_null=True)
    pipe_diameter = serializers.PrimaryKeyRelatedField(
        queryset=PipeDiameter.objects.all(), required=True, allow_null=True,
    )
    pipe_diameter_size_manual = serializers.FloatField(required=True, allow_null=True)
    support_distance = serializers.PrimaryKeyRelatedField(
        queryset=SupportDistance.objects.all(), required=True, allow_null=True,
    )
    support_distance_manual = serializers.FloatField(required=True, allow_null=True)
    mounting_group_a = serializers.PrimaryKeyRelatedField(
        queryset=PipeMountingGroup.objects.all(), required=True, allow_null=True,
    )
    mounting_group_b = serializers.PrimaryKeyRelatedField(
        queryset=PipeMountingGroup.objects.all(), required=True, allow_null=True,
    )
    material = serializers.PrimaryKeyRelatedField(
        queryset=Material.objects.all(), required=True, allow_null=True,
    )


class ShockSelectionPipeClampSerializer(serializers.Serializer):
    pipe_clamp_a = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), required=True, allow_null=True,
    )
    pipe_clamp_b = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), required=True, allow_null=True,
    )


class ShockSelectionParamsSerializer(serializers.Serializer):
    product_class = serializers.PrimaryKeyRelatedField(
        queryset=ProductClass.objects.all(), required=True, allow_null=True,
    )
    product_family = serializers.PrimaryKeyRelatedField(
        queryset=ProductFamily.objects.all(), required=True, allow_null=True,
    )
    load_and_move = ShockSelectionLoadAndMoveSerializer(required=True)
    pipe_options = ShockSelectionPipeOptionsSerializer(required=True)
    pipe_params = ShockSelectionPipeParamsSerializer(required=True)
    pipe_clamp = ShockSelectionPipeClampSerializer(required=True)
    variant = serializers.PrimaryKeyRelatedField(
        queryset=Variant.objects.all(), required=True, allow_null=True,
    )


class SpacerSelectionLoadAndMoveSerializer(serializers.Serializer):
    installation_length = serializers.IntegerField(required=False, allow_null=True)
    load = serializers.IntegerField(required=True, allow_null=True)
    load_type = serializers.CharField(required=True, allow_null=True)
    mounting_length = serializers.IntegerField(required=False, allow_null=True)


class SpacerSelectionPipeOptionsSerializer(serializers.Serializer):
    location = serializers.CharField(required=False, allow_null=True)
    spacer_counts = serializers.IntegerField(required=False, allow_null=True)


class SpacerSelectionPipeParamsSerializer(serializers.Serializer):
    temperature = serializers.FloatField(required=False, allow_null=True)
    pipe_diameter = serializers.PrimaryKeyRelatedField(
        queryset=PipeDiameter.objects.all(), required=False, allow_null=True,
    )
    pipe_diameter_size_manual = serializers.FloatField(required=False, allow_null=True)
    support_distance = serializers.PrimaryKeyRelatedField(
        queryset=SupportDistance.objects.all(), required=False, allow_null=True,
    )
    support_distance_manual = serializers.FloatField(required=False, allow_null=True)
    mounting_group_a = serializers.PrimaryKeyRelatedField(
        queryset=PipeMountingGroup.objects.all(), required=False, allow_null=True,
    )
    mounting_group_b = serializers.PrimaryKeyRelatedField(
        queryset=PipeMountingGroup.objects.all(), required=False, allow_null=True,
    )
    material = serializers.PrimaryKeyRelatedField(
        queryset=Material.objects.all(), required=False, allow_null=True,
    )


class SpacerSelectionPipeClampSerializer(serializers.Serializer):
    pipe_clamp_a = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), required=False, allow_null=True,
    )
    pipe_clamp_b = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), required=False, allow_null=True,
    )


class SpacerSelectionParamsSerializer(serializers.Serializer):
    load_and_move = SpacerSelectionLoadAndMoveSerializer(required=True)
    pipe_options = SpacerSelectionPipeOptionsSerializer(required=True)
    pipe_params = SpacerSelectionPipeParamsSerializer(required=True)
    pipe_clamp = SpacerSelectionPipeClampSerializer(required=True)
    variant = serializers.PrimaryKeyRelatedField(
        queryset=Variant.objects.all(), required=False, allow_null=True,
    )


class ShockCalcSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(help_text="ID Item (семейство SSB)")
    load_type = serializers.ChoiceField(
        choices=[(k, k) for k in LOAD_FACTORS.keys()],
        help_text="Тип нагрузки: H, HZ или HS"
    )
    load_value = serializers.FloatField(min_value=0, help_text="Величина нагрузки в кН")
    sn = serializers.FloatField(
        help_text="Рабочее перемещение Sn, мм (положительное — сжатие, отрицательное — растяжение)")
    branch_qty = serializers.IntegerField(
        min_value=1, max_value=2,
        help_text="Количество амортизаторов в ветке (1 или 2)"
    )
    pipe_direction = serializers.ChoiceField(
        choices=[(c.value, c.value) for c in PipeDirectionChoices],
        help_text="Направление трубы (x, y или z)"
    )
    mounting_length_full = serializers.FloatField(
        required=False, allow_null=True,
        help_text="(Опционально) Полная монтажная длина вместе с крепежами, мм"
    )
    mounting_variants = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=False,
        help_text="(Опционально) Список ID вариантов креплений (Variant.id)"
    )
    use_extra_margin = serializers.BooleanField(
        help_text="Флаг «±10 % запаса хода»"
    )

    def validate(self, attrs):
        ml = attrs.get('mounting_length_full')
        mv = attrs.get('mounting_variants')
        # либо оба переданы, либо ни одного
        if (ml is None) ^ (mv is None):
            raise serializers.ValidationError(
                "Если указан mounting_length_full, обязательно укажите mounting_variants, и наоборот."
            )
        return attrs


class ShockCalcResultSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(help_text="ID исходного Item")
    result = serializers.CharField(help_text="Код SSB")
    fn = serializers.IntegerField(help_text="Выбранная нагрузка FN, кН")
    stroke = serializers.FloatField(help_text="Выбранный ход, мм")
    type = serializers.IntegerField(help_text="Тип монтажа (1 или 2)")
    mounting_length = serializers.FloatField(
        allow_null=True, help_text="Входная монтажная длина, мм"
    )
    extender = serializers.FloatField(help_text="Длина удлинителя, мм")
    L2_req = serializers.FloatField(help_text="Требуемая длина блока, мм")
    L2_min = serializers.FloatField(help_text="Минимальное L2 из каталога, мм")
    L2_max = serializers.FloatField(help_text="Максимальное L2 из каталога, мм")
    L2_avg = serializers.FloatField(help_text="Среднее L2 из каталога, мм")
    L3 = serializers.FloatField(help_text="L3 из каталога, мм")
    L4 = serializers.FloatField(help_text="L4 из каталога, мм")
    block_length = serializers.FloatField(help_text="Длина пружинного блока (L3+L4), мм")


class AvailableMountsRequestSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(help_text="ID Item (семейство SSB)")
    branch_qty = serializers.IntegerField(
        min_value=1, max_value=2,
        help_text="Количество пружинных блоков (1 или 2)"
    )
    pipe_direction = serializers.ChoiceField(
        choices=[(c.value, c.value) for c in PipeDirectionChoices],
        help_text="Направление трубы (x, y или z)"
    )


class MountingVariantSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="ID варианта нижнего крепления")
    name = serializers.CharField(help_text="Наименование варианта")
    mounting_size = serializers.FloatField(help_text="Монтажный размер, мм")


class AvailableTopMountsRequestSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(help_text="ID Item (семейство SSB)")
    branch_qty = serializers.IntegerField(
        min_value=1, max_value=2,
        help_text="Количество пружинных блоков (1 или 2)"
    )


class TopMountVariantSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="ID варианта верхнего крепления")
    name = serializers.CharField(help_text="Название варианта")
    mounting_size = serializers.FloatField(help_text="Монтажный размер, мм")


class AssemblyLengthSerializer(serializers.Serializer):
    item_id = serializers.IntegerField(help_text="ID Item (семейство SSB)")
    load_type = serializers.ChoiceField(
        choices=[('H', 'H'), ('HZ', 'HZ'), ('HS', 'HS')],
        help_text="Тип нагрузки: H, HZ или HS"
    )
    load_value = serializers.FloatField(help_text="Величина нагрузки, кН")
    sn = serializers.FloatField(help_text="Перемещение Sn, мм (+/−)")
    branch_qty = serializers.IntegerField(
        min_value=1, max_value=2,
        help_text="Количество пружинных блоков (1 или 2)"
    )
    pipe_direction = serializers.ChoiceField(
        choices=[(c.value, c.value) for c in PipeDirectionChoices],
        help_text="Направление трубы (x, y или z)"
    )
    use_extra_margin = serializers.BooleanField(help_text="±10% запас хода")

    mounting_variants = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True,
        help_text="Список ID нижних креплений A"
    )
    top_mount_variants = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True,
        help_text="Список ID верхних креплений B"
    )
