from django.db.models import F, Manager, QuerySet, Q
from django.db.models.functions import Abs

from kernel.mixins import SoftDeleteQuerySet, SoftDeleteManager, AllObjectsManager

from catalog.choices import Standard


class PipeDiameterQuerySet(SoftDeleteQuerySet):
    def closest_by_size_and_standard(self, dn_size: float, standard: Standard) -> QuerySet:
        """
        Возвращает QuerySet с PipeDiameter, отсортированными по близости размера к dn_size
        в рамках заданного стандарта.

        :param dn_size: Номинаьлный диаметр для поиска ближайшего размера.
        :param standard: Стандарт, в рамках которого производится поиск.
        :return: QuerySet с PipeDiameter, отсортированными по разнице с dn_size (от меньшей к большей).
        """
        return self.filter(
            standard=standard
        ).annotate(
            diff=Abs(F('size') - dn_size)
        ).order_by('diff')


class PipeDiameterManagerMixin:
    def closest_by_size_and_standard(self, dn_size: float, standard: Standard = Standard.RF):
        """
        Возвращает ближайший по размеру PipeDiameter для заданного стандарта

        :param dn_size: Номинальный диаметр для поиска ближайшего размера.
        :param standard: Стандарт (по умолчанию Standard.RF)
        :return: PipeDiameter с ближайшим размером, либо None если подходящих нет.
        """
        return self.get_queryset().closest_by_size_and_standard(dn_size, standard).first()


class PipeDiameterSoftDeleteManager(PipeDiameterManagerMixin, SoftDeleteManager):
    queryset = PipeDiameterQuerySet


class PipeDiameterAllObjectsManager(PipeDiameterManagerMixin, AllObjectsManager):
    queryset = PipeDiameterQuerySet


class ClampMaterialCoefficientQuerySet(QuerySet):
    def for_temperature(self, temperature: int) -> QuerySet:
        """
        Возвращает QuerySet с ClampMaterialCoefficient, которые подходят для заданной температуры.

        :param temperature: Температура, для которой нужно найти коэффициенты.
        :return: QuerySet с подходящими ClampMaterialCoefficient.
        """
        return self.filter(
            Q(temperature_from__isnull=True, temperature_to__gte=temperature)
            | Q(temperature_from__lte=temperature, temperature_to__gte=temperature)
            | Q(temperature_from__lte=temperature, temperature_to__isnull=True)
        )


class ClampMaterialCoefficientManager(Manager):
    def get_queryset(self) -> ClampMaterialCoefficientQuerySet:
        return ClampMaterialCoefficientQuerySet(self.model, using=self._db)

    def for_temperature(self, temperature: int) -> QuerySet:
        """
        Возвращает ClampMaterialCoefficient для заданной температуры.

        :param temperature: Температура, для которой нужно найти коэффициент.
        :return: QuerySet с подходящими ClampMaterialCoefficient.
        """
        return self.get_queryset().for_temperature(temperature)
