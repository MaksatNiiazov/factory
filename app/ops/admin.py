import nested_admin

from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

from auditlog.models import LogEntry

from import_export.admin import ImportMixin

from rangefilter.filters import DateTimeRangeFilterBuilder

from kernel.inlines import AuditLogInline

from ops.api.exceptions import FormatNotSupported, ResourceNotFound
from ops.models import (
    Project, DetailType, Item, ProjectItem, ItemChild, FieldSet, Attribute, Variant, BaseComposition, ERPSyncLog,
    ERPSync,
)
from ops.resources import get_resources_list
from ops.widgets import MarkingTemplateWidget
from taskmanager.choices import TaskType
from taskmanager.models import TaskAttachment, Task
from ops.tasks import process_import_task


class ProjectItemInline(admin.StackedInline):
    model = ProjectItem
    extra = 0
    fieldsets = (
        (None, {
            'fields': ('position_number', 'original_item', 'customer_marking', 'count')
        }),
        (_('Нагрузка и перемещения'), {
            'fields': (
                'load_plus_x', 'load_plus_y', 'load_plus_z', 'load_minus_x', 'load_minus_y', 'load_minus_z',
                'additional_load_x', 'additional_load_y', 'additional_load_z',
                'move_plus_x', 'move_plus_y', 'move_plus_z', 'move_minus_x', 'move_minus_y', 'move_minus_z',
                'estimated_state',
            ),
        }),
        (_('Входные параметры пружины'), {'fields': ('minimum_spring_travel', 'tmp_spring')}),
        (_('Данные трубы'), {
            'fields': (
                'pipe_location', 'pipe_direction', 'ambient_temperature', 'nominal_diameter',
                'outer_diameter_special', 'insulation_thickness', 'span', 'clamp_material',
                'insert', 'pipe_mount', 'top_mount'
            ),
        }),
        (_('Технические требования'), {
            'fields': ('technical_requirements', 'full_technical_requirements')
        }),
        (_('Данные с CRM'), {
            'fields': (
                'crm_id', 'crm_mark_cont', 'work_type',
            )
        }),
        (_('Параметры подбора'), {
            'fields': ('selection_params',),
        }),
    )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'number', 'organization', 'owner', 'status', 'load_unit', 'move_unit', 'temperature_unit', 'created',
        'modified',
    )
    list_display_links = ('id', 'number')
    list_filter = (
        'status', 'load_unit', 'move_unit', 'temperature_unit',
        ('created', DateTimeRangeFilterBuilder()),
        ('modified', DateTimeRangeFilterBuilder()),
    )
    search_fields = (
        'id', 'number', 'organization__name', 'owner_email', 'owner__last_name', 'owner__first_name',
        'owner__middle_name',
    )
    readonly_fields = ('id', 'created', 'modified')
    fieldsets = (
        (None, {'fields': ('id', 'number', 'organization', 'owner', 'status')}),
        (_('Единицы измерения проекта'), {'fields': ('load_unit', 'move_unit', 'temperature_unit')}),
        (_('Важные даты'), {'fields': ('created', 'modified')}),
    )
    inlines = (ProjectItemInline,)


@admin.register(ProjectItem)
class ProjectItemAdmin(admin.ModelAdmin):
    list_display = ["id", "project", "position_number", "count"]
    list_display_links = ["id"]
    list_filter = ["project"]
    autocomplete_fields = ["project", "original_item", "nominal_diameter", "clamp_material", "pipe_mount", "top_mount"]
    search_fields = ["id", "project_id"]
    # inlines = [AuditLogInline]

    # def get_inline_instances(self, request, obj=None):
    #     inline_instances = super().get_inline_instances(request, obj)

    #     if obj:
    #         for inline in inline_instances:
    #             if isinstance(inline, AuditLogInline):
    #                 inline.model = LogEntry
    #                 inline.queryset = LogEntry.objects.filter(
    #                     content_type__app_label="ops",
    #                     content_type__model="projectitem",
    #                     object_id=obj.id
    #                 ).select_related("actor")
        
    #     return inline_instances


@admin.register(FieldSet)
class FieldSetAdmin(admin.ModelAdmin):
    list_display = ('id', 'icon', 'name', 'label')
    list_display_links = ('id', 'name', 'label')
    search_fields = ('name', 'label')
    readonly_fields = ('id',)
    fieldsets = (
        (None, {'fields': ('id', 'icon', 'name', 'label_ru', 'label_en')}),
    )


