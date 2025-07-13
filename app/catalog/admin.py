from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from catalog.models import (
    LoadGroup, Material, PipeDiameter, NominalDiameter, CoveringType, Covering, Directory,
    DirectoryField, DirectoryEntry, DirectoryEntryValue, ProductFamily, ProductClass, Load, SpringStiffness,
    SupportDistance, PipeMountingGroup, PipeMountingRule, ComponentGroup, SpringBlockFamilyBinding, SSBCatalog,
    ClampMaterialCoefficient, SSGCatalog
)


class DirectoryFieldInline(admin.TabularInline):
    model = DirectoryField
    extra = 0


@admin.register(Directory)
class DirectoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'display_name_template')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name')
    inlines = (DirectoryFieldInline,)


class DirectoryEntryValueInline(admin.TabularInline):
    model = DirectoryEntryValue
    extra = 0


@admin.register(DirectoryEntry)
class DirectoryEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'directory', 'display_name', 'get_values')
    list_display_links = ('id', 'display_name')
    search_fields = ('id', 'directory__name', 'display_name')
    inlines = (DirectoryEntryValueInline,)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('values__directory_field')

    @admin.display(description='Все значения')
    def get_values(self, obj):
        values = []
        for val_obj in obj.values.all():
            field_name = val_obj.directory_field.name
            value = val_obj.value
            values.append(f'{field_name}={value}')
        return '; '.join(values)


@admin.register(NominalDiameter)
class NominalDiameterAdmin(admin.ModelAdmin):
    list_display = ('id', 'dn')
    list_display_links = ('id', 'dn')
    search_fields = ('dn',)


@admin.register(PipeDiameter)
class PipeDiameterAdmin(admin.ModelAdmin):
    list_display = ('id', '__str__', 'standard', 'size')
    list_display_links = ('id', '__str__')
    list_filter = ('standard',)
    search_fields = ('dn__dn',)


@admin.register(LoadGroup)
class LoadGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'lgv', 'kn')
    list_display_links = ('id',)
    search_fields = ('id', 'lgv', 'kn')


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'type', 'name')
    list_display_links = ('id', 'name')
    list_filter = ('group',)
    search_fields = ('group', 'name',)


@admin.register(CoveringType)
class CoveringTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'numeric', 'name')
    list_display_links = ('id', 'numeric', 'name')
    search_fields = ('name',)

    readonly_fields = ('id',)
    fields = ('id', 'numeric', 'name_ru', 'name_en', 'description_ru', 'description_en')


@admin.register(Covering)
class CoveringAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)

    readonly_fields = ('id',)
    fields = ('id', 'name_ru', 'name_en', 'description_ru', 'description_en')


@admin.register(ProductClass)
class ProductClassAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    search_fields = ('name',)
    readonly_fields = ('id',)
    fields = ('id', 'name')


@admin.register(ProductFamily)
class ProductFamilyAdmin(admin.ModelAdmin):
    list_display = ('id', 'product_class', 'name', 'is_upper_mount_selectable', 'has_rod')
    list_display_links = ('id', 'name')
    list_filter = ('is_upper_mount_selectable', 'has_rod')
    search_fields = ('name', 'product_class__name')
    readonly_fields = ('id',)
    fields = ('id', 'product_class', 'name', 'icon', 'is_upper_mount_selectable', 'has_rod')


@admin.register(Load)
class LoadAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'series_name', 'size', 'rated_stroke_50', 'rated_stroke_100', 'rated_stroke_200', 'load_group_lgv',
        'design_load',
    )
    list_display_links = ('id',)
    list_filter = ('series_name',)


@admin.register(SpringStiffness)
class SpringStiffnessAdmin(admin.ModelAdmin):
    list_display = ('id', 'series_name', 'size', 'rated_stroke', 'value')
    list_display_links = ('id',)
    list_filter = ('series_name',)


@admin.register(SupportDistance)
class SupportDistanceAdmin(admin.ModelAdmin):
    pass


@admin.register(PipeMountingGroup)
class PipeMountingGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')
    filter_horizontal = ('variants',)
    search_fields = ('name', 'variants__detail_type__designation', 'variants_detail_type__name')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('variants')

    @admin.display(description='Типы креплений')
    def get_variants(self, obj):
        variants = list(obj.variants.all()[:5])
        names = [f'{variant.detail_type.designation} - {variant.detail_type.name}' for variant in variants]

        if obj.variants.count() > 5:
            return ', '.join(names) + ', ...'
        return ', '.join(names)


@admin.register(PipeMountingRule)
class PipeMountingRuleAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'family', 'num_spring_blocks', 'pipe_direction', 'get_pipe_mounting_groups', 'get_mounting_groups_b',
    )
    list_display_links = ('id',)
    list_filter = ('family', 'num_spring_blocks', 'pipe_direction')
    filter_horizontal = ('pipe_mounting_groups', 'mounting_groups_b')
    autocomplete_fields = ('family',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('pipe_mounting_groups')

    @admin.display(description='Группы креплений к трубе')
    def get_pipe_mounting_groups(self, obj):
        groups = list(obj.pipe_mounting_groups.all()[:5])
        names = [group.name for group in groups]

        if obj.pipe_mounting_groups.count() > 5:
            return ', '.join(names) + ', ...'
        return ', '.join(names)

    @admin.display(description='Группы креплений B')
    def get_mounting_groups_b(self, obj):
        groups = list(obj.mounting_groups_b.all()[:5])
        names = [group.name for group in groups]

        if obj.mounting_groups_b.count() > 5:
            return ', '.join(names) + ', ...'
        return ', '.join(names)


@admin.register(ComponentGroup)
class ComponentGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'group_type', 'get_detail_types')
    list_display_links = ('id', 'group_type')
    list_filter = ('group_type',)
    filter_horizontal = ('detail_types',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('detail_types')

    @admin.display(description=_('Типы деталей/изделии'))
    def get_detail_types(self, obj):
        detail_types = list(obj.detail_types.all()[:5])
        names = [detail_type.designation for detail_type in detail_types]

        if obj.detail_types.count() > 5:
            return ', '.join(names) + ', ...'
        return ', '.join(names)


@admin.register(SpringBlockFamilyBinding)
class SpringBlockFamilyBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'family', 'get_spring_block_types')
    list_display_links = ('id',)
    list_filter = ('family',)
    filer_horizontal = ('spring_block_types',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('spring_block_types')

    @admin.display(description=_('Допустимые типы пружинных блоков'))
    def get_spring_block_types(self, obj):
        detail_types = list(obj.spring_block_types.all()[:5])
        names = [detail_type.designation for detail_type in detail_types]

        if obj.spring_block_types.count() > 5:
            return ', '.join(names) + ', ...'
        return ', '.join(names)


@admin.register(SSBCatalog)
class SSBCatalogAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'fn', 'stroke', 'f', 'l', 'l1', 'l2_min', 'l2_max', 'l3_min', 'l3_max', 'l4', 'a', 'b', 'h', 'diameter_j',
    )
    list_display_links = ('id',)


@admin.register(SSGCatalog)
class SSGCatalogAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'fn', 'l_min', 'l_max', 'l1', 'd', 'd1', 'r', 's', 'sw', 'regulation',
    )
    list_display_links = ('id',)

@admin.register(ClampMaterialCoefficient)
class ClampMaterialCoefficientAdmin(admin.ModelAdmin):
    list_display = ["id", "material_group", "temperature_from", "temperature_to", "coefficient"]
    list_display_links = ["id"]
