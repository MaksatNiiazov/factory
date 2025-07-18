from collections import defaultdict
from typing import Optional, List, Dict, Any, Tuple

from django.db.models import Q, QuerySet, OuterRef, Exists, Count

from catalog.choices import ComponentGroupType, Standard
from catalog.models import (
    ClampMaterialCoefficient, Material, ProductFamily, PipeMountingGroup, PipeMountingRule, PipeDiameter, LoadGroup, ComponentGroup,
    SupportDistance, SpringBlockFamilyBinding, CoveringType, ClampSelectionMatrix,
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
            'product_class': None,
            'product_family': None,
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
            'pipe_clamp': {
                'pipe_mount': None,
                'top_mount': None,
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
            return support_distance

        if support_id is not None:
            support_obj = SupportDistance.objects.filter(id=support_id).first()

            if support_obj:
                return support_obj.id

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

        product_family = self.get_selected_product_family()

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

        if not self.params['product_family'] or self.params['pipe_options']['direction'] not in ['x', 'y', 'z']:
            self.debug.append(
                '#Тип крепления к трубе: Не выбран семейство изделии или направление трубы не "X" или "Y" или "Z".')
            return PipeMountingGroup.objects.none()

        rule = PipeMountingRule.objects.filter(
            family=self.params['product_family'],
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
        branch_qty = self.params['pipe_options']['branch_qty']

        if branch_qty > 1:
            is_support_distance_available = True
        else:
            is_support_distance_available = False

        pipe_mounting_groups = self.get_pipe_mounting_groups()

        return {
            'pipe_mounting_groups': list(pipe_mounting_groups.values_list('id', flat=True)),
            'is_support_distance_available': is_support_distance_available,
        }

    def get_pipe_mount_item(self) -> Optional[Item]:
        """
        Вовзращает выбранный элемент крепления к трубе (Item) по ID из параметров.
        Если ID не указан - возвращает None.
        """
        pipe_mount_id = self.params['pipe_clamp']['pipe_mount']

        if pipe_mount_id:
            pipe_mount = Item.objects.get(id=pipe_mount_id)
            return pipe_mount

        return None

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

    def get_selected_top_mount_id(self) -> Optional[int]:
        return self.params['pipe_clamp']['top_mount']

    def get_selected_product_family(self) -> Optional[ProductFamily]:
        """
        Возвращает объект семейства изделий (ProductFamily) по выбранному идентификатору.
        Если идентификатор не задан - возвращает None.
        """
        if not self.params['product_family']:
            return None

        return ProductFamily.objects.get(id=self.params['product_family'])

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
            f'parameters__{load_group_attribute.name}__in': load_group_ids,
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
        
        top_mount_item = self.get_top_mount_item()
        found_items = pipe_clamps.filter(**filter_params)
        self.debug.append(f'#Выбор крепления к трубе: Фильтрую по параметрам: {filter_params}')

        if not top_mount_item:
            self.debug.append(f'#Выбор крепления к трубе: Не выбрано верхнее крепление. Возвращаю найденные хомуты: {found_items.count()}')
            return list(found_items.values_list('id', flat=True))
        
        self.debug.append(f'#Проверяем совместимость хомутов с верхним креплением {top_mount_item.name} (id={top_mount_item.id})')
        top_attributes = top_mount_item.variant.get_attributes()
        load_group_attribute = self.get_load_group_attribute(top_attributes)

        if not load_group_attribute:
            self.debug.append(
                '#Выбор крепления к трубе: Не найден атрибут LoadGroup у верхнего крепления. Не могу найти подходящие хомуты.'
            )
            return []
        
        hanger_lgv = LoadGroup.objects.get(id=top_mount_item.parameters[load_group_attribute.name]).lgv

        matrix = ClampSelectionMatrix.objects.filter(
            product_family=self.get_selected_product_family(),
            detail_types=variant.detail_type,
        ).prefetch_related("entries").first()

        if not matrix:
            self.debug.append(f"#Выбор крепления к трубе: Не найден матрица выбора хомутов для семейства {self.get_selected_product_family()}.")
            return []
        
        load_group_attributes = self.get_load_group_attributes(attributes)
        compatible_item_ids = []

        for item in found_items:
            load_group_ids = [item.parameters[lg_attr.name] for lg_attr in load_group_attributes]
            clamp_lgvs = LoadGroup.objects.filter(id__in=load_group_ids).values_list('lgv', flat=True)

            if self.clamp_is_compatible(matrix=matrix, hanger_lg=hanger_lgv, clamp_lgs=clamp_lgvs):
                compatible_item_ids.append(item.id)

        self.debug.append(f"#После проверки по матрице осталось {len(compatible_item_ids)} хомут(ов)")
        return compatible_item_ids

    def get_available_pipe_clamps(self) -> List[int]:
        """
        Возвращает список ID подходящих креплений к трубе (Item), включая хомуты, башмаки и при необходимости - траверсы.
        Фильтрация выполняется по типа крепления, материалу, DN, нагрузочной группе, толщине изоляции, монтажному размеру.
        """
        self.debug.append('#Выбор крепления к трубе: Начинаю процесс поиска.')
        if not self.params['pipe_params']['pipe_mounting_group']:
            self.debug.append('#Выбор крепления к трубе: Не выбран тип крепления к трубе.')
            return []

        pipe_clamps = Item.objects.all()
        self.debug.append(f'#Выбор крепления к трубе: Этап 1, получаю все айтемы {pipe_clamps.count()}')
        pipe_mounting_group = PipeMountingGroup.objects.get(id=self.params['pipe_params']['pipe_mounting_group'])
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
        if not self.params['product_family']:
            self.debug.append(
                '#Выбор верхнего соединения: Не выбран семейство изделии для списка "Выбор верхнего соединения". '
                'Возвращаем пустой список.'
            )
            return []

        family = ProductFamily.objects.get(id=self.params['product_family'])

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

        product_family = self.get_selected_product_family()

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

    def calculate_system_height(self, variant: Variant) -> Tuple[Optional[float], Optional[Dict]]:
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

        children = []
        spring_block = self.get_suitable_spring_block_item()

        if spring_block:
            children.append(spring_block)

        pipe_mount = self.get_pipe_mount_item()
        if pipe_mount:
            children.append(pipe_mount)

        top_mount = self.get_top_mount_item()
        if top_mount:
            children.append(top_mount)

        extra_context = {}
        selected_spring = self.params['spring_choice'].get('selected_spring')
        if not selected_spring:
            return None, None

        extra_context['Fcold'] = selected_spring.get('load_minus')
        extra_context['k'] = selected_spring.get('spring_stiffness')

        value, errors = ephemeral_item.calculate_attribute(attribute, extra_context=extra_context, children=children)

        if errors:
            return None, errors

        return value, errors

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

        if not desired_system_height:
            self.debug.append('#Поиск DetailType: Пользователь не указал желаемую системную высоту.')
            return None, None, None

        spring_block = self.get_suitable_spring_block_item()
        items_for_specification = [spring_block]
        branch_qty = self.get_selected_branch_counts()

        if not spring_block:
            self.debug.append('#Поиск DetailType: Не выбран пружинный блок. Пропускаем поиск подходящих исполнений.')
            return None, None, None

        # TODO: Вынести эту логику в отдельный метод, так как ниже есть похожий код.
        spring_block_detail_types = BaseComposition.objects.filter(
            base_child=spring_block.type, count=branch_qty,
        ).values_list('base_parent', flat=True)

        spring_block_variants = BaseComposition.objects.filter(
            base_child_variant=spring_block.variant, count=branch_qty,
        ).values_list('base_parent_variant', flat=True)

        variants = Variant.objects.filter(detail_type__in=spring_block_detail_types)

        if spring_block_variants:
            variants = variants.filter(id__in=spring_block_variants)

        pipe_mount = self.get_selected_pipe_mount_id()

        if not pipe_mount:
            self.debug.append(
                '#Поиск DetailType: Не выбран "Выбор крепления к трубе". Пропускаем поиск подходящих исполнений.'
            )
            return None, None, None

        pipe_mount_item = Item.objects.get(id=pipe_mount)

        items_for_specification.append(pipe_mount)

        pipe_mount_detail_types = BaseComposition.objects.filter(
            base_child=pipe_mount_item.type, count=1,
        ).values_list('base_parent', flat=True)

        pipe_mount_variants = BaseComposition.objects.filter(
            base_child_variant=pipe_mount_item.variant, count=1,
        ).values_list('base_parent_variant', flat=True)

        variants = variants.filter(detail_type__in=pipe_mount_detail_types)

        if pipe_mount_variants:
            variants = variants.filter(id__in=pipe_mount_variants)

        top_mount = self.get_selected_top_mount_id()
        product_family = self.get_selected_product_family()

        if product_family.is_upper_mount_selectable:
            if not top_mount:
                self.debug.append(
                    '#Поиск DetailType: Не выбран "Выбор верхнего соединения". Пропускаем поиск подходящих исполнений.'
                )
                return None, None, None

            top_mount_item = Item.objects.get(id=top_mount)
            items_for_specification.append(top_mount_item)

            top_mount_detail_types = BaseComposition.objects.filter(
                base_child=top_mount_item.type,
                count=1,
            ).values_list('base_parent', flat=True)

            top_mount_variants = BaseComposition.objects.filter(
                base_child_variant=top_mount_item.variant,
                count=1,
            ).values_list('base_parent_variant', flat=True)

            variants = variants.filter(detail_type__in=top_mount_detail_types)

            if top_mount_variants:
                variants = variants.filter(id__in=top_mount_variants)

        if not variants.exists():
            self.debug.append('#Поиск DetailType: Не найдено ни одного подходящего исполнения.')
            return None, None, None

        component_group = ComponentGroup.objects.filter(group_type=ComponentGroupType.STUDS).first()

        if not component_group:
            self.debug.append('#Поиск DetailType: Не найден группа компонентов с типом "Шпильки"')
            return None, None, None

        stud_detail_types = component_group.detail_types.all()

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

            calculated_system_height, errors = self.calculate_system_height(variant)

            if errors:
                self.debug.append(f'Не удалось вычислить, ошибки: {errors}. Пропускаю исполнение.')
                continue

            if calculated_system_height is None:
                calculated_system_height = 0

            self.debug.append(f'Вычисленная системная высота: {calculated_system_height}')

            rest_system_height = desired_system_height - calculated_system_height
            self.debug.append(f'Системная высота которую нужно заполнить: {rest_system_height}')

            if rest_system_height == 0:
                self.debug.append(
                    f'Шпильки не требуется? Этот вариант подходящий. У него в базовом составе шпилек: '
                    f'{variant.stud_composition_count}. Поиск завершен.'
                )
                return variant, calculated_system_height, None
            if rest_system_height < 0:
                self.debug.append(f'Вычисленная системная высота больше чем нужной, пропускаем.')
                continue

            base_compositions = BaseComposition.objects.filter(
                base_parent_variant=variant,
                base_child__in=stud_detail_types,
            )
            total = base_compositions.count()

            self.debug.append(f'#Поиск шпилька: Количество шпилек в базовом составе: {total}')

            if not total:
                continue

            if total == 1:
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

                # Фильтруем Items, где в JSON поле parameters[attr_name] >= needed_length
                query_param = {f'parameters__{attr_name}__gte': rest_system_height}
                items = Item.objects.filter(
                    Q(type=base_child) | Q(variant=base_child_variant) if base_child_variant else Q(type=base_child)
                ).filter(**query_param)

                if items.exists():
                    items_for_specification.append(items.first())
                    self.debug.append(f'Найдено подходящее исполнение с одной шпилькой. Поиск завершен.')
                    return variant, calculated_system_height, items_for_specification
            elif total == 2:
                comp1, comp2 = base_compositions

                def get_items_and_attr_name(comp):
                    base_child = comp.base_child
                    base_child_variant = comp.base_child_variant

                    if base_child_variant:
                        attributes = base_child_variant.get_attributes()
                    else:
                        attributes = base_child.get_attributes()

                    attr = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LENGTH)
                    if not attr:
                        return None, []

                    attr_name = attr.name
                    item_qs = Item.objects.filter(
                        Q(type=base_child) | Q(variant=base_child_variant) if base_child_variant else Q(type=base_child)
                    ).exclude(parameters__isnull=True).exclude(**{f'parameters__{attr_name}__isnull': True})

                    return attr_name, list(item_qs)

                attr1, items1 = get_items_and_attr_name(comp1)
                attr2, items2 = get_items_and_attr_name(comp2)

                for it1 in items1:
                    val1 = it1.parameters.get(attr1)
                    if not isinstance(val1, (int, float)):
                        continue
                    for it2 in items2:
                        val2 = it2.parameters.get(attr2)
                        if not isinstance(val2, (int, float)):
                            continue
                        if val1 + val2 >= rest_system_height:
                            items_for_specification.append(it1)
                            items_for_specification.append(it2)
                            self.debug.append(f'Найдено подходящее исполнение с двумя шпилькой. Поиск завершен.')
                            return variant, calculated_system_height, items_for_specification
            elif total == 3:
                comp1, comp2, comp3 = base_compositions

                def get_items_and_attr_name(comp):
                    base_child = comp.base_child
                    base_child_variant = comp.base_child_variant

                    if base_child_variant:
                        attributes = base_child_variant.get_attributes()
                    else:
                        attributes = base_child.get_attributes()

                    attr = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LENGTH)
                    if not attr:
                        return None, []

                    attr_name = attr.name
                    item_qs = Item.objects.filter(
                        Q(type=base_child) | Q(variant=base_child_variant) if base_child_variant else Q(type=base_child)
                    ).exclude(parameters__isnull=True).exclude(**{f'parameters__{attr_name}__isnull': True})

                    return attr_name, list(item_qs)

                attr1, items1 = get_items_and_attr_name(comp1)
                attr2, items2 = get_items_and_attr_name(comp2)
                attr3, items3 = get_items_and_attr_name(comp3)

                for it1 in items1:
                    val1 = it1.parameters.get(attr1)
                    if not isinstance(val1, (int, float)):
                        continue

                    for it2 in items2:
                        val2 = it2.parameters.get(attr2)
                        if not isinstance(val2, (int, float)) or val2 != val1:
                            continue

                        for it3 in items3:
                            val3 = it3.parameters.get(attr3)
                            if not isinstance(val3, (int, float)):
                                continue

                            total_length = val1 + val2 + val3
                            if total_length >= rest_system_height:
                                items_for_specification.append(it1)
                                items_for_specification.append(it2)
                                items_for_specification.append(it3)
                                self.debug.append(f'Найдено подходящее исполнение с тремя шпилькой. Поиск завершен.')
                                return variant, calculated_system_height, items_for_specification

            self.debug.append(f'Не подходит, иду к следующему исполнению.')

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
        parameters['OD'] = self.get_nominal_diameter_size()

        # Монтажный размер (E)
        parameters['E'] = available_options['calculated_system_height']

        locked_parameters = ['E']
        
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

        available_pipe_clamps = self.get_available_pipe_clamps()
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
            debug_specification.append({
                'id': self.params['pipe_clamp']['pipe_mount'],
                'position': None,
                'count': 1,
            })
        if self.params['pipe_clamp']['top_mount']:
            debug_specification.append({
                'id': self.params['pipe_clamp']['top_mount'],
                'position': None,
                'count': 1,
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
                'pipe_mounts': available_pipe_clamps,
                'top_mount': available_top_mounts,
            },
            'suitable_variant': VariantSerializer(suitable_variant).data if suitable_variant else None,
            'calculated_system_height': calculated_system_height,
            'debug_specification': debug_specification,
            'specification': specification,
        }

        return available_options
