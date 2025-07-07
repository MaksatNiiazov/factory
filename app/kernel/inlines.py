from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from auditlog.models import LogEntry


class AuditLogInline(GenericTabularInline):
    """
    Вспомогательный класс для отображения записей аудита (LogEntry) в виде табличной встроенной формы в административной панели Django.
    """

    model = LogEntry
    ct_field = "content_type"
    ct_fk_field = "object_pk"
    fields = ["action", "timestamp", "actor", "changes"]
    readonly_fields = ["action", "timestamp", "actor", "changes"]
    extra = 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("actor")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
