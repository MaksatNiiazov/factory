from rest_framework.permissions import BasePermission

from kernel.api.permissions import ActionPermission

DEFAULT_OWNER_FIELD = 'owner'


class OwnActionPermission(ActionPermission):
    """
    Пользователь может взаимодействовать с объектами, в котором он владелец или автор, если присутствует такие разрешения:
    list|retrieve - app_label.view_own_model_name
    create - app_label.add_own_model_name
    update - app_label.change_own_model_name
    destroy - app_label.delete_own_model_name
    """
    perms_map = {
        'list': ['%(app_label)s.view_own_%(model_name)s'],
        'retrieve': ['%(app_label)s.view_own_%(model_name)s'],
        'create': ['%(app_label)s.add_own_%(model_name)s'],
        'update': ['%(app_label)s.change_own_%(model_name)s'],
        'partial_update': ['%(app_label)s.change_own_%(model_name)s'],
        'destroy': ['%(app_label)s.delete_own_%(model_name)s'],
    }

    owner_field = DEFAULT_OWNER_FIELD

    @classmethod
    def build(cls, owner_field=None):
        klass = type("OwnActionPermission", (OwnActionPermission,), {
            "owner_field": owner_field or DEFAULT_OWNER_FIELD,
        })
        return klass

    def get_owner(self, obj, owner_field=None):
        owner_field = owner_field or self.owner_field

        if not obj:
            return None

        if '__' in owner_field:
            field, *fields = self.owner_field.split('__')

            value = getattr(obj, field, None)
            owner_field = '__'.join(fields)

            return self.get_owner(value, owner_field=owner_field)

        return getattr(obj, owner_field, None)

    def has_object_permission(self, request, view, obj):
        owner = self.get_owner(obj)

        if not owner:
            return False

        if owner != request.user:
            return False

        return self.has_permission(request, view)


class ProjectItemPermission(ActionPermission):
    perms_map = dict(
        ActionPermission.perms_map,
        save_as=['%(app_label)s.change_%(model_name)s'],
        set_selection=['%(app_label)s.change_%(model_name)s'],
        update_item=['%(app_label)s.change_%(model_name)s'],
        calculate=['%(app_label)s.change_%(model_name)s'],
        get_selection_options=['%(app_label)s.view_%(model_name)s'],
    )


class ClonePermission(BasePermission):
    """
    Для клонирования объекта требуется разрешения на добавление объекта.
    """

    def has_permission(self, request, view):
        if view.action in ['clone']:
            if request.user.has_perm('ops.add_detailtype'):
                return True

        return False


class ERPSyncPermission(BasePermission):
    """
    Для синхронизации с ERP требуется разрешения:

    - Может синхронизировать изделия/детали/сборочные единицы в ERP
    """

    def has_permission(self, request, view):
        if view.action in ['sync_erp']:
            if request.user.has_perm('ops.sync_item_erp'):
                return True

        return False


class ProjectERPSyncPermission(BasePermission):
    """
    Для синхронизации проекта в ERP требуется разрешение:

    - Может синхронизировать проект в ERP
    """

    def has_permission(self, request, view):
        if view.action in ['sync_to_erp']:
            if request.user.has_perm('ops.sync_project_erp'):
                return True

        return False


class ImportFromCRMPermission(BasePermission):
    """
    Для импорта с CRM требуется разрешение:

    - Может импортировать проект с CRM
    """

    def has_permission(self, request, view):
        if view.action in ['import_from_crm']:
            if request.user.has_perm('ops.import_project_crm'):
                return True

        return False
