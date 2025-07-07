from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import DjangoModelPermissions, BasePermission


class ActionPermission(DjangoModelPermissions):
    """
    Использует разрешения (permissions) с модели:
    list|retrieve - app_label.view_model_name
    create - app_label.add_model_name
    update - app_label.change_model_name
    destroy - app_label.delete_model_name
    """
    perms_map = {
        'list': ['%(app_label)s.view_%(model_name)s'],
        'retrieve': ['%(app_label)s.view_%(model_name)s'],
        'create': ['%(app_label)s.add_%(model_name)s'],
        'update': ['%(app_label)s.change_%(model_name)s'],
        'partial_update': ['%(app_label)s.change_%(model_name)s'],
        'destroy': ['%(app_label)s.delete_%(model_name)s'],
    }

    def get_required_permissions(self, action, model_cls):
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name,
        }

        if action not in self.perms_map:
            raise PermissionDenied(action)

        return [perm % kwargs for perm in self.perms_map[action]]

    def get_model(self, queryset):
        return queryset.model

    def has_permission(self, request, view):
        if getattr(view, '_ignore_model_permissions', False):
            return True

        if not request.user or (not request.user.is_authenticated and self.authenticated_users_only):
            return False

        if request.user.is_superuser:
            return True

        queryset = self._queryset(view)
        perms = self.get_required_permissions(view.action, self.get_model(queryset))

        return request.user.has_perms(perms)


class AnyOneCanViewPermission(BasePermission):
    """
    Пользователи без авторизации, могут видеть список или конкретный элемент без ограничении
    """

    def has_permission(self, request, view):
        if view.action in ('list', 'retrieve'):
            return True

        return False


class AnyOneCanViewChoicesPermission(BasePermission):
    """
    Пользователи без авторизации, могут видеть список choices у полей без ограничении
    """

    def has_permission(self, request, view):
        method = request.method.lower()
        view_set = getattr(view, method, None)

        if view_set and getattr(view_set, 'is_choices_action', False):
            return True

        return False


class AuthorizationPermission(BasePermission):
    """
    Для API-точки `/api/users/login/`, не требуется авторизация
    """

    def has_permission(self, request, view):
        if view.action == 'login':
            return True

        return False


class CurrentUserInfoPermission(BasePermission):
    """
    Показать данные текущего авторизованного пользователя, в API-точке `/api/users/{user_id}/` или `/api/users/me/`.
    """

    def has_permission(self, request, view):
        if view.action != "retrieve":
            return False

        if not request.user.is_authenticated:
            return False

        user_id = view.kwargs.get("pk")

        if user_id == "me" or user_id == request.user.id:
            return True

        return False


class CurrentUserCanChangePermission(BasePermission):
    """
    Пользователь сам может поменять некоторых данные через API-точки:

    - `/api/users/set_item_table_columns/`
    - `/api/users/set_locale/`
    - `/api/users/set_timezone/`
    """

    def has_permission(self, request, view):
        if view.action not in ['set_item_table_columns', 'set_locale', 'set_timezone']:
            return False

        if not request.user.is_authenticated:
            return False

        user_id = view.kwargs.get("pk")

        if user_id == "me" or user_id == request.user.id:
            return True

        return False


class CurrentUserRequiredPermission(BasePermission):
    """
    Для API-точки `/api/users/logout/`, требуется быть авторизованным.
    """

    def has_permission(self, request, view):
        if view.action == "logout" and request.user.is_authenticated:
            return True

        return False
