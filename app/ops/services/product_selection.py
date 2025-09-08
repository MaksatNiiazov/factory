import copy
from decimal import Decimal, ROUND_HALF_UP
from math import isfinite
from typing import Optional, List, Dict, Any, Tuple

from django.db.models import Q, QuerySet, OuterRef, Exists, Count, Sum

from catalog.choices import ComponentGroupType, Standard
from catalog.models import (
    ClampMaterialCoefficient, Material, ProductFamily, PipeMountingGroup, PipeMountingRule, PipeDiameter, LoadGroup,
    ComponentGroup,
    SupportDistance, SpringBlockFamilyBinding, CoveringType, ClampSelectionMatrix, ClampSelectionEntry,
)

from ops.api.serializers import VariantSerializer
from ops.choices import AttributeCatalog, AttributeUsageChoices
from ops.loads.utils import get_suitable_loads
from ops.loads.standard_series import MAX_SIZE as MAX_SIZE_STANDARD
from ops.loads.l_series import MAX_SIZE as MAX_SIZE_L
from ops.models import BaseComposition, Item, Variant, Attribute, ProjectItem
from ops.services.base_selection import BaseSelectionAvailableOptions

DEFAULT_MINIMUM_SPRING_TRAVEL = 5
DEFAULT_BRANCH_QTY = 1


