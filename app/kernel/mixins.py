from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class MaxLengthMixin:
    @classmethod
    def get_max_length(cls) -> int:
        return max(len(choice.value) for choice in cls)


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        # метим все записи в этом кверисете
        return super().update(deleted_at=timezone.now())

    def hard_delete(self):
        # настоящие delete()
        return super().delete()

    def alive(self):
        # только не удалённые
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        # только мягко удалённые
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    """
    По-умолчанию скрывает записи с deleted_at != None.
    """
    queryset = SoftDeleteQuerySet

    def get_queryset(self):
        return self.queryset(self.model, using=self._db).alive()

    def hard_delete(self):
        return self.get_queryset().hard_delete()

    def deleted(self):
        return self.get_queryset().deleted()


class AllObjectsManager(models.Manager):
    """
    Возвращает все записи, включая мягко удалённые.
    """
    queryset = SoftDeleteQuerySet

    def get_queryset(self):
        return self.queryset(self.model, using=self._db)


class SoftDeleteModelMixin(models.Model):
    """
    Абстрактная модель для мягкого удаления.

    Достаточно наследоваться от неё:
        class MyModel(SoftDeleteModel):
            …

    и всё soft-delete ≡ работает.
    """
    deleted_at = models.DateTimeField(
        _('Дата удаления'),
        null=True,
        blank=True,
        editable=False,
    )

    # дефолтный менеджер — только «живые» записи
    objects = SoftDeleteManager()
    # менеджер для всех записей
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        # метим конкретный объект
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        # если нужно разово удалить физически
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        # снять метку удаления
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])
