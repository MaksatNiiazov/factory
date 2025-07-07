from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.db import models
from django_extensions.db.models import TimeStampedModel

from taskmanager.choices import TaskType, TaskStatus, TaskResultType

User = get_user_model()


class Task(TimeStampedModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks', verbose_name=_('Владелец'))
    type = models.CharField(max_length=TaskType.get_max_length(), choices=TaskType.choices, verbose_name=_('Тип'))
    dry_run = models.BooleanField(default=False, blank=True, verbose_name=_('Dry Run'))
    parameters = models.JSONField(null=True, blank=True, verbose_name=_('Параметры'))
    status = models.CharField(
        max_length=TaskStatus.get_max_length(), choices=TaskStatus.choices, default=TaskStatus.NEW,
        verbose_name=_('Статус'),
    )
    status_details = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f'Task {self.id} ({self.get_type_display()})'


class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    slug = models.SlugField()
    file = models.FileField(upload_to='task_attachments/')

    class Meta:
        unique_together = ['task', 'slug']

    def __str__(self):
        return f'Attachment {self.slug} or Task {self.task.id}'


class TaskResult(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='results')
    slug = models.SlugField()
    type = models.CharField(
        max_length=TaskResultType.get_max_length(), choices=TaskResultType.choices, verbose_name=_('Тип'),
    )
    result_file = models.FileField(upload_to='task_results/', null=True, blank=True)
    result_text = models.TextField(null=True, blank=True)
    result_json = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = ['task', 'slug']

    @property
    def result(self):
        if self.type == TaskResultType.FILE:
            return self.result_file
        if self.type == TaskResultType.TEXT:
            return self.result_text
        if self.type == TaskResultType.JSON:
            return self.result_json
