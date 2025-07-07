from rest_flex_fields import FlexFieldsModelSerializer

from kernel.api.base import CleanSerializerMixin
from kernel.api.serializers import UserSerializer
from taskmanager.models import Task, TaskAttachment, TaskResult


class TaskAttachmentSerializer(CleanSerializerMixin, FlexFieldsModelSerializer):
    class Meta:
        model = TaskAttachment
        fields = ['id', 'task', 'slug', 'file']
        expandable_fields = {
            'task': ('taskmanager.api.serializers.TaskSerializer', {'many': True}),
        }


class TaskResultSerializer(CleanSerializerMixin, FlexFieldsModelSerializer):
    class Meta:
        model = TaskResult
        fields = ['id', 'task', 'slug', 'type', 'result']
        expandable_fields = {
            'task': ('taskmanager.api.serializers.TaskSerializer', {'many': True}),
        }


class TaskSerializer(CleanSerializerMixin, FlexFieldsModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'owner', 'type', 'parameters', 'status', 'status_details', 'attachments', 'results']
        expandable_fields = {
            'owner': UserSerializer,
            'attachments': (TaskAttachmentSerializer, {'many': True}),
            'results': (TaskResultSerializer, {'many': True}),
        }