class AttributeInline(nested_admin.NestedStackedInline):
    model = Attribute
    extra = 0

    class Media:
        js = ('ops/attribute_inline.js',)


class VariantAdminForm(forms.ModelForm):
    class Meta:
        model = Variant
        fields = '__all__'
        widgets = {
            'marking_template': MarkingTemplateWidget(attrs={'style': 'width: 80em'}),
        }


class BaseCompositionInline(nested_admin.NestedTabularInline):
    model = BaseComposition
    extra = 0
    fk_name = 'base_parent_variant'

    def get_max_num(self, request, obj=None, **kwargs):
        # Добавить состав можно только для сборочных единиц или готовых изделий
        max_num = 100
        if obj and (obj.detail_type.category == DetailType.DETAIL or obj.detail_type.category == DetailType.BILLET):
            return 0
        return max_num


class VariantInline(nested_admin.NestedStackedInline):
    model = Variant
    extra = 0
    inlines = (BaseCompositionInline, AttributeInline)
    form = VariantAdminForm
    template = 'admin/ops/variant/stacked.html'
    fieldsets = (
        (
            None, {
                'fields': (
                    'name', 'sketch', 'sketch_coords', 'subsketch', 'subsketch_coords', 'marking_template',
                    'series',
                )
            }
        ),
        (
            _('Формулы'),
            {'fields': ('formula_weight', 'formula_height', 'formula_chain_weight', 'formula_spring_block')}),
    )


@admin.register(DetailType)
class DetailTypeAdmin(nested_admin.NestedModelAdmin):
    list_display = ('id', 'product_family', 'designation', 'category', 'branch_qty')
    list_display_links = ('id',)
    list_filter = ('category',)
    search_fields = ('id', 'product_family__name', 'designation')
    autocomplete_fields = ('product_family',)
    readonly_fields = ('id',)
    fieldsets = (
        (None,
         {
             'fields': (
                 'id', 'product_family', 'name', 'designation', 'category', 'branch_qty', 'technical_requirements',
             )
         }),
        ('ERP', {'fields': ('short_name_to_erp',)})
    )
    inlines = (AttributeInline, VariantInline)


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ['id', 'detail_type', 'name', 'marking_template']
    list_display_links = ['id', 'name']
    list_filter = ['detail_type']
    search_fields = ['detail_type__designation', 'name', 'marking_template']
    autocomplete_fields = ['detail_type']
    inlines = [AttributeInline, BaseCompositionInline]


class ItemChildInline(admin.TabularInline):
    model = ItemChild
    extra = 0
    fk_name = 'parent'
    autocomplete_fields = ['child']


class ItemAdminForm(forms.ModelForm):
    def clean(self):
        if 'name' in self.changed_data:
            self.instance.name_manual_changed = True

        return self.cleaned_data

    class Meta:
        model = Item
        fields = '__all__'


class AsyncImportForm(forms.Form):
    file = forms.FileField(label='Файл импорта (CSV или XLSX)')
    file_format = forms.ChoiceField(
        choices=(('xlsx', 'XLSX'), ('csv', 'CSV')),
        label='Формат файла'
    )
    category = forms.CharField(label='Category')
    designation = forms.CharField(label='Designation')
    is_dry_run = forms.BooleanField(label='Dry run', required=False, initial=False)


