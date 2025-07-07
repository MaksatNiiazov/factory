from django.db.models import OuterRef, Q, Exists, QuerySet

from kernel.mixins import SoftDeleteQuerySet, SoftDeleteManager, AllObjectsManager


class BaseCompositionQuerySet(SoftDeleteQuerySet):
    def for_variant(self, variant) -> QuerySet:
        """
        Возвращает базовые составы (BaseComposition) для указанного исполнения (Variant).

        :param variant: Исполнение (Variant), для которого выбираются базовые составы.
        :reurn: QuerySet с BaseComposition, где base_parent_variant соответствует исполнению.
        """
        return self.filter(base_parent_variant=variant)


class BaseCompositionManagerMixin:
    def for_variant(self, variant) -> QuerySet:
        """
        Возвращает базовые составы (BaseComposition) для указанного исполнения (Variant).

        Прокси-метод, вызывающий соответствующий метод QuerySet.
        """
        return self.get_queryset().for_variant(variant)


class BaseCompositionSoftDeleteManager(BaseCompositionManagerMixin, SoftDeleteManager):
    queryset = BaseCompositionQuerySet


class BaseCompositionAllObjectsManager(BaseCompositionManagerMixin, AllObjectsManager):
    queryset = BaseCompositionQuerySet


class AttributeQuerySet(SoftDeleteQuerySet):
    def for_detail_type(self, detail_type) -> QuerySet:
        """
        Возвращает базовые атрибуты для указанного типа детали (DetailType).

        :param detail_type: Тип детали, для которого выбираются атрибуты.
        :return: QuerySet с атрибутами, связанными с данным типом детали.
        """
        return self.filter(detail_type=detail_type)

    def for_variant(self, variant) -> QuerySet:
        """
        Возвращает атрибуты для указанного исполнения (Variant)

        В выборку входят как конкретные атрибуты исполнения, так и базовые атрибуты типа детали.
        Если у исполнения и типа детали есть атрибуты с одинаковым наименованием,
        выбирается только атрибут исполнения.

        :param variant: Исполнение (Variant), для которого выбираются атрибуты.
        :return: QuerySet с атрибутами с учётом приоритетов.
        """
        from ops.models import Attribute

        variant_name_subq = Attribute.objects.filter(variant=variant, name=OuterRef('name'))

        return self.filter(
            Q(detail_type=variant.detail_type) | Q(variant=variant)
        ).annotate(
            has_variant=Exists(variant_name_subq)
        ).filter(
            Q(variant=variant) | Q(has_variant=False)
        )


class AttributeManagerMixin:
    def for_detail_type(self, detail_type) -> QuerySet:
        """
        Возвращает базовые атрибуты для указанного типа детали (DetailType).

        Прокси-метод, вызывающий соответствующий метод QuerySet.
        """
        return self.get_queryset().for_detail_type(detail_type)

    def for_variant(self, variant) -> QuerySet:
        """
        Возвращает атрибуты для указанного исполнения (Variant).

        Прокси-метод, вызывающий соответствующий метод QuerySet.
        """
        return self.get_queryset().for_variant(variant)


class AttributeSoftDeleteManager(AttributeManagerMixin, SoftDeleteManager):
    queryset = AttributeQuerySet


class AttributeAllObjectsManager(AttributeManagerMixin, AllObjectsManager):
    queryset = AttributeQuerySet


class ItemQuerySet(SoftDeleteQuerySet):
    def generate_marking(self):
        for item in self:
            item.marking, item.marking_errors = item.generate_marking()

            if not item.name_manual_changed:
                item.name = item.generate_name()

        self.model.objects.bulk_update(self, fields=('marking', 'marking_errors', 'name'))

        return self

    def update_weight(self):
        for item in self:
            item.update_weight(commit=False)

        self.model.objects.bulk_update(self, fields=('weight', 'weight_errors'))

    def update_height(self):
        for item in self:
            item.update_height(commit=False)

        self.model.objects.bulk_update(self, fields=('height', 'height_errors'))


class ItemManager(SoftDeleteManager):
    queryset = ItemQuerySet

    def generate_marking(self):
        return self.get_queryset().generate_marking()

    def update_weight(self):
        return self.get_queryset().update_weight()

    def update_height(self):
        return self.get_queryset().update_height()
