from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from kernel.api.filter_backends import MappedOrderingFilter
from kernel.api.permissions import ActionPermission
from kernel.api.views import CustomModelViewSet
from taskmanager.api.filters import TaskFilter
from taskmanager.api.serializers import TaskSerializer
from taskmanager.models import Task


class TaskViewSet(CustomModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [ActionPermission]
    filter_backends = [DjangoFilterBackend, MappedOrderingFilter, SearchFilter]
    filterset_class = TaskFilter

    ordering_fields = ['id', 'owner', 'type', 'dry_run', 'status']
    search_fields = ['id', 'owner__email', 'owner__last_name', 'owner__first_name', 'owner__middle_name']