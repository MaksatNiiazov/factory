from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_flex_fields import FlexFieldsModelSerializer

from auditlog.models import LogEntry

from kernel.api.base import (
    TranslatorSerializerMixin,
    CleanSerializerMixin,
    ChoicesSerializer,
)

from catalog.models import (
    PipeDiameter,
    LoadGroup,
    Material,
    NominalDiameter,
    CoveringType,
    Covering,
    DirectoryField,
    Directory,
    SupportDistance,
    ProductFamily,
    ProductClass,
    Load,
    SpringStiffness,
    PipeMountingGroup,
    PipeMountingRule,
    ComponentGroup,
    SpringBlockFamilyBinding,
    SSBCatalog,
    SSGCatalog,
    ClampMaterialCoefficient,
)


class CatalogueBaseSerializer(
    CleanSerializerMixin, TranslatorSerializerMixin, FlexFieldsModelSerializer
):
    """
    Базовый сериализатор для каталогов, который добавляет поля для отображения наименования элемента и наименования в ERP.
    """

    display_name = serializers.SerializerMethodField(label=_("Наименование элемента"))
    erp_display_name = serializers.SerializerMethodField(label=_("Наименование в ERP"))

    def get_display_name(self, instance):
        return instance.display_name

    def get_erp_display_name(self, instance):
        if hasattr(instance, "erp_display_name"):
            return instance.erp_display_name

        return None


class DirectoryFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = DirectoryField
        fields = ["id", "directory", "name", "field_type"]


class DirectorySerializer(FlexFieldsModelSerializer):
    class Meta:
        model = Directory
        fields = ["id", "name", "display_name_template", "fields"]
        expandable_fields = {
            "fields": (DirectoryFieldSerializer, {"many": True}),
        }
        extra_kwargs = {"fields": {"read_only": True}}


class NominalDiameterSerializer(CatalogueBaseSerializer):
    class Meta:
        model = NominalDiameter
        fields = ("id", "dn")


class PipeDiameterSerializer(CatalogueBaseSerializer):
    class Meta:
        model = PipeDiameter
        fields = ("id", "dn", "option", "standard", "size", "display_name")
        expandable_fields = {
            "dn": NominalDiameterSerializer,
            "option": (
                ChoicesSerializer,
                {"model": PipeDiameter, "field_name": "option"},
            ),
            "standard": (
                ChoicesSerializer,
                {"model": PipeDiameter, "field_name": "standard"},
            ),
        }


class LoadGroupSerializer(CatalogueBaseSerializer):
    class Meta:
        model = LoadGroup
        fields = ("id", "lgv", "kn", "display_name")


class MaterialSerializer(CatalogueBaseSerializer):
    class Meta:
        model = Material
        fields = (
            "id",
            "group",
            "name",
            "display_name",
            "type",
            "astm_spec",
            "asme_type",
            "asme_uns",
            "source",
            "min_temp",
            "max_temp",
            "max_exhaust_gas_temp",
            "lz",
            "density",
            "spring_constant",
            "rp0",
        )
        translated_fields = ("name",)


class CoveringTypeSerializer(CatalogueBaseSerializer):
    class Meta:
        model = CoveringType
        fields = ("id", "numeric", "name", "description", "display_name")
        translated_fields = ("name", "description")


class CoveringSerializer(CatalogueBaseSerializer):
    class Meta:
        model = Covering
        fields = ("id", "name", "description")
        translated_fields = ("name", "description")


class SupportDistanceSerializer(CatalogueBaseSerializer):
    class Meta:
        model = SupportDistance
        fields = ("id", "name", "value")


class ProductClassSerializer(CatalogueBaseSerializer):
    class Meta:
        model = ProductClass
        fields = ("id", "name")


class ProductFamilySerializer(CatalogueBaseSerializer):
    class Meta:
        model = ProductFamily
        fields = [
            "id",
            "product_class",
            "name",
            "icon",
            "is_upper_mount_selectable",
            "has_rod",
            "selection_type",
        ]


class LoadSerializer(CatalogueBaseSerializer):
    class Meta:
        model = Load
        fields = (
            "id",
            "series_name",
            "size",
            "rated_stroke_50",
            "rated_stroke_100",
            "rated_stroke_200",
            "load_group_lgv",
            "design_load",
        )


class SpringStiffnessSerializer(CatalogueBaseSerializer):
    class Meta:
        model = SpringStiffness
        fields = ("id", "series_name", "size", "rated_stroke", "value")


class PipeMountingGroupSerializer(CatalogueBaseSerializer):
    class Meta:
        model = PipeMountingGroup
        fields = ("id", "name", "show_variants", "variants")
        expandable_fields = {
            "variants": ("ops.api.serializers.VariantSerializer", {"many": True}),
        }


class PipeMountingRuleSerializer(CatalogueBaseSerializer):
    class Meta:
        model = PipeMountingRule
        fields = (
            "id",
            "family",
            "num_spring_blocks",
            "pipe_direction",
            "pipe_mounting_groups_bottom",
            "pipe_mounting_groups_top",
        )
        expandable_fields = {
            "family": ProductFamilySerializer,
            "pipe_mounting_groups_bottom": (PipeMountingGroupSerializer, {"many": True}),
            "pipe_mounting_groups_top": (PipeMountingGroupSerializer, {"many": True}),
        }


class ComponentGroupSerializer(CatalogueBaseSerializer):
    class Meta:
        model = ComponentGroup
        fields = ("id", "group_type", "detail_types")
        expandable_fields = {
            "detail_types": (
                "ops.api.serializers.DetailTypeSerializer",
                {"many": True},
            ),
        }


class SpringBlockFamilyBindingSerializer(CatalogueBaseSerializer):
    class Meta:
        model = SpringBlockFamilyBinding
        fields = ("id", "family", "spring_block_types")
        expandable_fields = {
            "family": ProductFamilySerializer,
            "spring_block_types": (
                "ops.api.serializers.DetailTypeSerializer",
                {"many": True},
            ),
        }


class SSBCatalogSerializer(CatalogueBaseSerializer):
    class Meta:
        model = SSBCatalog
        fields = [
            "id",
            "fn",
            "stroke",
            "f",
            "l",
            "l1",
            "l2_min",
            "l2_max",
            "l3_min",
            "l3_max",
            "l4",
            "a",
            "b",
            "h",
            "diameter_j",
        ]


class SSGCatalogSerializer(CatalogueBaseSerializer):
    class Meta:
        model = SSGCatalog
        fields = [
            'id',
            'fn',
            'l_min',
            'l_max',
            'l1',
            'd',
            'd1',
            'r',
            's',
            'sw',
            'regulation',
        ]


class ClampMaterialCoefficientSerializer(CatalogueBaseSerializer):
    class Meta:
        model = ClampMaterialCoefficient
        fields = ["id", "material_group", "temperature_from", "temperature_to", "coefficient"]


class LogEntrySerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()
    content_type = serializers.CharField(source="content_type.model")

    class Meta:
        model = LogEntry
        fields = [
            "id",
            "timestamp",
            "actor",
            "action",
            "content_type",
            "object_pk",
            "changes",
        ]

    def get_actor(self, obj):
        user = obj.actor
        return (
            {
                "id": user.id,
                "username": user.get_username(),
            }
            if user
            else None
        )
