from django import forms
from django.contrib import admin
from django.contrib.auth.forms import (
    UserChangeForm as DefaultUserChangeForm,
    UserCreationForm as DefaultUserCreationForm,
)
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin, GroupAdmin as DefaultGroupAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from kernel.models import User, Organization, ApiToken

admin.site.index_title = _('Applications')
admin.site.site_header = _('OPS Administration')
admin.site.site_title = _('OPS Administration')


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'external_id')
    list_display_links = ('id', 'name')
    search_fields = ('id', 'name', 'external_id')


class UserChangeForm(DefaultUserChangeForm):
    class Meta:
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = self.fields.get("user_permissions")

        if f:
            f.label_from_instance = lambda p: p.name


class UserCreationForm(DefaultUserCreationForm):
    class Meta:
        model = User
        fields = ('email',)


@admin.register(User)
class UserAdmin(DefaultUserAdmin):
    list_display = ('id', 'email', 'full_name', 'organization', 'status_f', 'is_active')
    list_display_links = ('id', 'email', 'full_name')
    list_filter = ('status', 'organization', 'is_active')
    search_fields = ('id', 'email', 'last_name', 'first_name', 'middle_name', 'organization__name', 'crm_login')
    autocomplete_fields = ('organization',)
    ordering = ('email',)
    filter_horizontal = ('user_permissions',)

    @admin.display(description=_('ФИО'), ordering='last_name')
    def full_name(self, instance):
        return instance.full_name

    @admin.display(description=_('Статус'), ordering='status')
    def status_f(self, instance):
        status = instance.get_status_display()

        if instance.status == User.INTERNAL_USER and instance.crm_login:
            status += f' ({instance.crm_login})'

        return status

    fieldsets = (
        (None, {'fields': ('email', 'organization', 'status', 'crm_login', 'password')}),
        (_('Personal info'), {'fields': ('last_name', 'first_name', 'middle_name')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Техническая информация'), {'fields': ('ui_config',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'organization', 'password1', 'password2'),
        }),
    )

    form = UserChangeForm
    add_form = UserCreationForm

    class Media:
        css = {
            'all': ('custom_admin.css',),
        }

class GroupChangeForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = self.fields.get("permissions")

        if f:
            f.label_from_instance = lambda p: p.name

class GroupAdmin(DefaultGroupAdmin):
    filter_horizontal = ('permissions',)

    form = GroupChangeForm

    class Media:
        css = {
            'all': ('custom_admin.css',),
        }


admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'token')
    list_display_links = ('id',)
    search_fields = ('user__email', 'user__last_name', 'user__first_name', 'user__middle_name', 'token')
    autocomplete_fields = ('user',)
