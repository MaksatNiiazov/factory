from collections import defaultdict
from typing import Any, Dict, List, Optional

from catalog.models import ProductFamily
from ops.choices import AttributeType, AttributeCatalog
from ops.models import Attribute, Variant


class BaseSelectionAvailableOptions:
    @classmethod
    def get_default_params(cls):
        params = {
            'product_class': None,
            'product_family': None,
        }
        return params

    def __init__(self, project_item):
        self.project_item = project_item

        params = project_item.selection_params

        if not params:
            params = self.get_default_params()

        self.params = params
        self.debug = []

    def get_dn_attribute(self, attributes: List[Attribute]) -> Optional[Attribute]:
        """
        Возвращает атрибут с типом 'Номинальный диаметр' (DN) из переданного списка атрибутов.
        """
        found_dn = next(
            (
                attribute for attribute in attributes
                if attribute.type == AttributeType.CATALOG and attribute.catalog == AttributeCatalog.NOMINAL_DIAMETER
            ), None
        )
        return found_dn

    def get_pipe_diameter_attribute(self, attributes: List[Attribute]) -> Optional[Attribute]:
        """
        Возвращает атрибут с типом "Номинальный диаметр трубы" (PipeDiameter) из переданного списка атрибутов.
        """
        found_pipe_diameter = next(
            (
                attribute for attribute in attributes
                if attribute.type == AttributeType.CATALOG and attribute.catalog == AttributeCatalog.PIPE_DIAMETER
            ), None
        )
        return found_pipe_diameter

    def get_load_group_attribute(self, attributes: List[Attribute]) -> Optional[Attribute]:
        """
        Возвращает атрибут с типом 'Нагрузочная группа' из переданного списка атрибутов.
        """
        found_load_group = next(
            (
                attribute for attribute in attributes
                if attribute.type == AttributeType.CATALOG and attribute.catalog == AttributeCatalog.LOAD_GROUP
            ), None
        )
        return found_load_group

    def get_material_attribute(self, attributes: List[Attribute]) -> Optional[Attribute]:
        found_material = next(
            (
                attribute for attribute in attributes
                if attribute.type == AttributeType.CATALOG and attribute.catalog == AttributeCatalog.MATERIAL
            ), None
        )
        return found_material

    def get_attribute_by_catalog(self, attributes: List[Attribute], catalog: str) -> Optional[Attribute]:
        """
        Возвращает атрибут из списка по значению 'Каталог' (catalog),
        """
        found_attribute = next(
            (
                attribute for attribute in attributes
                if attribute.type == AttributeType.CATALOG and attribute.catalog == catalog
            ), None
        )
        return found_attribute

    def get_attribute_by_usage(self, attributes: List[Attribute], usage: str) -> Optional[Attribute]:
        """
        Возвращает атрибут из списка по значению 'Использование атрибута' (usage),
        в соответствии со справочником AttributeUsageChoices.
        """
        found_attribute = next(
            (attribute for attribute in attributes if attribute.usage == usage),
            None,
        )
        return found_attribute

    def get_product_family(self) -> Optional[ProductFamily]:
        """
        Возвращает выбранное семейство изделия по идентификатору в параметрах,
        либо None, если семейство не выбрано.
        """
        if not self.params['product_family']:
            return None

        return ProductFamily.objects.get(id=self.params['product_family'])

    def get_variant(self):
        variant_id = self.params['suitable_variant']

        if not variant_id:
            return None

        return Variant.objects.get(id=variant_id)
    
    def get_specification(self, variant: Variant, items) -> List[Dict[str, Any]]:
        if not variant:
            self.debug.append('#Спецификация: Variant не выбран.')
            return []

        items = list(items)
        if not items:
            self.debug.append('#Спецификация: Список Item пуст.')
            return []

        base_compositions = variant.get_base_compositions()

        specification: List[Dict[str, Any]] = [{
            'detail_type': bc.base_child_id,
            'variant': bc.base_child_variant_id,
            'item': None,
            'position': bc.position,
            'material': None,
            'count': bc.count,
        } for bc in base_compositions]

        rows_by_variant = defaultdict(list)
        rows_by_dt = defaultdict(list)

        for row in specification:
            if row['variant'] is not None:
                rows_by_variant[row['variant']].append(row)
            rows_by_dt[row['detail_type']].append(row)

        for it in items:
            candidates = rows_by_variant.get(it.variant_id, [])
            if not any(r for r in candidates if r['item'] is None):
                candidates = rows_by_dt.get(it.type_id, [])

            target_row = next((r for r in candidates if r['item'] is None), None)
            if target_row:
                target_row['item'] = it.id
                target_row['material'] = it.material_id
                if target_row in rows_by_variant.get(it.variant_id, []):
                    rows_by_variant[it.variant_id].remove(target_row)
                if target_row in rows_by_dt.get(it.type_id, []):
                    rows_by_dt[it.type_id].remove(target_row)

        return specification

    def get_available_options(self):
        raise NotImplementedError
