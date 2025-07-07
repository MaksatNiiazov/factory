from django.contrib import admin

from taskmanager.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'owner', 'type', 'dry_run', 'status', 'created', 'modified']
    list_display_links = ['id']
    list_filter = ['type', 'dry_run', 'status', 'created', 'modified']
    search_fields = ['id', 'owner__email', 'owner__last_name', 'owner__first_name', 'owner__middle_name']
    autocomplete_fields = ['owner']