@admin.register(Item)
class ItemAdmin(ImportMixin, admin.ModelAdmin):
    list_display = (
        'id', 'inner_id', 'type', 'variant', 'name', 'marking', 'weight', 'height', 'material', 'author', 'erp_id',
        'erp_nomspec', 'created', 'modified',
    )
    list_display_links = ('id', 'inner_id', 'name')
    list_filter = (
        'type', 'variant', 'material',
        ('created', DateTimeRangeFilterBuilder()),
        ('modified', DateTimeRangeFilterBuilder()),
    )
    search_fields = (
        'id', 'inner_id', 'name', 'marking',
        'author__email', 'author__last_name', 'author__first_name', 'author__middle_name',
    )

    autocomplete_fields = ('type', 'variant', 'material', 'author')
    readonly_fields = ('id', 'inner_id', 'type', 'variant', 'marking', 'marking_errors', 'created', 'modified')

    fieldsets = (
        (None, {'fields': ('id', 'inner_id', 'name', 'marking', 'marking_errors', 'comment', 'author')}),
        (_('Тип детали и исполнение'), {'fields': ('type', 'variant')}),
        (_('Параметры'),
         {'fields': ('weight', 'weight_errors', 'height', 'height_errors', 'chain_weight', 'chain_weight_errors',
                     'spring_block_length', 'spring_block_length_errors', 'parameters', 'parameters_errors',
                     'material')}),
        (_('Синхронизация с ERP'), {'fields': ('erp_id', 'erp_nomspec')}),
        (_('Важные даты'), {'fields': ('created', 'modified')}),
    )
    add_fieldsets = (
        (None, {
            'fields': ('type', 'variant', 'name', 'weight', 'height', 'material', 'parameters', 'author'),
        }),
    )
    form = ItemAdminForm
    inlines = [ItemChildInline]

    def get_resource_classes(self, request):
        classes = get_resources_list()
        return classes

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets

        return super().get_fieldsets(request, obj=obj)

    def get_readonly_fields(self, request, obj=None):
        if not obj:
            return []

        return super().get_readonly_fields(request, obj=obj)

    import_template_name = 'admin/import_export/import.html'
    import_form_class = AsyncImportForm

    def get_import_form(self, request):
        return self.import_form_class

    def get_queryset(self, request):
        qs = super().get_queryset(request).filter(deleted_at__isnull=True)
        return qs

    def import_action(self, request, *args, **kwargs):
        """
        Асинхронный импорт через админку: создаём Task + TaskAttachment и запускаем Celery-задачу.
        """
        Form = self.get_import_form(request)

        if request.method == 'POST':
            form = Form(request.POST, request.FILES)
            if form.is_valid():
                cd = form.cleaned_data
                fmt = cd['file_format']
                category = cd['category']
                designation = cd['designation']
                uploaded = cd['file']
                dry_run = cd['is_dry_run']

                # проверяем формат
                if fmt not in ('xlsx', 'csv'):
                    self.message_user(request, 'Неподдерживаемый формат файла', level=messages.ERROR)
                    return redirect(request.get_full_path())

                # убеждаемся, что ресурс существует
                resource_name = f'{category}_{designation}'
                resources_list = get_resources_list()
                if not any(r.__name__ == resource_name for r in resources_list):
                    self.message_user(request, f'Ресурс "{resource_name}" не найден', level=messages.ERROR)
                    return redirect(request.get_full_path())
                # создаём задачу в БД
                task = Task.objects.create(
                    owner=request.user,
                    type=TaskType.IMPORT,
                    dry_run=dry_run,
                    parameters={
                        'category': category,
                        'designation': designation,
                        'file_format': fmt,
                    },
                )
                # прикрепляем файл
                TaskAttachment.objects.create(
                    task=task,
                    slug='imported_file',
                    file=uploaded,
                )
                # запускаем celery-задачу
                process_import_task(task.id)

                self.message_user(
                    request,
                    f'Импорт запущен асинхронно (Task #{task.id})',
                    level=messages.SUCCESS
                )
                return redirect(request.get_full_path())

        else:
            form = Form()

        context = dict(
            self.admin_site.each_context(request),
            title='Импорт данных',
            form=form,
            opts=self.model._meta,
            app_label=self.model._meta.app_label,
        )
        return TemplateResponse(request, self.import_template_name, context)


class ERPSyncLogInline(admin.TabularInline):
    model = ERPSyncLog
    extra = 0
    readonly_fields = ('created_at',)
    autocomplete_fields = ('erp_sync',)

    def has_add_permission(self, request, obj):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ERPSync)
class ERPSyncAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'instance', 'status', 'author', 'created_at', 'start_at', 'finished_at')
    list_filter = ('status', 'type', 'created_at', 'author')
    search_fields = ('item__name', 'project__number', 'author__username')
    autocomplete_fields = ('item', 'project', 'author')
    readonly_fields = ('created_at',)
    inlines = [ERPSyncLogInline]

    @admin.display(description=_('Объект'))
    def instance(self, obj):
        return obj.get_instance()