class ProductSelectionAvailableOptions(BaseSelectionAvailableOptions):
    @classmethod
    def get_default_params(cls):
        params = {
            'pipe_options': {
                'location': ProjectItem.HORIZONTAL,
                'direction': ProjectItem.X,
                'branch_qty': 1,
                'without_pipe_clamp': False,
            },
            'load_and_move': {
                'load_plus_x': 0,
                'load_plus_y': 0,
                'load_plus_z': 0,
                'load_minus_x': 0,
                'load_minus_y': 0,
                'load_minus_z': 0,
                'additional_load_x': 0,
                'additional_load_y': 0,
                'additional_load_z': 0,
                'test_load_x': 0,
                'test_load_y': 0,
                'test_load_z': 0,
                'move_plus_x': 0,
                'move_plus_y': 0,
                'move_plus_z': 0,
                'move_minus_x': 0,
                'move_minus_y': 0,
                'move_minus_z': 0,
                'estimated_state': 'cold',
            },
            'spring_choice': {
                'minimum_spring_travel': 5,
                'selected_spring': None,
            },
            'pipe_params': {
                'temp1': None,
                'temp2': None,
                'nominal_diameter': None,
                'outer_diameter_special': None,
                'support_distance': None,
                'support_distance_manual': None,
                'insulation_thickness': None,
                'outer_insulation_thickness': None,
                'clamp_material': None,
                'pipe_mounting_group': None,
                'add_to_specification': True,
            },
            "pipe_clamp": {
                "pipe_mount_type": None,
                "pipe_mount": None,
                "top_mount": None,
            },
            'system_settings': {
                'system_height': None,
                'connection_height': None,
                'suspension': None,
                'pipe_axis_height': None,
            },
            'variant': None,
        }
        return params

    def is_clamp_or_shoe(self, attributes: List[Attribute]) -> bool:
        """
        Проверяет, содержит ли список атрибутов параметр 'Номинальный диаметр трубы' (PipeDiameter),
        что означает, что это хомут или башмак.
        """
        found_pipe_diameter = self.get_pipe_diameter_attribute(attributes)
        return bool(found_pipe_diameter)

    def is_lug(self, attributes: List[Attribute]) -> bool:
        """
        Проверяет, содержит ли список атрибутов параметр 'Нагрузочкая группа',
        что означает, что это проушина (lug).
        """
        found_load_group = self.get_load_group_attribute(attributes)
        return bool(found_load_group)

    def is_clamp_or_traverse(self, attributes: List[Attribute]) -> bool:
        """
        Проверяет, содержит ли список атрибутов параметр "Монтажный размер",
        что означает, что это хомут или траверса.
        """
        found_installation_size = self.get_attribute_by_usage(attributes, AttributeUsageChoices.INSTALLATION_SIZE)
        return bool(found_installation_size)

    def get_support_distance(self) -> Optional[float]:
        support_distance = self.params['pipe_params']['support_distance_manual']
        support_id = self.params['pipe_params']['support_distance']

        if support_distance is not None:
            return int(support_distance)

        if support_id is not None:
            support_obj = SupportDistance.objects.filter(id=support_id).first()

            if support_obj:
                return int(support_obj.value)

        return None

    def get_pipe_diameter(self) -> Optional[PipeDiameter]:
        """
        Возвращает объект PipeDiameter по ID из параметров трубы.
        """
        pipe_diameter_id = self.params['pipe_params']['nominal_diameter']

        if not pipe_diameter_id:
            return None
        
        pipe_diameter = PipeDiameter.objects.filter(id=pipe_diameter_id).first()

        if not pipe_diameter:
            self.debug.append(f'Не найден объект PipeDiameter с id={pipe_diameter_id}. Возможно, он был удалён.')
            return None

        return pipe_diameter

    def get_nominal_diameter_size(self) -> Optional[float]:
        """
        Возвращает номинальный диаметр трубы из параметров.
        """
        manual_size = self.params['pipe_params']['outer_diameter_special']

        if manual_size is not None:
            return manual_size
        
        pipe_diameter = self.get_pipe_diameter()

        if pipe_diameter:
            return pipe_diameter.size

        self.debug.append('Не указан номинальный диаметр трубы и не задан специальный диаметр.')
        return None

    def get_load_minus_z(self) -> float:
        load_minus_z = self.params['load_and_move']['load_minus_z']
        return load_minus_z

    def get_temperatures(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Возвращает температуры из параметров трубы.
        """
        temp1 = self.params['pipe_params']['temp1']
        temp2 = self.params['pipe_params']['temp2']
        return temp1, temp2

    def get_selected_clamp_load(self) -> Optional[float]:
        """Возвращает нагрузку выбранного амортизатора/распорки."""
        selected_spring = self.get_selected_spring_block()
        if not selected_spring:
            return None

        variant = selected_spring.get('variant')
        parameters = selected_spring.get('parameters') or {}

        item = selected_spring.get('item')
        if isinstance(item, Item):
            variant = item.variant
            parameters = item.parameters or {}

        if isinstance(variant, Variant):
            attributes = variant.get_attributes()
            load_attr = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LOAD)
            if load_attr:
                value = parameters.get(load_attr.name)
                if value is not None:
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        return None

        return None

    def calculate_load(self) -> Dict[str, Any]:
        """
        Выполняет расчёт подходящих пружинных болков по введённой нагрузке и перемещениям.
        Учитываются: минимальный запас хода, температурное состояние, кол-во пружинных блоков,
        а также испытательные нагрузки (если заданы).

        В зависимости от параметра семейства (has_rod), при подборе учитываются ход штока.
        Возвращает:
        - best_load: наилучший подходящий пружинный блок
        - loads: список всех подхоядщих блоков по обеим сериям
        """
        minimum_spring_travel = self.params['spring_choice']['minimum_spring_travel']
        load_minus_z = self.params['load_and_move']['load_minus_z']
        additional_load_z = self.params['load_and_move']['additional_load_z']

        if additional_load_z:
            load_minus_z += additional_load_z

        move_plus_z = self.params['load_and_move']['move_plus_z']
        move_minus_z = self.params['load_and_move']['move_minus_z']
        estimated_state = self.params['load_and_move']['estimated_state']
        branch_qty = self.params['pipe_options']['branch_qty']

        if branch_qty > 1:
            load_minus_z /= branch_qty

        best_load = None
        loads = []

        test_load_x = self.params['load_and_move'].get('test_load_x')
        test_load_y = self.params['load_and_move'].get('test_load_y')
        test_load_z = self.params['load_and_move'].get('test_load_z')

        product_family = self.get_product_family()

        if not product_family:
            self.debug.append('#Пружинные блоки: Необходимо выбрать семейство изделия.')

        best_load, loads_standard = get_suitable_loads(
            'standard_series',
            MAX_SIZE_STANDARD,
            load_minus_z,
            move_plus_z,
            move_minus_z,
            minimum_spring_travel,
            estimated_state,
            best_load,
            test_load_x=test_load_x,
            test_load_y=test_load_y,
            test_load_z=test_load_z,
            has_rod=product_family.has_rod if product_family else False,
        )
        loads.extend(loads_standard)

        best_load, loads_l = get_suitable_loads(
            'l_series',
            MAX_SIZE_L,
            load_minus_z,
            move_plus_z,
            move_minus_z,
            minimum_spring_travel,
            estimated_state,
            best_load,
            test_load_x=test_load_x,
            test_load_y=test_load_y,
            test_load_z=test_load_z,
            has_rod=product_family.has_rod if product_family else False,
        )
        loads.extend(loads_l)

        return {
            'best_load': best_load,
            'loads': loads,
        }

    def get_pipe_mounting_groups(self) -> QuerySet:
        """
        Возвращает список (QuerySet) групп типов креплений к трубе, подходящих
        под выбранное семейство изделия, направление трубы и количество пружинных блоков.

        Если условия не выполнены (семейство не выбрано или направление не X/Y),
        возвращается пустой QuerySet.
        """
        pipe_mounting_groups = PipeMountingGroup.objects.all()

        if not self.get_product_family() or self.params['pipe_options']['direction'] not in ['x', 'y', 'z']:
            self.debug.append(
                '#Тип крепления к трубе: Не выбран семейство изделии или направление трубы не "X" или "Y" или "Z".'
            )
            return PipeMountingGroup.objects.none()

        rule = PipeMountingRule.objects.filter(
            family=self.get_product_family(),
            num_spring_blocks=self.params['pipe_options']['branch_qty'],
            pipe_direction=self.params['pipe_options']['direction'],
        ).first()

        if not rule:
            self.debug.append('#Тип крепления к трубе: Отсутствует "Правило выбора крепления к трубы".')
            return PipeMountingGroup.objects.none()

        pipe_mounting_groups = pipe_mounting_groups.filter(
            id__in=rule.pipe_mounting_groups.values_list('id', flat=True)
        )

        return pipe_mounting_groups

    def get_pipe_params(self) -> Dict[str, Any]:
        """
        Возвращает параметры, связанные с трубой:
        - Список ID групп типов креплений к трубе, доступных по текущей конфигурации
        - Признак доступности параметра 'расстояние между опорами' (если пружинных блоков больше одного)
        """
        branch_qty = self.params["pipe_options"]["branch_qty"]

        if branch_qty > 1:
            is_support_distance_available = True
        else:
            is_support_distance_available = False

        if is_support_distance_available:
            available_support_distances = list(self.get_available_support_distances().values_list("id", flat=True))
        else:
            available_support_distances = []

        pipe_mounting_groups = self.get_pipe_mounting_groups()

        return {
            "pipe_mounting_groups": list(pipe_mounting_groups.values_list("id", flat=True)),
            "is_support_distance_available": is_support_distance_available,
            "support_distances": available_support_distances,
        }

    def get_pipe_mount_item(self) -> Tuple[Optional[Item], Optional[Item]]:
        """
        Вовзращает выбранный элемент крепления к трубе (Item) по ID из параметров.
        Если ID не указан - возвращает None.
        """
        pipe_mount_id = self.params['pipe_clamp']['pipe_mount']

        if pipe_mount_id:
            pipe_mount = Item.objects.get(id=pipe_mount_id)

            load_group_id = pipe_mount.parameters['LGV']
            load_group_lgv = LoadGroup.objects.get(id=load_group_id).lgv

            hanger_load_group_ids = self.get_load_group_ids_by_lgv()

            entry = ClampSelectionEntry.objects.filter(
                matrix__product_families=self.get_product_family(),
                matrix__clamp_detail_types=pipe_mount.variant.detail_type,
                hanger_load_group=self.get_lgv(),
                clamp_load_group=load_group_lgv,
            ).first()

            if not entry:
                fastener_component_group = ComponentGroup.objects.filter(
                    group_type=ComponentGroupType.FASTENER,
                ).first()

                if not fastener_component_group:
                    self.debug.append(
                        f"Невозможно получить крепление к трубе, так как не создан ComponentGroup.FASTENER",
                    )
                    return None, None

                zom = Item.objects.filter(
                    type_id__in=fastener_component_group.detail_types.values_list("id", flat=True),
                    parameters__LGV=load_group_id,
                ).first()
                return pipe_mount, zom

            if entry.result == "unlimited":
                zom = Item.objects.filter(
                    type_id__in=entry.matrix.fastener_detail_types.values_list('id', flat=True),
                    parameters__LGV=load_group_id,
                ).first()
                return pipe_mount, zom
            elif entry.result == "adapter_required":
                zom = Item.objects.filter(
                    type_id__in=entry.matrix.fastener_detail_types.values_list('id', flat=True),
                    parameters__LGV__in=hanger_load_group_ids,
                    parameters__LGV2=load_group_id,
                ).first()
                return pipe_mount, zom

        return None, None

    def get_top_mount_item(self) -> Optional[Item]:
        """
        Возвращает выбранный элемент верхнего креления (Item) по ID из параметров.
        Если ID не указан - возвращает None.
        """
        top_mount_id = self.params['pipe_clamp']['top_mount']

        if top_mount_id:
            top_mount = Item.objects.get(id=top_mount_id)

            return top_mount

        return None

    def get_selected_location(self) -> str:
        return self.params['pipe_options']['location']

    def get_selected_branch_counts(self) -> int:
        return self.params['pipe_options']['branch_qty']

    def get_selected_spring_block(self) -> Optional[Dict]:
        return self.params['spring_choice']['selected_spring']

    def get_selected_pipe_mount_id(self) -> Optional[int]:
        return self.params['pipe_clamp']['pipe_mount']

    def get_selected_pipe_mount_type(self):
        pipe_mount_type = self.params["pipe_clamp"]["pipe_mount_type"] or "item"
        return pipe_mount_type

    def get_selected_pipe_mount_item_as_variant(self):
        pipe_mount_id = self.params["pipe_clamp"]["pipe_mount"]
        return Variant.objects.get(id=pipe_mount_id)

    def get_selected_top_mount_id(self) -> Optional[int]:
        return self.params['pipe_clamp']['top_mount']

    def get_clamp_material(self) -> Optional[Material]:
        """
        Возвращает материал хомута (Material) по выбранному идентификатору.
        """
        material_id = self.params['pipe_params']['clamp_material']
        if not material_id:
            return None

        material = Material.objects.filter(id=material_id).first()

        if not material:
            self.debug.append(f'Не найден материал с id={material_id}. Возможно, он был удалён.')
            return None
        
        return material

    def get_available_pipe_directions(self, location: str) -> List[str]:
        """
        Возвращает допустимые направления трубы в зависимости от её расположения:
        - для горизонтального: x, y, под углом
        - для вертикального: z, под углом
        """
        if location == 'horizontal':
            return ['x', 'y', 'at_angle']
        elif location == 'vertical':
            return ['z', 'at_angle']

        return []

    def get_available_branch_counts(self, location: str) -> List[int]:
        """
        Возвращает допустимое количество пружинных блоков в зависимости от расположения трубы.
        - Горизонтальное: 1 или 2 блока
        - Вертикальное: только 2 блока
        """
        if location == 'horizontal':
            return [1, 2]
        elif location == 'vertical':
            return [2]

        return []

    def get_available_support_distances(self):
        support_distances = SupportDistance.objects.all()
        return support_distances

    def get_lgv(self):
        selected_spring = self.get_selected_spring_block()

        if not selected_spring:
            self.debug.append('#Не удалось получить выбранный пружинный блок.')
            return None

        lgv = selected_spring.get('load_group_lgv')

        return lgv

    def get_load_group_ids_by_lgv(self) -> List[int]:
        """
        Возвращает список ID групп нагрузок (LoadGroup) по lgv выбранного пружинного блока.
        """
        selected_spring = self.get_selected_spring_block()

        if not selected_spring:
            self.debug.append('#Не удалось получить выбранный пружинный блок.')
            return []
        
        lgv = selected_spring.get('load_group_lgv')

        if not lgv:
            self.debug.append('#Не удалось получить lgv для выбранного пружинного блока.')
            return []

        load_group_ids = list(LoadGroup.objects.filter(lgv=lgv).values_list('id', flat=True))
        
        if not load_group_ids:
            self.debug.append(f'Не найдены группы нагрузок с lgv={lgv}. Возможно, они были удалены.')
            return []
        
        return load_group_ids

    def clamp_is_compatible(self, *, matrix, hanger_lg, clamp_lgs):
        entry_map = {
            e.clamp_load_group: e
            for e in matrix.entries.filter(
                hanger_load_group=hanger_lg,
                clamp_load_group__in=clamp_lgs,
            )
        }

        for lg in clamp_lgs:
            entry = entry_map.get(lg)

            if not entry:
                continue

            if entry.result == "unlimited" and len(clamp_lgs) == 1:
                return True
            if (
                entry.result == "adapter_required"
                and len(clamp_lgs) >= 2
                and hanger_lg in clamp_lgs
            ):
                return True

        return False

    def get_available_clamps(self, variant: Variant, attributes: List[Attribute], pipe_clamps: QuerySet) -> List[int]:
        """
        Возвращает список доступных хомутов (Item) для выбранного варианта (Variant).
        """
        self.debug.append(f'#Выбор крепления к трубе: Есть номинальный диаметр трубы, это возможно хомут.')

        # Проверка что в атрибутах есть необходимые параметры
        pipe_diameter_attribute = self.get_pipe_diameter_attribute(attributes)
        if not pipe_diameter_attribute:
            self.debug.append(
                '#Выбор крепления к трубе: Не найден атрибут PipeDiameter. Не могу найти подходящие хомуты.'
            )
            return []

        load_group_attribute = self.get_load_group_attribute(attributes)
        if not load_group_attribute:
            self.debug.append(
                '#Выбор крепления к трубе: Не найден атрибут LoadGroup. Не могу найти подходящие хомуты.'
            )
            return []
        
        material_attribute = self.get_material_attribute(attributes)
        if not material_attribute:
            self.debug.append(
                '#Выбор крепления к трубе: Не найден атрибут Material. Не могу найти подходящие хомуты.'
            )
            return []
        
        load_attribute = self.get_attribute_by_usage(attributes, usage=AttributeUsageChoices.LOAD)
        if not load_attribute:
            self.debug.append(
                '#Выбор крепления к трубе: Не найден атрибут Load. Не могу найти подходящие хомуты.'
            )
            return []
        
        covering_type_attribute = self.get_attribute_by_catalog(attributes, catalog=AttributeCatalog.COVERING_TYPE)
        if not covering_type_attribute:
            self.debug.append(
                '#Выбор крепления к трубе: Не найден атрибут CoveringType. Не могу найти подходящие хомуты.'
            )
            return []

        clamp_load_attribute = self.get_attribute_by_usage(attributes, AttributeUsageChoices.CLAMP_LOAD)
        if not clamp_load_attribute:
            self.debug.append(
                '#Выбор крепления к трубе: Не найден атрибут ClampLoad. Не могу найти подходящие хомуты.'
            )
            return []

        selected_clamp_load = self.get_selected_clamp_load()
        if selected_clamp_load is None:
            self.debug.append(
                '#Выбор крепления к трубе: Не найдена нагрузка выбранного амортизатора/распорки. Не могу найти подходящие хомуты.'
            )
            return []
        
        # Инициализация нужных данных
        load_group_ids = self.get_load_group_ids_by_lgv()

        # Этап 1: Проверка по диаметру трубы
        if self.params['pipe_params']['insulation_thickness']:
            # Есть внутренняя изоляция
            self.debug.append(
                f'#Выбор крепления к трубе: Есть внутренняя изоляция, сравнение через него по формуле'
            )

            nominal_diameter_size = self.get_nominal_diameter_size()

            if not nominal_diameter_size:
                self.debug.append(
                    '#Выбор крепления к трубе: Не указан номинальный диаметр трубы или специальный диаметр. Не могу найти подходящие хомуты.'
                )
                return []
            
            dn_size = nominal_diameter_size + 2 * self.params['pipe_params']['insulation_thickness']

            pipe_diameter = PipeDiameter.objects.closest_by_size_and_standard(dn_size, Standard.RF)

            if not pipe_diameter:
                self.debug.append(
                    f'#Выбор крепления к трубе: Не нашел подходящий PipeDiameter для размера {dn_size}. Не могу найти подходящие хомуты.'
                )
                return []
        else:
            # Нет внутренней изоляции
            self.debug.append(
                f'#Выбор крепления к трубе: Нет внутренней изоляции, идет поиск по номинальному диаметру трубы.'
            )

            # TODO: Там же есть manual_size еще, надо учитывать это!
            pipe_diameter = self.get_pipe_diameter()

            if not pipe_diameter:
                self.debug.append(
                    '#Выбор крепления к трубе: Не указан номинальный диаметр трубы. Не могу найти подходящие хомуты.'
                )
                return []
        
        # Этап 2: Проверка по материалу и температуре
        self.debug.append('#Выбор крепления к трубе: Начинаю проверку по материалу и температуре.')

        # Температуры
        temp1, temp2 = self.get_temperatures()
        self.debug.append(f'#Выбор крепления к трубе: Температура 1: {temp1}, Температура 2: {temp2}')

        # Введенная нагрузка
        load = self.get_load_minus_z()
        self.debug.append(f'#Выбор крепления к трубе: Введенная нагрузка: {load}')

        # Группа материалов
        clamp_material = self.get_clamp_material()

        if not clamp_material:
            self.debug.append('#Выбор крепления к трубе: Не указан материал хомута. Не могу найти подходящие хомуты.')
            return []
        
        material_group = clamp_material.group
        self.debug.append(f'#Выбор крепления к трубе: Группа материала: {material_group}.')

        if not temp1:
            self.debug.append(
                '#Выбор крепления к трубе: Не указана температура 1. Не могу найти подходящие хомуты.'
            )
            return []
        
        temp1_material_coefficient = ClampMaterialCoefficient.objects.filter(
            material_group=material_group
        ).for_temperature(temp1).first()

        if not temp1_material_coefficient:
            self.debug.append(
                f'#Выбор крепления к трубе: Не нашел коэффициент материала для температуры {temp1}. Не могу найти подходящие хомуты.'
            )
            return []
        
        temp1_coefficient_value = temp1_material_coefficient.coefficient
        self.debug.append(f'#Выбор крепления к трубе: Коэффициент материала для температуры {temp1}: {temp1_coefficient_value}')
        load_with_temp1_coefficient = load / temp1_coefficient_value
        self.debug.append(f'#Выбор крепления к трубе: Нагрузка с учетом коэффициента для температуры {temp1}: {load_with_temp1_coefficient}')

        if temp2:
            temp2_material_coefficient = ClampMaterialCoefficient.objects.filter(
                material_group=material_group
            ).for_temperature(temp2).first()

            if not temp2_material_coefficient:
                self.debug.append(
                    f'#Выбор крепления к трубе: Не нашел коэффициент материала для температуры {temp2}. Не могу найти подходящие хомуты.'
                )
                return []

            temp2_coefficient_value = temp2_material_coefficient.coefficient
            self.debug.append(f'#Выбор крепления к трубе: Коэффициент материала для температуры {temp2}: {temp2_coefficient_value}')
            load_with_temp2_coefficient = load / temp2_coefficient_value
            self.debug.append(f'#Выбор крепления к трубе: Нагрузка с учетом коэффициента для температуры {temp2}: {load_with_temp2_coefficient}')
        else:
            self.debug.append('#Выбор крепления к трубе: Не указана температура 2. Использую только температуру 1.')
            load_with_temp2_coefficient = None
        
        # Этап 3: Проверка крепления по типу покрытия
        self.debug.append('#Выбор крепления к трубе: Начинаю проверку по типу покрытия.')
        if clamp_material.is_stainless_steel():
            required_covering_type_codes = [0]
            self.debug.append(f'#Выбор крепления к трубе: Материал {clamp_material.name} - нержавеющая сталь. Требуется покрытие типа 0.')
        elif clamp_material.is_black_metal() and temp1 < 250:
            required_covering_type_codes = [1, 2]
            self.debug.append(f'#Выбор крепления к трубе: Материал {clamp_material.name} - черный металл и температура < 250. Требуется покрытие типа 1 или 2.')
        elif clamp_material.is_black_metal() and temp1 >= 250:
            required_covering_type_codes = [3]
            self.debug.append(f'#Выбор крепления к трубе: Материал {clamp_material.name} - черный металл и температура >= 250. Требуется покрытие типа 3.')
        else:
            self.debug.append(
                f'#Выбор крепления к трубе: Неизвестный тип у материала {clamp_material.name}. Не могу найти подходящие хомуты.'
            )
            return []
        
        covering_type_ids = list(CoveringType.objects.filter(numeric__in=required_covering_type_codes).values_list('id', flat=True))

        # Этап 4: Базовая фильтрация
        filter_params = {
            'variant': variant,
            f'parameters__{material_attribute.name}': clamp_material.id,
            f'parameters__{pipe_diameter_attribute.name}': pipe_diameter.id,
            f'parameters__{clamp_load_attribute.name}__gte': selected_clamp_load,
            f'parameters__{load_attribute.name}__gte': load_with_temp1_coefficient,
            f'parameters__{covering_type_attribute.name}__in': covering_type_ids,
        }

        if load_with_temp2_coefficient is not None:
            filter_params[f'parameters__{load_attribute.name}__gte'] = load_with_temp2_coefficient

        # Этап 5: Проверка и фильтрация двойных хомутов
        branch_qty = self.get_selected_branch_counts()

        if self.is_clamp_or_traverse(attributes) and branch_qty > 1:
            self.debug.append(
                f'#Выбор крепления к трубе: Есть монтажный размер и количество опор больше 1, это хомут '
                f'или траверса, фильтрация еще по монтажному размеру.'
            )
            install_size_attr = self.get_attribute_by_usage(attributes, AttributeUsageChoices.INSTALLATION_SIZE)

            if not install_size_attr:
                self.debug.append(
                    '#Выбор крепления к трубе: Не найден атрибут InstallationSize. Не могу найти подходящие хомуты.'
                )
                return []

            support_distance = self.get_support_distance()

            if not support_distance:
                self.debug.append(
                    '#Выбор крепления к трубе: Не указано расстояние между опорами. Не могу найти подходящие хомуты.'
                )
                return []
            
            filter_params[f'parameters__{install_size_attr.name}'] = support_distance
        else:
            self.debug.append(
                '#Выбор крепления к трубе: Нет монтажного размера или количество опор 1, фильтрация по нему не требуется.'
            )

        lgv = self.get_lgv()

        matrix = ClampSelectionMatrix.objects.filter(
            product_families=self.get_product_family(),
            clamp_detail_types=variant.detail_type,
        ).prefetch_related('entries').first()

        if not matrix:
            self.debug.append(
                f'Не найдено матрица выбора хомутов для хомута {variant.detail_type}. Будут хомуты с '
                f'LGV={lgv}',
            )
            filter_params[f'parameters__{load_group_attribute.name}__in'] = load_group_ids
            self.debug.append(f'#Выбор крепления к трубе: Фильтрую по параметрам: {filter_params}')
            found_items = pipe_clamps.filter(**filter_params)
            return list(found_items.values_list('id', flat=True))

        self.debug.append(f'#Выбор крепления к трубе: Фильтрую по параметрам: {filter_params}')

        found_item_ids = []

        unlimited_entries = matrix.entries.filter(hanger_load_group=lgv, result='unlimited')
        self.debug.append(f'Проверяем по unlimited записям матрицы: {unlimited_entries.count()}')

        zom_items = Item.objects.filter(type__in=matrix.fastener_detail_types.all())
        self.debug.append(f'#Выбор крепления к трубе: Всего айтемов в переходников: {zom_items.count()}')

        for entry in unlimited_entries:
            self.debug.append(f'#Выбор крепления к трубе: Проверяю запись матрицы: {entry}')

            clamp_load_group_ids = list(
                LoadGroup.objects.filter(lgv=entry.clamp_load_group).values_list('id', flat=True)
            )

            new_filter_params = copy.copy(filter_params)
            new_filter_params[f'parameters__{load_group_attribute.name}__in'] = clamp_load_group_ids
            filtered_pipe_clamps = pipe_clamps.filter(**new_filter_params)

            if not filtered_pipe_clamps.exists():
                continue

            filtered_zom_items = zom_items.filter(
                Q(parameters__LGV__in=load_group_ids) & (
                    Q(parameters__LGV2=None) | ~Q(parameters__has_key="LGV2")
                )
            )
            self.debug.append(f'#Выбор крепления к трубе: Найдено переходников: {filtered_zom_items.count()}')

            if filtered_zom_items.exists():
                found_item_ids.extend(filtered_pipe_clamps.values_list('id', flat=True))

        adapter_required_entries = matrix.entries.filter(hanger_load_group=lgv, result='adapter_required')
        self.debug.append(f'Проверяем по adapter_required записям матрицы: {adapter_required_entries.count()}')

        for entry in adapter_required_entries:
            self.debug.append(f'#Выбор крепления к трубе: Проверяю запись матрицы: {entry}')

            clamp_load_group_ids = list(
                LoadGroup.objects.filter(lgv=entry.clamp_load_group).values_list('id', flat=True)
            )

            new_filter_params = copy.copy(filter_params)
            new_filter_params[f'parameters__{load_group_attribute.name}__in'] = clamp_load_group_ids
            filtered_pipe_clamps = pipe_clamps.filter(**new_filter_params)

            if not filtered_pipe_clamps.exists():
                continue

            filtered_zom_items = zom_items.filter(
                parameters__LGV__in=load_group_ids,  # Первый параметр LGV это по нагрузочкой группе подвеса
                parameters__LGV2__in=clamp_load_group_ids,  # Второй параметр LGV это по нагрузочкой группе хомута
            )
            self.debug.append(f'#Выбор крепления к трубе: Найдено переходников: {filtered_zom_items.count()}')

            if filtered_zom_items.exists():
                found_item_ids.extend(filtered_pipe_clamps.values_list('id', flat=True))

        return list(set(found_item_ids))

    def get_selected_pipe_mounting_group(self):
        if not self.params['pipe_params']['pipe_mounting_group']:
            self.debug.append('#Выбор крепления к трубе: Не выбран тип крепления к трубе.')
            return None

        pipe_mounting_group = PipeMountingGroup.objects.get(id=self.params['pipe_params']['pipe_mounting_group'])
        return pipe_mounting_group

    def get_available_pipe_clamp_variants(self, pipe_mounting_group):
        self.debug.append(f"#Выбор крепления к трубе: Показываю список исполнений вместо деталей.")
        return list(pipe_mounting_group.variants.values_list("id", flat=True))

    def get_available_pipe_clamps(self, pipe_mounting_group) -> List[int]:
        """
        Возвращает список ID подходящих креплений к трубе (Item), включая хомуты, башмаки и при необходимости - траверсы.
        Фильтрация выполняется по типа крепления, материалу, DN, нагрузочной группе, толщине изоляции, монтажному размеру.
        """
        self.debug.append('#Выбор крепления к трубе: Начинаю процесс поиска.')
        pipe_clamps = Item.objects.all()
        self.debug.append(f'#Выбор крепления к трубе: Этап 1, получаю все айтемы {pipe_clamps.count()}')
        pipe_clamps = pipe_clamps.filter(variant__in=pipe_mounting_group.variants.all())
        self.debug.append(
            f'#Выбор крепления к трубе: Этап 2, айтемы после фильтрации типом крепления к трубе {pipe_clamps.count()}'
        )

        if not pipe_clamps.exists():
            self.debug.append('#Выбор крепления к трубе: Пустой список после фильтрации по группе.')
            return []

        material_id = self.params['pipe_params']['clamp_material']
        selected_spring = self.params['spring_choice']['selected_spring']
        if not material_id or not selected_spring:
            self.debug.append('#Выбор крепления к трубе: Нет материала или пружинного блока.')
            return []

        load_group_lgv = selected_spring['load_group_lgv']
        load_group_ids = list(LoadGroup.objects.filter(lgv=load_group_lgv).values_list('id', flat=True))
        variants = Variant.objects.filter(id__in=pipe_clamps.values_list('variant', flat=True)).distinct()

        branch_qty = self.get_selected_branch_counts()
        self.debug.append(f'#Выбор крепления к трубе: Количество опор: {branch_qty}')

        found_items = []

        for variant in variants:
            self.debug.append(f'#Выбор крепления к трубе: Исполнение {variant} (id={variant.id})')

            attributes = variant.get_attributes()

            if self.is_clamp_or_shoe(attributes):
                clamp_ids = self.get_available_clamps(variant, attributes, pipe_clamps)
                found_items.extend(clamp_ids)
            elif self.is_lug(attributes):
                # Проушина
                self.debug.append(
                    f'#Выбор крепления к трубе: Это не было хомут или башмак, но есть LoadGroup, это проушина'
                )
                load_group_attribute = self.get_load_group_attribute(attributes)
                load_group_attribute_name = load_group_attribute.name

                material_attribute = self.get_material_attribute(attributes)
                if not material_attribute:
                    self.debug.append(
                        f'#Выбор крепления к трубе: Не нашел атрибута Material. Поиск у {variant} (id={variant.id}) '
                        f'окончен.'
                    )
                    continue

                filter_params = {
                    'variant': variant,
                    f'parameters__{material_attribute.name}': material_id,
                    f'parameters__{load_group_attribute_name}__in': load_group_ids,
                }

                # Доп. фильтры для проушин:
                # а) зависимость от толщины изоляции, значение атрибута должно быть больше толщины изоляции;
                thickness_attribute = self.get_attribute_by_usage(attributes, AttributeUsageChoices.THICKNESS)
                if thickness_attribute and self.params['pipe_params']['outer_insulation_thickness']:
                    self.debug.append(
                        f'#Выбор крепления к трубе: Есть атрибут толщина и пользователь указал внешнюю толщину '
                        f'изоляции. Включаем в фильтр.'
                    )
                    outer_insulation_thickness = self.params['pipe_params']['outer_insulation_thickness']
                    filter_params[f'parameters__{thickness_attribute.name}__lt'] = outer_insulation_thickness
                else:
                    self.debug.append(
                        f'#Выбор крепления к трубе: Нет либо атрибута толщины или пользователь не указал внешнюю '
                        f'толщину изоляции. Не добавляем в фильтр.'
                    )

                # б) влияние температуры для проушин (формулу пока не дали).
                # TODO: Здесь должен быть влияние температуры для проушин
                pass

                self.debug.append(
                    f'#Выбор крепления к трубе: У исполнение {variant} ищем по такому фильтру '
                    f'(проушина): {filter_params}'
                )
                finding_items = list(pipe_clamps.filter(**filter_params).values_list('id', flat=True))
                self.debug.append(
                    f'#Выбор крепления к трубе: У исполнение {variant} найдено (проушина): {len(finding_items)}'
                )
                found_items.extend(finding_items)
            elif self.is_clamp_or_traverse(attributes) and branch_qty > 1:
                # Траверса
                self.debug.append(
                    f'#Выбор крепления к трубе: Есть монтажный размер и количество опор больше 1. Но это не хомут, '
                    f'это траверса.'
                )
                install_size_attr = self.get_attribute_by_usage(attributes, AttributeUsageChoices.INSTALLATION_SIZE)
                support_distance = self.get_support_distance()

                if support_distance is None:
                    self.debug.append(
                        f'#Выбор крепления к трубе: Пользователь не указал расстояние опор. Заканчиваю поиск у '
                        f'{variant} (id={variant.id})'
                    )
                    continue

                material_attribute = self.get_material_attribute(attributes)
                if not material_attribute:
                    self.debug.append(
                        f'#Выбор крепления к трубе: Не нашел атрибута Material. Поиск у {variant} (id={variant.id}) '
                        f'окончен.'
                    )
                    continue

                filter_params = {
                    'variant': variant,
                    f'parameters__{material_attribute.name}': material_id,
                    f'parameters__{install_size_attr.name}': support_distance,
                }
                self.debug.append(
                    f'#Выбор крепления к трубе: У исполнение {variant} ищем по такому фильтру '
                    f'(траверса): {filter_params}'
                )
                finding_items = list(pipe_clamps.filter(**filter_params).values_list('id', flat=True))
                self.debug.append(
                    f'#Выбор крепления к трубе: У исполнение {variant} найдено (траверса): {len(finding_items)}'
                )
                found_items.extend(finding_items)

            self.debug.append(f'#Выбор крепления к трубе: Окончиваю поиск у {variant} (id={variant.id})')

        found_items = list(set(found_items))
        self.debug.append(f'#Выбор крепления к трубе: Найдено {len(found_items)}')
        return found_items

    def get_available_top_mounts(self) -> List[int]:
        """
        Возвращает список ID доступных верхних креплений (Item),
        если семейство изделия поддерживает выборв ерхнего соединения.
        Если не выбрано семейство или выбор недоступен - возвращается пустой список.
        """
        if not self.get_product_family():
            self.debug.append(
                '#Выбор верхнего соединения: Не выбран семейство изделии для списка "Выбор верхнего соединения". '
                'Возвращаем пустой список.'
            )
            return []

        family = self.get_product_family()

        if not family.is_upper_mount_selectable:
            self.debug.append(
                '#Выбор верхнего соединения: У семейство изделии не выбран параметр "Доступен выбор верхнего '
                'крепления". Возвращаем пустой список.'
            )
            return []

        top_mounts = Item.objects.filter(type__product_family=family)

        return list(top_mounts.values_list('id', flat=True))

    def get_suitable_spring_block_item(self) -> Optional[Item]:
        """
        Возвращает Item, соответствующий выбранному пружинному блоку по его маркировке.
        Маркировка приводится к стандартному виду (добавляется ведущий 0 при необходимости).
        Если найдено несколько - берётся первый. Если не найден - возвращается None.
        """
        self.debug.append('#Пружинный блок: Начинаю поиск детали пружинного блока по выбранному пружинному блоку.')
        selected_spring = self.get_selected_spring_block()

        if not selected_spring:
            self.debug.append('#Пружинный блок: Не выбран пружинный блок для поиска детали пружинного блока.')
            return None

        series_name = selected_spring['name']
        size = selected_spring['size']
        rated_stroke = selected_spring['rated_stroke']

        product_family = self.get_product_family()

        if not product_family:
            self.debug.append('#Пружинный блок: Не выбран семейство изделии.')
            return None

        # Ищем исполнения, у которого обязательно есть два атрибута: Типоразмер и Номинальный ход
        has_size = Attribute.objects.filter(
            Q(variant=OuterRef('pk')) | Q(detail_type=OuterRef('detail_type')),
            usage=AttributeUsageChoices.SIZE,
        )

        has_rated_stroke = Attribute.objects.filter(
            Q(variant=OuterRef('pk')) | Q(detail_type=OuterRef('detail_type')),
            usage=AttributeUsageChoices.RATED_STROKE,
        )

        selectable_group = ComponentGroup.objects.filter(
            group_type=ComponentGroupType.SERIES_SELECTABLE,
            detail_types=OuterRef('detail_type'),
        )

        allowed_detail_types = SpringBlockFamilyBinding.objects.filter(
            family=product_family
        ).values_list('spring_block_types', flat=True)

        variants = Variant.objects.annotate(
            has_size_attr=Exists(has_size),
            has_rated_stroke_attr=Exists(has_rated_stroke),
            is_series_selectable=Exists(selectable_group),
        ).filter(
            has_size_attr=True,
            has_rated_stroke_attr=True,
            is_series_selectable=True,
            series=series_name,
            detail_type_id__in=allowed_detail_types,
        )

        if not variants.exists():
            self.debug.append(f'#Пружинный блок: Не найдено подходящих исполнений для серии {series_name}.')
            self.debug.append(
                f'#Пружинный блок: Проверьте, что есть ComponentGroup с типом SERIES_SELECTABLE и '
                f'с атрибутами "Типоразмер" и "Номинальный ход".'
            )
            return None

        found_block_items = []

        for variant_index, variant in enumerate(variants):
            self.debug.append(
                f'#Пружинный блок: Проверяю исполнение {variant_index + 1}/{variants.count()} - {variant.name} '
                f'(id={variant.id})'
            )

            # Получаем список атрибутов конкретного исполнения
            # Здесь так же задаем приоритетность атрибутов: атрибуты самого исполнения приоритетнее чем базовый атрибут
            attributes = variant.get_attributes()

            size_attribute = self.get_attribute_by_usage(attributes, AttributeUsageChoices.SIZE)
            rated_stroke_attribute = self.get_attribute_by_usage(attributes, AttributeUsageChoices.RATED_STROKE)

            if not size_attribute or not rated_stroke_attribute:
                # Если нет хотя бы одного из атрибутов, то пропускаем, это не то исполнение
                continue

            size_key = f'parameters__{size_attribute.name}'
            stroke_key = f'parameters__{rated_stroke_attribute.name}'

            self.debug.append(f'#Пружинный блок: Ищу детали по фильтру: {size_key}={size}, {stroke_key}={rated_stroke}')

            # TODO: Временное решение, нужно чтобы изначально в parameters хранился значение соответствующему типу.
            filtered_items = Item.objects.filter(
                variant=variant
            ).filter(
                Q(**{size_key: size}) | Q(**{size_key: str(size)}),
                Q(**{stroke_key: rated_stroke}) | Q(**{stroke_key: str(rated_stroke)}),
            )

            self.debug.append(
                f'#Пружинный блок: Найдено {filtered_items.count()} деталей по фильтру: '
                f'{size_key}={size}, {stroke_key}={rated_stroke}'
            )

            found_block_items.extend(filtered_items)

        found_block_items = list(set(found_block_items))
        total = len(found_block_items)

        if not total:
            self.debug.append(
                f'#Пружинный блок: Не найден деталь пружинного блока.'
            )
            return None

        if total > 1:
            self.debug.append(
                f'#Пружинный блок: Найдено несколько деталей пружинного блока: {total}. Выбираю первую'
            )
            spring_ids = ', '.join([str(item.id) for item in found_block_items])
            self.debug.append(f'#Пружинный блок: Список деталей пружинного блока: {spring_ids}')

        return found_block_items[0]

    def get_desired_system_height(self) -> Optional[float]:
        return self.params['system_settings']['system_height']

    def calculate_cold_mounting_length(self, variant: Variant) -> Tuple[Optional[Attribute], Optional[float], Optional[Dict]]:
        """
        Вычисляет длину холодной монтировки для исполнения (Variant).
        """
        cache_key = f"calculate_cold_mounting_length_{variant.id}"

        if self.key_exists_in_cache(cache_key):
            attribute, value, errors = self.get_from_cache(cache_key)
            return attribute, value, errors

        attribute = Attribute.objects.for_variant(variant).filter(usage=AttributeUsageChoices.E_INITIAL).first()

        ephemeral_item = Item(
            type=variant.detail_type,
            variant=variant,
            parameters={},
        )

        children = []
        spring_block = self.get_suitable_spring_block_item()

        if spring_block:
            children.append(spring_block)

        specification = self.get_specification(variant, children, remove_empty=True)

        selected_spring = self.params["spring_choice"].get("selected_spring")

        if not selected_spring:
            result = None, None, None
            self.add_to_cache(cache_key, result)
            return result

        extra_context = {
            "Finitial": selected_spring.get("load_initial"),
            "Fcold": selected_spring.get("load_minus"),
            "k": selected_spring.get("spring_stiffness"),
        }

        value, errors = ephemeral_item.calculate_attribute(
            attribute,
            extra_context=extra_context,
            children=specification,
        )

        if value is not None:
            # Приводим значение к целому числу с округлением
            value = int(Decimal(str(value)).to_integral_value(rounding=ROUND_HALF_UP))

        result = attribute, value, errors
        self.add_to_cache(cache_key, result)
        self.debug.append(
            f"#Расчет {attribute.name}: {value} (с ошибками: {errors}) для исполнения {variant.name} (id={variant.id})"
        )
        return result

    def calculate_system_height_without_studs(self, variant: Variant) -> Tuple[Optional[float], Optional[Dict]]:
        attribute = Attribute.objects.for_variant(variant).filter(name='Etmp').first()

        if not attribute:
            return None, {'Etmp': 'Нет атрибута для вычисления высоты системы без шпилек.'}

        ephemeral_item = Item(
            type=variant.detail_type,
            variant=variant,
            parameters={},
        )

        children = []
        spring_block = self.get_suitable_spring_block_item()

        if spring_block:
            children.append(spring_block)

        pipe_mount, zom = self.get_pipe_mount_item()

        if pipe_mount:
            children.append(pipe_mount)

        if zom:
            children.append(zom)

        top_mount = self.get_top_mount_item()
        if top_mount:
            children.append(top_mount)

        coupling_items = self.find_couplings(variant)

        if coupling_items:
            children.extend(coupling_items)

        extra_context = {}
        selected_spring = self.params['spring_choice'].get('selected_spring')
        if not selected_spring:
            return None, None

        extra_context['Finitial'] = selected_spring.get('load_initial')
        extra_context['Fcold'] = selected_spring.get('load_minus')
        extra_context['k'] = selected_spring.get('spring_stiffness')

        cold_mounting_length_attribute, cold_mounting_length, cold_mounting_length_errors = self.calculate_cold_mounting_length(variant)

        extra_context[cold_mounting_length_attribute.name] = cold_mounting_length

        specification = self.get_specification(variant, children, remove_empty=True)
        value, errors = ephemeral_item.calculate_attribute(attribute, extra_context=extra_context, children=specification)

        if errors:
            return None, errors

        return value, errors

    def calculate_system_height(self, variant: Variant, children=None) -> Tuple[Optional[float], Optional[Dict]]:
        """
        Выполняет расчет общей высоты системы на основе исполнения (variant),
        используя атрибут с типом 'Используется для подсчета высоты системы' (SYSTEM_HEIGHT).

        Формируется временный Item, к которому подставляются дочерние компоненты:
        пружинный блок, крепление к трубе и верхнее соединение (если заданы).
        Дополнительно передаются параметры Fcold и k для подстановки в формулу.

        Возвращает вычисленную высоту (float) или None при ошибке.
        """
        attribute = Attribute.objects.for_variant(variant).filter(usage=AttributeUsageChoices.SYSTEM_HEIGHT).first()

        ephemeral_item = Item(
            type=variant.detail_type,
            variant=variant,
            parameters={},
        )

        if not children:
            children = []
            spring_block = self.get_suitable_spring_block_item()

            if spring_block:
                children.append(spring_block)

            pipe_mount, zom = self.get_pipe_mount_item()

            if pipe_mount:
                children.append(pipe_mount)

            if zom:
                children.append(zom)

            top_mount = self.get_top_mount_item()
            if top_mount:
                children.append(top_mount)

        extra_context = {}
        selected_spring = self.params['spring_choice'].get('selected_spring')
        if not selected_spring:
            return None, None

        extra_context['Finitial'] = selected_spring.get('load_initial')
        extra_context['Fcold'] = selected_spring.get('load_minus')
        extra_context['k'] = selected_spring.get('spring_stiffness')

        cold_mounting_length_attribute, cold_mounting_length, cold_mounting_length_errors = self.calculate_cold_mounting_length(variant)
        extra_context[cold_mounting_length_attribute.name] = cold_mounting_length

        specification = self.get_specification(variant, children, remove_empty=True)
        value, errors = ephemeral_item.calculate_attribute(attribute, extra_context=extra_context, children=specification)

        if errors:
            return None, errors

        return value, errors

    def load_stud_lengths(self, base_composition, ascending=True):
        base_child = base_composition.base_child
        base_child_variant = base_composition.base_child_variant

        if base_child_variant:
            attributes = base_child_variant.get_attributes()
        else:
            attributes = base_child.get_attributes()

        attr = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LENGTH)
        if not attr:
            return None, [], set(), Item.objects.none()

        attr_name = attr.name

        qs = Item.objects.filter(
            Q(type=base_child) | Q(variant=base_child_variant) if base_child_variant else Q(type=base_child)
        ).exclude(
            parameters__isnull=True
        ).exclude(
            **{f'parameters__{attr_name}__isnull': True}
        )

        raw = qs.values_list(f'parameters__{attr_name}', flat=True)
        lengths = []
        for v in raw:
            if isinstance(v, (int, float)):
                lengths.append(int(v))
            elif isinstance(v, str) and v.isdigit():
                lengths.append(int(v))
        lengths.sort(reverse=not ascending)

        return attr_name, lengths, set(lengths), qs

    def get_coupling_items(self, base_composition):
        base_child = base_composition.base_child
        base_child_variant = base_composition.base_child_variant

        if base_child_variant:
            attributes = base_child_variant.get_attributes()
        else:
            attributes = base_child.get_attributes()

        attr = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LOAD_GROUP)

        if not attr:
            return None, []

        attr_name = attr.name
        item_qs = Item.objects.filter(
            Q(type=base_child) | Q(variant=base_child_variant) if base_child_variant else Q(type=base_child)
        ).exclude(parameters__isnull=True).exclude(**{f'parameters__{attr_name}__isnull': True})

        return attr_name, item_qs

    def find_couplings(self, variant):
        coupling_component_group = ComponentGroup.objects.filter(
            group_type=ComponentGroupType.COUPLING,
        ).first()

        if not coupling_component_group:
            self.debug.append(f"#Поиск муфт: Не нашли список муфт в ComponentGroup.")
            return None

        coupling_detail_types = coupling_component_group.detail_types.all()

        base_compositions = BaseComposition.objects.filter(
            base_parent_variant=variant,
            base_child__in=coupling_detail_types,
        )
        total = base_compositions.aggregate(total_count=Sum("count"))["total_count"] or 0

        if not total:
            self.debug.append(f"#Поиск муфт: В базовом составе нет муфт.")
            return []

        found_coupling_items = []

        for base_composition in base_compositions:
            attribute_name, coupling_items = self.get_coupling_items(base_composition)

            filter_params = {
                f"parameters__{attribute_name}__in": self.get_load_group_ids_by_lgv(),
            }
            coupling_item = coupling_items.filter(**filter_params).first()

            if not coupling_item:
                self.debug.append(f"#Поиск муфт: Для базового состава {base_composition} не нашли подходящей муфты.")
                return None

            found_coupling_items.append(coupling_item)

        return found_coupling_items

    def find_one_stud(self, base_compositions, rest_system_height):
        self.debug.append(f"#Поиск шпилька: В базовом составе 1 шпилька, ищем только одну шпильку.")
        base_composition = base_compositions[0]
        attr_name, lengths, set_lengths, qs = self.load_stud_lengths(base_composition, ascending=True)

        if not attr_name:
            self.debug.append(
                f'#Поиск шпилька: Базовый состав={base_composition} не имеет атрибута usage=LENGTH. Пропускаю',
            )
            return None

        if rest_system_height in set_lengths:
            item = qs.filter(**{f"parameters__{attr_name}": rest_system_height}).first()
            if item:
                self.debug.append(f"Найдено подходящая шпилька: {item} (id={item.id})")
                return item

        self.debug.append(f"Не смогли найти подходящую шпильку по {attr_name}={rest_system_height}.")
        return None

    def find_two_studs(self, variant, base_compositions, rest_system_height):
        self.debug.append('#Поиск шпилька: В базовом составе 2 шпильки, ищем пару шпилек.')
        comp1, comp2 = base_compositions

        attr1, len1, set1, qs1 = self.load_stud_lengths(comp1, ascending=True)
        attr2, len2, set2, qs2 = self.load_stud_lengths(comp2, ascending=True)

        if not attr1 or not attr2:
            self.debug.append('#Поиск шпилька: нет LENGTH у одной из шпилек.')
            return None, None

        a_list, a_attr, a_qs, b_set, b_attr, b_qs = (
            (len1, attr1, qs1, set2, attr2, qs2) if len(len1) <= len(len2)
            else (len2, attr2, qs2, set1, attr1, qs1)
        )

        visited = set()
        for l in a_list:
            need = rest_system_height - l
            if l in visited:
                continue
            visited.add(l)

            if need in b_set:
                it1 = a_qs.filter(**{f"parameters__{a_attr}": l}).first()
                it2 = b_qs.filter(**{f"parameters__{b_attr}": need}).first()
                if it1 and it2:
                    studs = sorted(
                        [(int(it1.parameters.get(a_attr)), it1),
                         (int(it2.parameters.get(b_attr)), it2)],
                        key=lambda x: x[0],
                        reverse=True
                    )
                    bigger, smaller = studs[0][1], studs[1][1]

                    self.debug.append(
                        f"Найдены подходящие шпильки: {bigger} (id={bigger.id}), {smaller} (id={smaller.id})"
                    )
                    return bigger, smaller

        self.debug.append(f"Не нашли пару шпилек для высоты {rest_system_height}.")
        return None, None

    def find_three_studs(self, variant, base_compositions, rest_system_height):
        self.debug.append(
            '#Поиск шпилька: В базовом составе 3 шпильки. Условие: 2 одинаковые + третья минимальная; сумма = высоте.'
        )
        comp1, comp2, comp3 = base_compositions

        attr1, len1, set1, qs1 = self.load_stud_lengths(comp1, ascending=False)  # по условию — идём от больших
        attr2, len2, set2, qs2 = self.load_stud_lengths(comp2, ascending=False)
        attr3, len3, set3, qs3 = self.load_stud_lengths(comp3, ascending=True)  # "третья минимальная" ищется снизу

        if not (attr1 and attr2 and attr3):
            self.debug.append('#Поиск шпилька: нет LENGTH у одной из шпилек.')
            return None, None, None

        shorter_two = len1 if len(len1) <= len(len2) else len2
        for l in shorter_two:
            third = rest_system_height - 2 * l
            if third > l:
                continue
            if third in set3:
                it1 = qs1.filter(**{f"parameters__{attr1}": l}).first()
                it2 = qs2.filter(**{f"parameters__{attr2}": l}).first()
                it3 = qs3.filter(**{f"parameters__{attr3}": third}).first()
                if it1 and it2 and it3:
                    self.debug.append(
                        f"Найдены подходящие шпильки: {it1} (id={it1.id}), {it2} (id={it2.id}), {it3} (id={it3.id})")
                    return it1, it2, it3

        self.debug.append(
            f"Не нашли тройку шпилек для высоты {rest_system_height}."
        )
        return None, None, None

    def get_suitable_variant(self) -> Tuple[Optional[Variant], Optional[float], Optional[List]]:
        """
        Выполняет пошаговый подбор подходящих Variant (исполнений) изделия
        на основе выбранных компонентов:
        - пружинного блока
        - крепления к трубе
        - верхнего крепления (если доступно)

        Подбор ведётся по структуре BaseComposition:
        - сначало по типам (DetailType)
        - затем уточняется по конкретным Variant

        Возвращает список сериализованных подходящих Variant.
        """
        desired_system_height = self.get_desired_system_height()

        spring_block = self.get_suitable_spring_block_item()
        branch_qty = self.get_selected_branch_counts()
        items_for_specification = [spring_block]

        if not spring_block:
            self.debug.append('#Поиск DetailType: Не выбран пружинный блок. Пропускаем поиск подходящих исполнений.')
            return None, None, None

        variants = Variant.objects.all()
        variants = self.filter_suitable_variants_via_child(variants, spring_block, count=branch_qty)

        pipe_mount = self.get_selected_pipe_mount_id()

        if not pipe_mount:
            self.debug.append(
                '#Поиск DetailType: Не выбран "Выбор крепления к трубе". Пропускаем поиск подходящих исполнений.'
            )
            return None, None, None

        pipe_mount_type = self.get_selected_pipe_mount_type()

        component_group = ComponentGroup.objects.filter(group_type=ComponentGroupType.STUDS).first()

        if not component_group:
            self.debug.append('#Поиск DetailType: Не найден группа компонентов с типом "Шпильки"')
            return None, None, None

        stud_detail_types = component_group.detail_types.all()

        if pipe_mount_type == "variant":
            self.debug.append(f"#Поиск DetailType: pipe_mount_type == variant")
            pipe_mount_variant = self.get_selected_pipe_mount_item_as_variant()
            self.debug.append(f"#Поиск DetailType: Выбарнный исполнение pipe_mount_variant: {pipe_mount_variant}")
            base_compositions = pipe_mount_variant.base_parent.all()
            load_group_ids = self.get_load_group_ids_by_lgv()

            for base_composition in base_compositions:
                self.debug.append(f"Базовый состав: {base_composition}")
                bc_found_item = None
                if base_composition.base_child in stud_detail_types:
                    continue

                if base_composition.base_child_variant:
                    suitable_item = Item.objects.filter(
                        variant=base_composition.base_child_variant, parameters__LGV__in=load_group_ids,
                    ).first()
                    bc_found_item = suitable_item
                    self.debug.append(f"Найденный Item для базового состава: {suitable_item}")
                else:
                    variants = Variant.objects.filter(detail_type=base_composition.base_child)
                    for variant in variants:
                        suitable_item = Item.objects.filter(
                            variant=variant, parameters__LGV__in=load_group_ids,
                        ).first()

                        if suitable_item:
                            bc_found_item = suitable_item
                            self.debug.append(f"Найденный Item для базового состава: {suitable_item}")
                            break

                if bc_found_item:
                    variants = self.filter_suitable_variants_via_child(variants, bc_found_item, count=base_composition.count)
                    items_for_specification.append(bc_found_item)
                else:
                    self.debug.append(f"Поиск DetailType: Не найден айтем для базового состава {base_composition}")
                    return None, None, None
        else:
            pipe_mount_item, zom = self.get_pipe_mount_item()

            if not pipe_mount_item:
                self.debug.append(f"Поиск DetailType: Не найдено подходящее крепление к трубе (id={pipe_mount}).")
                return None, None, None

            items_for_specification.append(pipe_mount_item)

            variants = self.filter_suitable_variants_via_child(variants, pipe_mount_item, count=1)

            if zom:
                items_for_specification.append(zom)

                variants = self.filter_suitable_variants_via_child(variants, zom, count=branch_qty)

        top_mount = self.get_selected_top_mount_id()
        product_family = self.get_product_family()

        if product_family.is_upper_mount_selectable:
            if not top_mount:
                self.debug.append(
                    '#Поиск DetailType: Не выбран "Выбор верхнего соединения". Пропускаем поиск подходящих исполнений.'
                )
                return None, None, None

            top_mount_item = Item.objects.get(id=top_mount)
            items_for_specification.append(top_mount_item)

            variants = self.filter_suitable_variants_via_child(variants, top_mount_item, count=1)

        if not variants.exists():
            self.debug.append('#Поиск DetailType: Не найдено ни одного подходящего исполнения.')
            return None, None, None

        variants = variants.annotate(
            stud_composition_count=Count(
                'base_parent',
                filter=Q(base_parent__base_child__in=stud_detail_types),
                distinct=True
            )
        ).order_by('stud_composition_count')

        # Циклично вычисляем системную высоту у каждого исполнения
        total_variants = variants.count()

        self.debug.append(
            f'#Поиск DetailType: Нашли {total_variants} исполнении, начинаю циклично проверять системную высоту'
        )

        for index, variant in enumerate(variants):
            self.debug.append(f'[{index + 1}/{total_variants}] {variant} (id={variant.id})')

            attribute = Attribute.objects.for_variant(variant).filter(usage=AttributeUsageChoices.SYSTEM_HEIGHT).first()
            if not attribute:
                self.debug.append(
                    f'#Поиск DetailType: У исполнения {variant} (id={variant.id}) не найден атрибут '
                    f'с использованием SYSTEM_HEIGHT. Пропускаю.'
                )
                continue

            attribute = Attribute.objects.for_variant(variant).filter(usage=AttributeUsageChoices.E_INITIAL).first()
            if not attribute:
                self.debug.append(
                    f'#Поиск DetailType: У исполнения {variant} (id={variant.id}) не найден атрибут '
                    f'с использованием E_INITIAL. Пропускаю.'
                )
                continue

            current_system_height, errors = self.calculate_system_height_without_studs(variant)

            if errors:
                self.debug.append(f'Не удалось вычислить, ошибки: {errors}. Пропускаю исполнение.')
                continue

            if current_system_height is not None:
                current_system_height = int(Decimal(str(current_system_height)).to_integral_value(rounding=ROUND_HALF_UP))

            self.debug.append(f'Вычисленная системная высота без шпилек: {current_system_height}')

            base_compositions = BaseComposition.objects.filter(
                base_parent_variant=variant,
                base_child__in=stud_detail_types,
            )
            total = base_compositions.count()

            found = False

            if desired_system_height:
                rest_system_height = float(Decimal(str(desired_system_height)) - Decimal(str(current_system_height)))
                rest_system_height = int(Decimal(str(rest_system_height)).to_integral_value(rounding=ROUND_HALF_UP))
                self.debug.append(f'Системная высота которую нужно заполнить: {rest_system_height}')

                if rest_system_height == 0:
                    self.debug.append(
                        f'Шпильки не требуется? Этот вариант подходящий. У него в базовом составе шпилек: '
                        f'{variant.stud_composition_count}. Поиск завершен.'
                    )
                    return variant, current_system_height, items_for_specification
                if rest_system_height < 0:
                    self.debug.append(f'Вычисленная системная высота больше чем нужной, пропускаем.')
                    continue

                coupling_items = self.find_couplings(variant)

                if coupling_items is None:
                    self.debug.append(f"Не нашли муфты, пропускаем.")
                    continue

                items_for_specification.extend(coupling_items)

                self.debug.append(f'#Поиск шпилька: Количество шпилек в базовом составе: {total}')
                if total == 1:
                    stud_item = self.find_one_stud(base_compositions, rest_system_height)

                    if stud_item:
                        items_for_specification.append(stud_item)
                        self.debug.append(f'Найдено подходящее исполнение с одной шпилькой. Поиск завершен.')
                        found = True
                    else:
                        continue
                elif total == 2:
                    stud_item1, stud_item2 = self.find_two_studs(variant, base_compositions, rest_system_height)

                    if stud_item1 and stud_item2:
                        items_for_specification.append(stud_item1)
                        items_for_specification.append(stud_item2)
                        self.debug.append(f'Найдено подходящее исполнение с двумя шпильками. Поиск завершен.')
                        found = True
                    else:
                        continue
                elif total == 3:
                    stud_item1, stud_item2, stud_item3 = self.find_three_studs(
                        variant, base_compositions, rest_system_height,
                    )

                    if stud_item1 and stud_item2 and stud_item3:
                        items_for_specification.append(stud_item1)
                        items_for_specification.append(stud_item2)
                        items_for_specification.append(stud_item3)
                        self.debug.append(f'Найдено подходящее исполнение с тремя шпильками. Поиск завершен.')
                        found = True
                    else:
                        continue
            else:
                self.debug.append(
                    'Пользователь не указал желаемую системную высоту, возвращаем шпилку минимальной высоты.'
                )
                self.debug.append(f'#Поиск шпилька: Количество шпилек в базовом составе: {total}')

                if not total:
                    self.debug.append(
                        f'#Поиск шпилька: У исполнения {variant} (id={variant.id}) нет базового состава с '
                        f'шпильками. Пропускаю.'
                    )
                    continue
                elif total != 1:
                    self.debug.append(
                        f'#Поиск шпилька: У исполнения {variant} (id={variant.id}) есть базовый состав с '
                        f'шпильками, но их больше одной. Пропускаю.'
                    )
                    continue

                base_composition = base_compositions[0]
                base_child = base_composition.base_child
                base_child_variant = base_composition.base_child_variant

                if base_child_variant:
                    attributes = base_child_variant.get_attributes()
                else:
                    attributes = base_child.get_attributes()

                attr = self.get_attribute_by_usage(attributes, usage=AttributeUsageChoices.LENGTH)
                if not attr:
                    self.debug.append(
                        f'#Поиск шпилька: Базовый состав={base_composition} не имеет атрибута usage=LENGTH. Пропускаю',
                    )
                    continue

                attr_name = attr.name

                # Сортируем Items по JSON полю parameters[attr_name] по возрастанию
                items = Item.objects.filter(
                    Q(type=base_child) | Q(variant=base_child_variant) if base_child_variant else Q(type=base_child)
                ).exclude(parameters__isnull=True).exclude(**{f'parameters__{attr_name}__isnull': True}).order_by(
                    f'parameters__{attr_name}'
                )

                if not items.exists():
                    self.debug.append(
                        f'#Поиск шпилька: У базового состава {base_composition} нет подходящих Items. Пропускаю.'
                    )
                    continue

                first_item = items.first()
                items_for_specification.append(first_item)
                found = True

            if not found:
                self.debug.append(
                    f'#Поиск DetailType: Не удалось найти подходящие шпильки для исполнения {variant} (id={variant.id}).'
                )
                continue

            calculated_system_height, errors = self.calculate_system_height(variant, items_for_specification)

            if errors:
                self.debug.append(f'Не удалось вычислить, ошибки: {errors}. Пропускаю исполнение.')
                continue

            # TODO: Нужно подумать, чтобы округлять не прямо в коде, а чтобы при вычислении атрибута
            if calculated_system_height is not None:
                calculated_system_height = int(
                    Decimal(str(calculated_system_height)).to_integral_value(rounding=ROUND_HALF_UP)
                )

            self.debug.append(f'Вычисленная системная высота: {calculated_system_height}')

            return variant, calculated_system_height, items_for_specification

        self.debug.append(f'#Поиск DetailType: Никаких исполнении не нашли. Завершаю поиск.')

        return None, None, None
    
    def get_parameters(self, available_options: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """
        Возвращает параметры, необходимые для создания изделия переменок.
        """
        parameters = {}

        if not available_options:
            available_options = self.get_available_options()
        
        # Диаметр трубопровода (OD)
        parameters['OD'] = self.get_pipe_diameter().id

        # Монтажный размер блока (E2)
        variant = self.get_variant()
        attr, cold_mounting_length, errors = self.calculate_cold_mounting_length(variant)
        parameters[attr.name] = cold_mounting_length

        locked_parameters = [attr.name]
        
        return parameters, locked_parameters

    def get_available_options(self) -> Dict[str, Any]:
        """
        Возвращает полную структуру доступных для выбора параметров на фронте:
        - направления и количество пружинных блоков в зависимости от расположения трубы,
        - список доступных креплений к трубе и верхних соединений,
        - подбор подходящего пружинного блока,
        - список возможных исполнений (Variant),
        - расчет высоты системы,
        - спецификация (состав изделия),
        - отладочная информация.
        """
        selected_location = self.get_selected_location()
        available_directions = self.get_available_pipe_directions(selected_location)
        available_branch_counts = self.get_available_branch_counts(selected_location)

        pipe_mounting_group = self.get_selected_pipe_mounting_group()

        if pipe_mounting_group and pipe_mounting_group.show_variants:
            available_pipe_clamps_type = "variant"
            available_pipe_clamps = self.get_available_pipe_clamp_variants(pipe_mounting_group)
        elif pipe_mounting_group:
            available_pipe_clamps_type = "item"
            available_pipe_clamps = self.get_available_pipe_clamps(pipe_mounting_group)
        else:
            available_pipe_clamps_type = "item"
            available_pipe_clamps = []

        available_top_mounts = self.get_available_top_mounts()

        suitable_variant, calculated_system_height, items_for_specification = self.get_suitable_variant()
        specification = self.get_specification(suitable_variant, items_for_specification)

        spring_block = self.get_suitable_spring_block_item()

        debug_specification = []

        if spring_block:
            debug_specification.append({
                'id': spring_block.id if spring_block else None,
                'position': None,
                'count': self.params['pipe_options']['branch_qty'],
            })
        if self.params['pipe_clamp']['pipe_mount']:
            pipe_mount, zom = self.get_pipe_mount_item()
            debug_specification.append({
                'id': self.params['pipe_clamp']['pipe_mount'],
                'position': None,
                'count': self.params["pipe_options"]["branch_qty"],
            })

            if zom:
                debug_specification.append({
                    'id': zom.id,
                    'position': None,
                    'count': self.params["pipe_options"]["branch_qty"],
                })

        if self.params['pipe_clamp']['top_mount']:
            debug_specification.append({
                'id': self.params['pipe_clamp']['top_mount'],
                'position': None,
                'count': self.params["pipe_options"]["branch_qty"],
            })

        available_options = {
            'debug': self.debug,
            'pipe_options': {
                'locations': ['horizontal', 'vertical'],
                'directions': available_directions,
                'branch_qty': available_branch_counts,
            },
            'spring_choice': self.calculate_load(),
            'pipe_params': self.get_pipe_params(),
            'pipe_clamp': {
                "pipe_mount_type": available_pipe_clamps_type,
                'pipe_mounts': available_pipe_clamps,
                'top_mount': available_top_mounts,
            },
            'suitable_variant': VariantSerializer(suitable_variant).data if suitable_variant else None,
            'calculated_system_height': calculated_system_height,
            'debug_specification': debug_specification,
            'specification': specification,
        }

        return available_options

    def get_data_for_sketch(self) -> Dict[str, Any]:
        def _num(x, ndigits: Optional[int] = None):
            if x is None:
                return None
            try:
                v = float(x)
                if not isfinite(v):
                    return None
                if ndigits is None:
                    return v
                return round(v, ndigits)
            except Exception:
                return None

        def _int(x):
            v = _num(x)
            return int(v) if v is not None else None

        def _or0(x):
            v = _num(x)
            return v if v is not None else 0.0

        temp1, temp2 = self.get_temperatures()
        pipe_d = self.get_pipe_diameter()
        od_manual = self.params["pipe_params"]["outer_diameter_special"]
        ins_thk = self.params["pipe_params"]["insulation_thickness"] or 0
        branch_qty = self.get_selected_branch_counts()

        move = self.params["load_and_move"]
        load_plus_x = _or0(move.get("load_plus_x"))
        load_plus_y = _or0(move.get("load_plus_y"))
        load_plus_z = _or0(move.get("load_plus_z"))
        load_minus_x = _or0(move.get("load_minus_x"))
        load_minus_y = _or0(move.get("load_minus_y"))
        load_minus_z = _or0(move.get("load_minus_z"))

        add_x = _or0(move.get("additional_load_x"))
        add_y = _or0(move.get("additional_load_y"))
        add_z = _or0(move.get("additional_load_z"))

        test_x = _num(move.get("test_load_x"))
        test_y = _num(move.get("test_load_y"))
        test_z = _num(move.get("test_load_z"))

        mov_px = _or0(move.get("move_plus_x"))
        mov_py = _or0(move.get("move_plus_y"))
        mov_pz = _or0(move.get("move_plus_z"))
        mov_mx = _or0(move.get("move_minus_x"))
        mov_my = _or0(move.get("move_minus_y"))
        mov_mz = _or0(move.get("move_minus_z"))

        load_plus_x += add_x
        load_plus_y += add_y
        load_plus_z += add_z
        load_minus_x += add_x
        load_minus_y += add_y
        load_minus_z += add_z

        spring = self.get_selected_spring_block()

        spring_name = spring.get("name")
        spring_size = spring.get("size")
        spring_stiffness = _num(spring.get("spring_stiffness"))
        spring_rated_stroke = _num(spring.get("rated_stroke"))
        load_cold = _num(spring.get("load_minus"))
        load_hot = _num(spring.get("hot_design_load"))
        load_initial = _num(spring.get("spring_stiffness"))

        od_effective = _num(od_manual) if od_manual is not None else (_num(pipe_d.size) if pipe_d else None)
        dn_print = f"DN {int(pipe_d.size)}" if pipe_d and _num(pipe_d.size) is not None else "-"

        up_travel_left = spring["up_range"]
        down_travel_left = spring["down_range"]

        spring_stiffness_n_per_mm = spring_stiffness

        return {
            "pipe": {
                "dn_text": dn_print,  # DN трубы
                "outer_diameter_mm": _num(od_effective, 1),  # Диам. трубы
                "insulation_thickness_mm": ins_thk,  # Толщ. изол.
                "medium_temperature_c_1": _num(temp1, 1),  # Темп. среды (1)
                "medium_temperature_c_2": _num(temp2, 1),  # (2) если заполнено
                "slope_angle_deg": 0,  # Угол наклона
            },
            "movement_mm": {
                "x_plus": _num(mov_px, 1),
                "x_minus": _num(mov_mx, 1),
                "y_plus": _num(mov_py, 1),
                "y_minus": _num(mov_my, 1),
                "z_plus": _num(mov_pz, 1),
                "z_minus": _num(mov_mz, 1),
            },
            "loads_kN": {
                "x_plus": _num(load_plus_x, 3),
                "x_minus": _num(load_minus_x, 3),
                "y_plus": _num(load_plus_y, 3),
                "y_minus": _num(load_minus_y, 3),
                "z_plus": _num(load_plus_z, 3),
                "z_minus": _num(load_minus_z, 3),
            },
            "test_loads_kN": {
                "x": _num(test_x, 3),
                "y": _num(test_y, 3),
                "z": _num(test_z, 3),
            },
            "chain_weight_kN": 0,
            "additional_weight_kN": 0,
            "spring_block": {
                "hot_load_kN": _num(load_hot, 3),  # Горяч. напр.
                "cold_load_kN": _num(load_cold, 3),  # Холод. напр.
                "stiffness_N_per_mm": spring_stiffness_n_per_mm,  # Жестк. пруж.: N/мм
                "series": spring_name,
                "size": spring_size,
                "rated_stroke_mm": spring_rated_stroke,
                "initial_load_kN": _num(load_initial, 3),
            },
            "spring_travel_reserve_mm": {
                "up": up_travel_left,  # вверх
                "down": down_travel_left  # вниз
            },
            # Диапаз. рег-ки
            "regulation_range_mm": None,
            # Отклон. от Z [°]
            "deviation_from_Z_deg": None,
            # Справочная мета
            "estimated_state": self.params["load_and_move"].get("estimated_state"),
        }
