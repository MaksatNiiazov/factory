from collections import Counter, defaultdict
from copy import copy
from typing import Optional, List, Dict, Any, Tuple

from django.db.models import Q, OuterRef, Exists, Count, Sum

from constance import config

from catalog.models import (
    PipeDiameter, SupportDistance, PipeMountingGroup, PipeMountingRule, Material, SSBCatalog,
)

from ops.api.constants import FN_ON_REQUEST
from ops.api.serializers import VariantSerializer
from ops.choices import AttributeUsageChoices, AttributeCatalog
from ops.models import Item, BaseComposition, Variant, Attribute
from ops.services.base_selection import BaseSelectionAvailableOptions


class ShockSelectionAvailableOptions(BaseSelectionAvailableOptions):
    @classmethod
    def get_default_params(cls):
        params = {
            'product_class': None,
            'product_family': None,
            'load_and_move': {
                'installation_length': None,
                'move': None,
                'load': None,
                'load_type': None,
            },
            'pipe_options': {
                'location': None,
                'shock_counts': None,
            },
            'pipe_params': {
                'temperature': None,
                'pipe_diameter': None,
                'pipe_diameter_size_manual': None,
                'support_distance': None,
                'support_distance_manual': None,
                'mounting_group_a': None,
                'mounting_group_b': None,
                'material': None,
            },
            'pipe_clamp': {
                'pipe_clamp_a': None,
                'pipe_clamp_b': None,
            },
            'variant': None,
        }
        return params

    def get_mounting_length_from_items(self) -> Optional[float]:
        """
        Возвращает суммарную монтажную длину по элементам спецификации (без исполнения).
        """
        base_items = self._get_base_items()
        if not base_items:
            self.debug.append("#get_mounting_length_from_items: Нет базовых элементов для расчёта.")
            return 0

        mounting_length = 0.0
        for item in base_items:
            variant = item.variant
            if not variant:
                continue
            attributes = variant.get_attributes()
            for attr in attributes:
                if attr.usage == AttributeUsageChoices.INSTALLATION_SIZE:
                    value = item.parameters.get(attr.name)
                    if value:
                        try:
                            mounting_length += float(value)
                        except (TypeError, ValueError):
                            self.debug.append(
                                f"#get_mounting_length_from_items: Неверное значение параметра {attr.name} у Item {item.id}")
        self.debug.append(f"#get_mounting_length_from_items: Расчётная монтажная длина = {mounting_length}")
        return mounting_length

    def get_catalog_block(self):
        """
        Возвращает первый блок, удовлетворяющий условиям:
        - fn >= заданной нагрузки
        - stroke >= заданного перемещения (с коэффициентом запаса)
        """
        required_load = self.get_load()
        required_move = self.get_move()
        installation_length = self.get_installation_length()

        if installation_length is not None:
            self.debug.append(f"#get_load_and_move: Указана монтажная длина: {installation_length} мм.")

        if required_load is None or required_move is None:
            self.debug.append("#get_load_and_move: Не заданы нагрузка или перемещение.")
            return None

        required_stroke = required_move * config.SSB_SN_MARGIN_COEF

        candidates_by_load = SSBCatalog.objects.filter(
            fn__gte=required_load
        ).exclude(fn=FN_ON_REQUEST).order_by("fn", "stroke")

        grouped_by_fn = {}
        for c in candidates_by_load:
            grouped_by_fn.setdefault(c.fn, []).append(c)

        for fn, group in grouped_by_fn.items():
            self.debug.append(f"#get_load_and_move: Проверяем группу с нагрузкой FN = {fn}")

            for block in group:
                if block.stroke < required_stroke:
                    self.debug.append(
                        f"#get_load_and_move: Пропущен блок stroke={block.stroke} < требуемого {required_stroke}"
                    )
                    continue

                # Временный расчёт монтажной длины без учёта исполнения
                mounting_length = self.get_mounting_length_from_items() or 0
                l_cold = installation_length - mounting_length if installation_length is not None else None

                if l_cold is None:
                    self.debug.append(
                        f"#get_load_and_move: Не указана installation_length, блок выбран без проверки длины.")
                    return block

                # Проверка типа 2
                if block.l2_min and block.l2_max and block.l2_min <= l_cold <= block.l2_max:
                    self.debug.append(
                        f"#get_load_and_move: Найден подходящий блок с типом 2: {block.l2_min} ≤ {l_cold} ≤ {block.l2_max}"
                    )
                    return block

                # Проверка типа 1
                if block.l and block.f:
                    l1 = block.l + block.f
                    if l_cold <= l1 + 5:
                        self.debug.append(
                            f"#get_load_and_move: Найден подходящий блок с типом 1: {l_cold} <= {l1} + 5"
                        )
                        return block

            self.debug.append(
                f"#get_load_and_move: Для FN = {fn} нет подходящего блока по длине. Переход к следующей нагрузке.")

        self.debug.append("#get_load_and_move: Не найдено подходящего блока.")
        return None

    def get_installation_length(self) -> Optional[int]:
        """
        Возвращает значение монтажной длины из параметров.
        Если значение не указано, возвращает None.
        """
        return self.params['load_and_move']['installation_length']

    def get_move(self) -> Optional[int]:
        """
        Возвращает значение перемещение (Sn).
        Если значение не указано, возвращает None.
        """
        return self.params['load_and_move']['move']

    def get_load(self) -> Optional[float]:
        """
        Возвращает значение нагрузки с учетом типа нагрузки.

        Метод определяет тип нагрузки и вычисляет значение нагрузки
        в зависимости от указанного типа. Если тип нагрузки или
        значение нагрузки не указаны, возвращает None и добавляет
        соответствующее сообщение в список отладочных сообщений.

        Возвращаемое значение:
            Optional[float]: Значение нагрузки, скорректированное
            в зависимости от типа нагрузки, или None, если данные
            некорректны.

        Тип нагрузки:
            - 'hz': нагрузка делится на 1.5.
            - 'hs': нагрузка делится на 1.7.

        Исключительные случаи:
            - Если тип нагрузки не указан, добавляется сообщение
              "Не указан тип нагрузки." в список отладочных сообщений.
            - Если значение нагрузки не указано, добавляется сообщение
              "Не указан нагрузка." в список отладочных сообщений.
        """
        load_type = self.get_load_type()

        if not load_type:
            self.debug.append(f'Не указан тип нагрузки.')
            return None

        load: Optional[float] = self.params['load_and_move']['load']

        if not load:
            self.debug.append(f'Не указан нагрузка.')
            return None

        if load_type == 'hz':
            load = load / 1.5
        elif load_type == 'hs':
            load = load / 1.7

        shock_counts = self.get_shock_counts()

        if shock_counts and shock_counts > 1:
            load = load / shock_counts

        return load

    def get_load_type(self) -> Optional[str]:
        return self.params['load_and_move']['load_type']

    def get_available_load_types(self) -> List[str]:
        """
        Возвращает список доступных типов нагрузки.
        """
        return ['h', 'hz', 'hs']

    def get_pipe_location(self) -> Optional[str]:
        return self.params['pipe_options']['location']

    def get_available_pipe_locations(self):
        return ['horizontal', 'vertical']

    def get_shock_counts(self) -> Optional[int]:
        return self.params['pipe_options']['shock_counts']

    def get_available_shock_counts(self):
        location = self.params['pipe_options']['location']

        if location == 'vertical':
            return [2]
        elif location == 'horizontal':
            return [1, 2]

        return []

    def get_temperature(self):
        return self.params['pipe_params']['temperature']

    def get_pipe_diameter_size(self) -> Optional[float]:
        """
        Возвращает диаметр трубы в миллиметрах.
        """
        manual_size = self.params['pipe_params']['pipe_diameter_size_manual']

        if manual_size is not None:
            return manual_size

        pipe_diameter_id = self.params['pipe_params']['pipe_diameter']

        if pipe_diameter_id is None:
            return None

        pipe_diameter = PipeDiameter.objects.filter(id=pipe_diameter_id).first()

        if not pipe_diameter:
            self.debug.append(f'Не найден диаметр трубы с id={pipe_diameter_id}. Возможно он был удален.')
            return None

        return pipe_diameter.size

    def get_available_pipe_diameters(self):
        pipe_diameters = PipeDiameter.objects.all()
        return pipe_diameters

    def get_support_distance(self) -> Optional[float]:
        """
        Возвращает расстояние между опорами трубы в миллиметрах.
        """
        support_distance_manual = self.params['pipe_params']['support_distance_manual']

        if support_distance_manual is not None:
            return support_distance_manual

        support_distance_id = self.params['pipe_params']['support_distance']

        if support_distance_id is None:
            return None

        support_distance = SupportDistance.objects.filter(id=support_distance_id).first()

        if not support_distance:
            self.debug.append(
                f'Не найдено расстояние между опорами трубы с id={support_distance_id}. Возможно оно было удалено.')
            return None

        return support_distance.value

    def get_available_support_distances(self):
        support_distances = SupportDistance.objects.all()
        return support_distances

    def get_available_mounting_groups_a(self):
        """
        Получает доступные группы креплений A на основе параметров.
        """
        if not self.params['product_family']:
            self.debug.append('#Тип крепления A: Не выбран семейство изделии')
            return PipeMountingGroup.objects.none()

        if not self.params['pipe_options']['shock_counts']:
            self.debug.append('#Тип крепления A: Не выбран количество амортизаторов')

        if not self.params['pipe_options']['location']:
            self.debug.append('#Тип крепления A: Не выбран направление трубы')
            return PipeMountingGroup.objects.none()

        rules = PipeMountingRule.objects.filter(
            family=self.params['product_family'],
            num_spring_blocks=self.params['pipe_options']['shock_counts'],
        )

        location = self.params['pipe_options']['location']

        if location == 'horizontal':
            rule = rules.filter(pipe_direction__in=['x', 'y']).first()
        elif location == 'vertical':
            rule = rules.filter(pipe_direction='z').first()
        else:
            self.debug.append('#Тип крепления A: Неверное направление трубы.')
            return PipeMountingGroup.objects.none()

        if not rule:
            self.debug.append('#Тип крепления A: Отсутствует "Правила выбора крепления".')
            return PipeMountingGroup.objects.none()

        pipe_mounting_groups = rule.pipe_mounting_groups.all()

        return pipe_mounting_groups

    def get_available_mounting_groups_b(self):
        """
        Получает доступные группы креплений B на основе параметров.
        """
        if not self.params['product_family']:
            self.debug.append('#Тип крепления B: Не выбран семейство изделии')
            return PipeMountingGroup.objects.none()

        family = self.get_product_family()

        if not family.is_upper_mount_selectable:
            self.debug.append(
                '#Тип крепления B: Должен быть выбран "Доступен выбор верхнего крепления" в семейство изделии'
            )
            return PipeMountingGroup.objects.none()

        if not self.params['pipe_options']['shock_counts']:
            self.debug.append('#Тип крепления B: Не выбран количество амортизаторов')
            return PipeMountingGroup.objects.none()

        if not self.params['pipe_options']['location']:
            self.debug.append('#Тип крепления B: Не выбран направление трубы')
            return PipeMountingGroup.objects.none()

        rules = PipeMountingRule.objects.filter(
            family=self.params['product_family'],
            num_spring_blocks=self.params['pipe_options']['shock_counts'],
        )

        location = self.params['pipe_options']['location']

        if location == 'horizontal':
            rule = rules.filter(pipe_direction__in=['x', 'y']).first()
        else:
            rule = rules.filter(pipe_direction='z').first()

        if not rule:
            self.debug.append('#Тип крепления B: Отсутствует "Правила выбора крепления".')
            return PipeMountingGroup.objects.none()

        mounting_groups_b = rule.mounting_groups_b.all()

        return mounting_groups_b

    def get_available_materials(self):
        materials = Material.objects.all()
        return materials

    def is_clamp(self, attributes: List[Attribute]) -> bool:
        """
        Проверяет, является ли деталь хомутом по атрибутам.
        """
        found_load = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LOAD)
        found_pipe_diameter = self.get_pipe_diameter_attribute(attributes)

        return bool(found_load and found_pipe_diameter)

    def is_bracket(self, attributes: List[Attribute]) -> bool:
        """
        Проверяет, является ли деталь скобой по атрибутам.
        """
        found_load = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LOAD)

        return bool(found_load)

    def get_mounting_group_a(self) -> Optional[PipeMountingGroup]:
        """
        Получает группу креплений A из параметров.
        """
        mounting_group_a_id = self.params['pipe_params']['mounting_group_a']

        if not mounting_group_a_id:
            self.debug.append("Не выбрана группа креплений A.")
            return None

        mounting_group_a = PipeMountingGroup.objects.filter(id=mounting_group_a_id).first()

        if not mounting_group_a:
            self.debug.append(f"Группа креплений A с id={mounting_group_a_id} не найдена. Возможно она была удалена.")
            return None

        return mounting_group_a

    def get_mounting_group_b(self) -> Optional[PipeMountingGroup]:
        """
        Получает группу креплений B из параметров.
        """
        mounting_group_b_id = self.params['pipe_params']['mounting_group_b']

        if not mounting_group_b_id:
            self.debug.append("Не выбрана группа креплений B.")
            return None

        mounting_group_b = PipeMountingGroup.objects.filter(id=mounting_group_b_id).first()

        if not mounting_group_b:
            self.debug.append(f"Группа креплений B с id={mounting_group_b_id} не найдена. Возможно она была удалена.")
            return None

        return mounting_group_b

    def get_available_pipe_clamps_a(self) -> List[int]:
        """
        Получает список доступных креплений A для текущих параметров.
        """
        self.debug.append('#Список креплений A: Начинаю поиск доступных креплений A')

        # Получаем диаметр трубы
        pipe_diameter_id = self.params['pipe_params']['pipe_diameter']
        pipe_diameter = PipeDiameter.objects.filter(id=pipe_diameter_id).first()
        temperature = self.params['pipe_params']['temperature']

        # Кандидаты материалов по температуре
        if temperature is not None:
            materials_qs = Material.objects.filter(min_temp__lte=temperature, max_temp__gte=temperature)
            self.debug.append(
                f"#Список креплений A: Найдено {materials_qs.count()} материалов подходящих по температуре {temperature}°C"
            )
        else:
            materials_qs = Material.objects.all()
            self.debug.append(
                f"#Список креплений A: Температура не задана — будут использоваться все материалы ({materials_qs.count()} шт.)"
            )

        explicit_material_id = self.params['pipe_params'].get('material')
        if explicit_material_id:
            chosen_material_id = explicit_material_id
            self.debug.append(f"#Список креплений A: Явно выбран материал id={chosen_material_id}")
        else:
            chosen_material_id = materials_qs.values_list('id', flat=True).first()
            if chosen_material_id:
                self.debug.append(
                    f"#Список креплений A: Материал не задан — по температуре выбран id={chosen_material_id}")
            else:
                self.debug.append("#Список креплений A: Подходящих материалов не найдено")

        # Группа креплений A
        mounting_group_a = self.get_mounting_group_a()
        if not mounting_group_a:
            self.debug.append("#Список креплений A: Не выбрана группа креплений A. Поиск невозможен.")
            return []

        variants = mounting_group_a.variants.all()
        items = Item.objects.filter(variant__in=variants)

        found_items = []

        for variant in variants:
            self.debug.append(f"#Список креплений A: Проверяю исполнение {variant} (id={variant.id})")
            attributes = variant.get_attributes()

            if not attributes:
                self.debug.append(f"#Список креплений A: У варианта id={variant.id} нет атрибутов.")
                continue

            load_attribute = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LOAD)
            pipe_diameter_attribute = self.get_pipe_diameter_attribute(attributes)
            material_attr = attributes.filter(catalog=AttributeCatalog.MATERIAL).first()

            if not load_attribute:
                self.debug.append(f"#Список креплений A: У варианта {variant.id} отсутствует атрибут нагрузки.")
                continue

            load_value = self.get_load()

            # Базовый фильтр
            filter_params = {
                'variant': variant,
                f'parameters__{load_attribute.name}__gte': load_value,
            }

            # Фильтр по диаметру, если атрибут есть
            if pipe_diameter_attribute and pipe_diameter:
                filter_params[f'parameters__{pipe_diameter_attribute.name}'] = pipe_diameter.id
                self.debug.append(f"#Список креплений A: Фильтрация по диаметру = {pipe_diameter.id}")
            # Фильтр по материалу, если атрибут есть и выбран ОДИН материал
            if material_attr and chosen_material_id:
                filter_params[f'parameters__{material_attr.name}'] = chosen_material_id
                self.debug.append(
                    f"#Список креплений A: Фильтрация по диаметру = {pipe_diameter.id}"
                )
            elif material_attr and not chosen_material_id:
                self.debug.append(
                    "#Список креплений A: Атрибут материала есть, но подходящий материал не выбран — пропускаю фильтрацию по материалу")

            matched = list(items.filter(**filter_params).values_list('id', flat=True))
            self.debug.append(
                f"#Список креплений A: Найдено {len(matched)} подходящих элементов для варианта {variant}."
            )
            found_items.extend(matched)

        if not found_items:
            self.debug.append("#Список креплений A: Не найдено подходящих креплений.")
        else:
            self.debug.append(f"#Список креплений A: Итоговое количество найденных креплений: {len(found_items)}")

        return found_items

    def get_available_pipe_clamps_b(self) -> List[int]:
        """
        Получает список доступных креплений B для текущих параметров.
        """
        self.debug.append('#Список креплений B: Начинаю поиск доступных креплений B')
        mounting_group_b = self.get_mounting_group_b()

        if not mounting_group_b:
            self.debug.append("#Список креплений B: Не выбрана группа креплений B. Поиск невозможен.")
            return []

        variants = mounting_group_b.variants.all()

        items = Item.objects.filter(variant__in=variants)

        found_items = []

        for variant in variants:
            self.debug.append(f"#Список креплений B: Проверяю исполнение {variant} (id={variant.id})")
            attributes = variant.get_attributes()

            # Найти скобы по нагрузке
            if self.is_bracket(attributes):
                # Это скоба
                self.debug.append(f"#Список креплений B: Исполнение {variant} является скобой")
                load_attribute = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LOAD)

                filter_params = {
                    'variant': variant,
                    f'parameters__{load_attribute.name}__gte': self.get_load(),
                }
                bracket_items = list(items.filter(**filter_params).values_list('id', flat=True))
                self.debug.append(f"#Список креплений B: Найдено {len(bracket_items)} скоб для исполнения {variant}")
                found_items.extend(bracket_items)

        if not found_items:
            self.debug.append("#Список креплений B: Не найдено подходящих скоб.")
            return []

        return found_items

    def get_shock_item(self, variant, check_load):
        """
        Получение гидроамортизатора по нагрузке (check_load) и перемещению.
        """
        base_compositions = BaseComposition.objects.filter(base_parent_variant=variant)

        for base_composition in base_compositions:
            base_variant = base_composition.base_child_variant
            base_detail_type = base_composition.base_child

            if base_variant:
                variants_to_check = [base_variant]
            elif base_detail_type:
                variants_to_check = Variant.objects.filter(detail_type=base_detail_type)
            else:
                self.debug.append(
                    f'#Гидроамортизатор: У базового состава {base_composition} отсутствуют Variant или DetailType.'
                )
                continue

            for variant_to_check in variants_to_check:
                attributes = variant_to_check.get_attributes()
                load_attribute = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LOAD)
                rated_stroke_attribute = self.get_attribute_by_usage(attributes, AttributeUsageChoices.RATED_STROKE)

                if not load_attribute or not rated_stroke_attribute:
                    self.debug.append(
                        f'#Гидроамортизатор: У Variant {variant_to_check} отсутствуют атрибуты LOAD или RATED_STROKE.'
                    )
                    continue

                rated_stroke_value = self.get_move()

                if rated_stroke_value is None:
                    self.debug.append(
                        f'#Гидроамортизатор: Не задано значение перемещения (RATED_STROKE).'
                    )
                    return None

                catalog_block = self.get_catalog_block()

                filter_params = {
                    f'parameters__{load_attribute.name}__gte': catalog_block.fn,
                    f'parameters__{rated_stroke_attribute.name}__gte': catalog_block.stroke,
                }
                item = (
                    Item.objects
                    .filter(variant=variant_to_check)
                    .filter(**filter_params)
                    .order_by(
                        f'parameters__{load_attribute.name}',
                        f'parameters__{rated_stroke_attribute.name}'
                    )
                    .first()
                )
                if item:
                    self.debug.append(
                        f'#Гидроамортизатор: Найден Item {item.id} для Variant {variant_to_check} '
                        f'(нагрузка ≥ {check_load}, ход ≥ {rated_stroke_value})'
                    )
                    return item

                self.debug.append(
                    f'#Гидроамортизатор: Не найден Item для Variant {variant_to_check} с параметрами {filter_params}.'
                )

        self.debug.append('#Гидроамортизатор: Не найден подходящий гидроамортизатор.')
        return None

    def is_clamp_a_required(self) -> bool:
        """
        Проверяет, требуется ли крепление A на основе наличия исполнений в группе креплений A.
        """
        mounting_group_a = self.get_mounting_group_a()

        if not mounting_group_a:
            # TODO: Подумать над тем, что делать если группа креплений A не выбрана
            return True

        if mounting_group_a.variants.exists():
            return True
        else:
            self.debug.append('Крепление A не требуется, так как группа креплений A не содержит исполнений.')
            return False

    def get_pipe_clamp_a(self) -> Optional[Item]:
        """
        Получает крепление A по ID из параметров.
        """
        pipe_clamp_a_id = self.params['pipe_clamp']['pipe_clamp_a']

        if not pipe_clamp_a_id:
            return None

        pipe_clamp_a = Item.objects.filter(pk=pipe_clamp_a_id).first()

        if not pipe_clamp_a:
            self.debug.append(f'Крепление A с id={pipe_clamp_a_id} не найдено. Возможно оно было удалено.')
            return None

        return pipe_clamp_a

    def is_clamp_b_required(self) -> bool:
        """
        Проверяет, требуется ли крепление B на основе наличия исполнений в группе креплений B.
        """
        mounting_group_b = self.get_mounting_group_b()

        if not mounting_group_b:
            # TODO: Подумать над тем, что делать если группа креплений B не выбрана
            return True

        if mounting_group_b.variants.exists():
            return True
        else:
            self.debug.append('Крепление B не требуется, так как группа креплений B не содержит исполнений.')
            return False

    def get_pipe_clamp_b(self) -> Optional[Item]:
        """
        Получает крепление B по ID из параметров.
        """
        pipe_clamp_b_id = self.params['pipe_clamp']['pipe_clamp_b']

        if not pipe_clamp_b_id:
            return None

        pipe_clamp_b = Item.objects.filter(pk=pipe_clamp_b_id).first()

        if not pipe_clamp_b:
            self.debug.append(f'Крепление B с id={pipe_clamp_b_id} не найдено. Возможно оно было удалено.')
            return None

        return pipe_clamp_b

    def get_sn_margin(self) -> float:
        """
        Возвращает перемещение с запасом.
        """
        move = self.get_move()

        if move is None:
            self.debug.append('Не задано значение перемещения (Sn). Возвращаю 0.')
            return 0.0

        return abs(move) * config.SSB_SN_MARGIN_COEF

    def get_l2(self, l_cold) -> float:
        move = self.get_move()
        return l_cold - move / 2

    def get_suitable_variant(self):
        load = self.get_load()
        sn_margin = self.get_sn_margin()
        shock_counts = self.get_shock_counts()
        installation_length = self.get_installation_length()
        move = self.get_move()

        if not load:
            self.debug.append('Не задана пользовательская нагрузка. Поиск исполнения изделия невозможен.')
            return None, None, None
        if not sn_margin:
            self.debug.append('Не задано перемещение с запасом. Поиск исполнения изделия невозможен.')
            return None, None, None
        if not shock_counts:
            self.debug.append('Не задано количество амортизаторов. Поиск исполнения изделия невозможен.')
            return None, None, None

        base_items_for_specification = self._get_base_items()

        candidates = SSBCatalog.objects.filter(
            fn__gte=load,
            stroke__gte=sn_margin,
        ).exclude(fn=FN_ON_REQUEST).order_by('fn', 'stroke')

        variants = Variant.objects.filter(detail_type__product_family=self.get_product_family())
        if base_items_for_specification:
            for base_item in base_items_for_specification:
                need = getattr(base_item, 'count', 1) or 1
                variants = self.filter_suitable_variants_via_child(variants, base_item, count=need)

            # строгая проверка кратностей по базе (без shock)
            prefilt = []
            for v in variants:
                if self._check_base_counts(v, base_items_for_specification):
                    prefilt.append(v)
                else:
                    self.debug.append(
                        f'#SSB: variant id={v.id} отброшен префильтром — не хватает кратности по базовым компонентам.'
                    )
            variants = prefilt


        current_fn = None
        for fn, group in self._group_by(candidates, key=lambda c: c.fn).items():
            self.debug.append(f'=== Проверяем нагрузку FN = {fn} Н ===')
            for stroke, stroke_group in self._group_by(group, key=lambda c: c.stroke).items():
                self.debug.append(f'  -- Проверяем ход Sn = {stroke} мм --')
                for candidate in stroke_group:
                    for variant in variants:
                        self.debug.append(f'Пробуем вариант {variant} (id={variant.id})')

                        shock = self.get_shock_item(variant, fn)
                        if not shock:
                            self.debug.append('Не найден амортизатор для варианта.')
                            self.debug.append(
                                f'Отказ от блока FN={fn}, Stroke={stroke}, Variant={variant}: амортизатор не найден.')
                            continue

                        items_for_specification = copy(base_items_for_specification)
                        items_for_specification.append(shock)

                        # строгая проверка кратностей с учётом shock
                        if not self._check_base_counts(variant, items_for_specification):
                            self.debug.append(
                                f'#SSB: variant id={variant.id} отброшен — base_composition не покрывает '
                                f'базовые+shock по кратностям.'
                            )
                            continue

                        mounting_length, errors = self.calculate_mounting_length(variant, items_for_specification)
                        if errors:
                            self.debug.append(f'Ошибка расчета монтажной длины: {errors}')
                            self.debug.append('Используем монтажную длину = 0 для продолжения подбора.')
                            mounting_length = 0

                        if not self.params.get('pipe_clamp', {}).get('pipe_clamp_a') and not self.params.get(
                                'pipe_clamp', {}).get('pipe_clamp_b'):
                            block_l = installation_length if installation_length else candidate.l + candidate.f
                            type_ = 2 if candidate.l2_min and candidate.l2_max and candidate.l2_min <= block_l <= candidate.l2_max else 1
                            self.debug.append(
                                f"Крепления A и B не заданы — считаем монтажный размер только по {'L4' if type_ == 2 else 'F'} = {candidate.l4 if type_ == 2 else candidate.f}")
                        else:
                            self.debug.append(f"Крепления заданы — монтажный размер = {mounting_length}")

                        l = candidate.l or 0

                        if installation_length is not None:
                            l_cold = installation_length
                            l2 = self.get_l2(l_cold)
                            self.debug.append(
                                f'L_req = {installation_length}, монтажный размер = {mounting_length}, '
                                f'l_cold = {l_cold}'
                            )

                            # Тип 2 — проверка попадания в диапазон L2
                            if candidate.l2_min and candidate.l2_max and candidate.l2_min <= l_cold <= candidate.l2_max:
                                l4 = candidate.l4 or 0
                                self.debug.append(
                                    f'Подходит тип 2: {candidate.l2_min} ≤ {l_cold} ≤ {candidate.l2_max}')
                                return self._return_result(
                                    variant, candidate, fn, candidate.stroke, l_cold,
                                    mounting_length, l, l2, l4, type_=2,
                                    items_for_specification=items_for_specification,
                                )

                            # Тип 1 — проверка совпадения с L1
                            elif candidate.l1:
                                l1 = candidate.l1
                                l2 = self.get_l2(l_cold)
                                l4 = candidate.f or 0
                                self.debug.append(
                                    f'Проверка типа 1: L1 = L + F = {candidate.l} + {candidate.f} = {l1}')
                                if l_cold <= l1 + 5:
                                    self.debug.append(
                                        f'Подходит тип 1: {l_cold} ≤ {l1} + 5')
                                    return self._return_result(
                                        variant, candidate, fn, candidate.stroke, l_cold,
                                        mounting_length, l, l2, l4, type_=1,
                                        items_for_specification=items_for_specification
                                    )

                                if self._is_stroke_adjustment_allowed() and self.is_valid_by_stroke_adjustment(
                                        l_cold, self.get_move(), candidate.stroke, l1
                                ):
                                    self.debug.append('Применена регулировка штока — нестандартный подбор')
                                    return self._return_result(
                                        variant, candidate, fn, candidate.stroke, l_cold,
                                        mounting_length, l, l2, l4, type_=1,
                                        items_for_specification=items_for_specification
                                    )
                            self.debug.append('Ни один тип не подошёл по длине. Переход к следующему варианту.')
                            continue

                        else:
                            if candidate.l and candidate.f:
                                l_cold = candidate.l + candidate.f
                                self.debug.append(f'Тип 1: L1 = L + F = {candidate.l} + {candidate.f} = {l_cold}')
                                block_type = 1
                            elif candidate.l2_min:
                                l_cold = candidate.l2_min
                                self.debug.append(f'Тип 2: l2_min = {l_cold}')
                                block_type = 2
                            else:
                                self.debug.append('Нет данных по стандартной длине блока.')
                                continue

                            l_final = l_cold + sn_margin / 2
                            l2 = self.get_l2(l_cold)

                            self.debug.append(f'Расчётная длина системы: {l_cold} + {sn_margin}/2 = {l_final} мм')
                            result = self._build_shock_result_and_return(
                                variant=variant,
                                candidate=candidate,
                                check_load=fn,
                                stroke=candidate.stroke,
                                l_cold=l_cold,
                                mounting_length=mounting_length,
                                l=candidate.l,
                                l2=l2,
                                l4=candidate.f if block_type == 1 else candidate.l4,
                                block_type=block_type,
                                items_for_specification=items_for_specification,
                                sn_margin=sn_margin,
                            )
                            if result[0]:
                                return result

            self.debug.append(f'Для FN = {fn} не удалось подобрать блок. Переход к следующей нагрузке.')

        self.debug.append('Не найдено подходящих исполнений для всех вариантов нагрузки.')
        return None, None, None

    def calculate_mounting_length(self, variant, items_for_specification):
        mounting_length = 0

        for item in items_for_specification:
            if item.variant.detail_type.product_family == self.get_product_family():
                continue

            attributes = item.variant.get_attributes()
            for attribute in attributes:
                if attribute.usage == AttributeUsageChoices.INSTALLATION_SIZE:
                    value = item.parameters.get(attribute.name)
                    if value:
                        mounting_length += float(value)

        return mounting_length, None

    def is_valid_by_stroke_adjustment(self, l_cold, move, stroke, standard_l) -> bool:
        """
        Проверяет, находится ли фактический диапазон длин (хода штока)
        в допустимых пределах с учетом запаса.
        """
        # Если данные неполные или регулировка штоком не разрешена, возвращаем False
        if None in [l_cold, move, stroke, standard_l] or not self._is_stroke_adjustment_allowed():
            self.debug.append(
                "#Нестандартный подбор: не выполнены условия запуска — один из параметров не задан или регулировка запрещена.")
            return False

        reserve_coef = config.SSB_EXTRA_MARGIN_PERCENT
        reserve_mm = float(stroke) * reserve_coef

        l_cold = float(l_cold)
        move = float(move)

        if move < 0:
            l_hot = l_cold + abs(move)
        else:
            l_hot = l_cold - move
        l_real_min = min(l_cold, l_hot)
        l_real_max = max(l_cold, l_hot)

        l_min = float(standard_l) - float(stroke) / 2 + reserve_mm
        l_max = float(standard_l) + float(stroke) / 2 - reserve_mm

        self.debug.append("#Нестандартный подбор: расчёт диапазона штока")
        self.debug.append(f">> ВХОДНЫЕ ПАРАМЕТРЫ")
        self.debug.append(f"l_cold: {l_cold}, move: {move}, stroke: {stroke}, standard_l: {standard_l}")
        self.debug.append(f">> РАСЧЁТ")
        self.debug.append(f"reserve_mm = stroke * reserve_coef = {stroke} * {reserve_coef} = {reserve_mm:.2f}")
        self.debug.append(f"l_cold = {l_cold:.2f}")

        # Тут формируем строку в зависимости от знака move
        if move < 0:
            self.debug.append(f"l_hot = l_cold + abs(move) = {l_cold:.2f} + {abs(move):.2f} = {l_hot:.2f}")
        else:
            self.debug.append(f"l_hot = l_cold - move = {l_cold:.2f} - {move:.2f} = {l_hot:.2f}")

        self.debug.append(f"Фактический диапазон: min={l_real_min:.2f}, max={l_real_max:.2f}")
        self.debug.append(
            f"Допустимый диапазон: min = standard_l - stroke / 2 + reserve_mm = "
            f"{standard_l} - {stroke}/2 + {reserve_mm:.2f} = {l_min:.2f}"
        )
        self.debug.append(
            f"max = standard_l + stroke / 2 - reserve_mm = "
            f"{standard_l} + {stroke}/2 - {reserve_mm:.2f} = {l_max:.2f}"
        )

        is_valid = l_real_min >= l_min and l_real_max <= l_max
        self.debug.append(f">> РЕЗУЛЬТАТ ПРОВЕРКИ: {is_valid}")
        return is_valid

    def _build_shock_result(self, variant, entry, fn, stroke, l_cold, mounting_length, l, l2, l4, type_, l_final=None):
        """
        Формирует результат подбора изделия.
        """
        # Если l_final не передан — считаем его
        if l_final is None:
            if type_ == 1:
                l_final = (l_cold or 0) + (mounting_length or 0)
                self.debug.append(
                    f'L_final (тип 1): l_cold + монтажный размер = {l_cold} + {mounting_length} = {l_final}')
            elif type_ == 2:
                # Sn уже учтён в l_cold при подборе типа 2 — использовать как есть
                l_final = (l_cold or 0) + (mounting_length or 0)
                self.debug.append(
                    f'L_final (тип 2): l_cold + монтажный размер = {l_cold} + {mounting_length} = {l_final}')

        # Маркировка блока
        marking = (
            f"{variant.detail_type.designation} "
            f"{fn:04.0f}.{stroke:03.0f}.{int(l_cold):04d}.{type_}"
        )

        # Рассчитываем длину удлинителя (extender) только для типа 2, для типа 1 он = 0
        extender_length = 0
        if type_ == 2:
            l4 = entry.l4 or 0
            extender_length = l_cold - (l + l4 + mounting_length)
            self.debug.append(
                f"Расчёт удлинителя: {l_cold} - ({l} + {l4} + {mounting_length}) = {extender_length}"
            )

        return {
            'marking': marking,
            'stroke': stroke,
            'type': type_,
            'extender': extender_length,
            'mounting_length': mounting_length,
            'l_cold': l_cold,
            'l1': entry.l1,
            'l2': l2,
            'l2_min': entry.l2_min,
            'l2_max': entry.l2_max,
            'l3_min': entry.l3_min,
            'l3_max': entry.l3_max,
            'l4': entry.l4,
            'l_final': l_final,
        }

    def get_parameters(self, available_options: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """
        Возвращает параметры, необходимые для создания изделия гидроамортизатора.
        """
        parameters = {}

        if not available_options:
            available_options = self.get_available_options()

        l1 = available_options.get('shock_result', {}).get('l1', None)

        if l1 is not None:
            parameters['L1'] = l1

        return parameters, []

    def get_available_options(self):
        self.debug = []

        if not self.initialize_selection_params():
            return {
                'debug': self.debug,
                'suitable_variant': None,
                'shock_result': None,
                'specifications': [],
                'load_and_move': {
                    'load_types': self.get_available_load_types(),
                },
                'pipe_options': {
                    'locations': self.get_available_pipe_locations(),
                    'shock_counts': self.get_available_shock_counts(),
                },
                'pipe_params': {
                    'pipe_diameters': list(PipeDiameter.objects.all().values_list('id', flat=True)),
                    'support_distances': list(SupportDistance.objects.all().values_list('id', flat=True)),
                    'mounting_groups_a': [],
                    'mounting_groups_b': [],
                    'materials': list(Material.objects.all().values_list('id', flat=True)),
                },
                'pipe_clamp': {
                    'pipe_clamps_a': [],
                    'pipe_clamps_b': [],
                },
            }

        available_load_types = self.get_available_load_types()
        available_pipe_locations = self.get_available_pipe_locations()
        available_shock_counts = self.get_available_shock_counts()
        available_pipe_diameters = self.get_available_pipe_diameters()
        available_support_distances = self.get_available_support_distances()
        available_mounting_groups_a = self.get_available_mounting_groups_a()
        available_mounting_groups_b = self.get_available_mounting_groups_b()
        available_materials = self.get_available_materials()
        available_pipe_clamps_a = self.get_available_pipe_clamps_a()
        available_pipe_clamps_b = self.get_available_pipe_clamps_b()

        suitable_variant, shock_result, items_for_specification = self.get_suitable_variant()
        specification = self.get_specification(suitable_variant, items_for_specification)

        available_options = {
            'debug': self.debug,
            'load_and_move': {
                'load_types': available_load_types,
            },
            'pipe_options': {
                'locations': available_pipe_locations,
                'shock_counts': available_shock_counts,
            },
            'pipe_params': {
                'pipe_diameters': list(available_pipe_diameters.values_list('id', flat=True)),
                'support_distances': list(available_support_distances.values_list('id', flat=True)),
                'mounting_groups_a': list(available_mounting_groups_a.values_list('id', flat=True)),
                'mounting_groups_b': list(available_mounting_groups_b.values_list('id', flat=True)),
                'materials': list(available_materials.values_list('id', flat=True)),
            },
            'pipe_clamp': {
                'pipe_clamps_a': available_pipe_clamps_a,
                'pipe_clamps_b': available_pipe_clamps_b,
            },
            'suitable_variant': VariantSerializer(suitable_variant).data if suitable_variant else None,
            'shock_result': shock_result,
            'specifications': specification,
        }

        return available_options

    def initialize_selection_params(self) -> bool:
        self.debug.append('#Инициализация: начинаем проверку входных данных.')

        # Проверка product_family
        if not self.params.get('product_family'):
            self.debug.append('#Инициализация: не указано семейство изделий (product_family).')
            return False

        # Проверка количества амортизаторов
        shock_counts = self.params.get('pipe_options', {}).get('shock_counts')
        if not shock_counts:
            self.debug.append('#Инициализация: не указано количество амортизаторов (shock_counts).')
            return False

        # Проверка направления трубы
        pipe_location = self.params.get('pipe_options', {}).get('location')
        if not pipe_location:
            self.debug.append('#Инициализация: не указано направление трубы (pipe_location).')
            return False

        # Преобразование направления трубы в pipe_direction
        if pipe_location == 'horizontal':
            directions = ['x', 'y']
        elif pipe_location == 'vertical':
            directions = ['z']
        else:
            self.debug.append(f'#Инициализация: неизвестное направление трубы: {pipe_location}')
            return False

        # Поиск правила крепления
        rules = PipeMountingRule.objects.filter(
            family_id=self.params['product_family'],
            num_spring_blocks=shock_counts
        )

        rules = rules.filter(pipe_direction__in=directions)

        rule = rules.first()

        if not rule:
            self.debug.append('#Инициализация: не найдено правило PipeMountingRule для указанных параметров.')
            return False

        self.debug.append('#Инициализация: входные данные корректны, найдено правило подбора.')
        return True

    def _is_stroke_adjustment_allowed(self) -> bool:
        """
        Возвращает True, если регулировка штока разрешена для выбранного семейства изделия.
        """
        product_family = self.get_product_family()
        if product_family is None:
            self.debug.append("#Регулировка штока: семейство изделия не выбрано.")
            return False

        result = product_family.has_rod
        self.debug.append(f"#Регулировка штока разрешена: {result}")
        return result

    def _return_result(self, variant, candidate, check_load, stroke, l_cold, mounting_length, l, l2, l4, type_,
                       items_for_specification):
        """
        Унифицированный возврат результата подбора.
        """

        l_final = l_cold + mounting_length
        shock_result = self._build_shock_result(
            variant=variant,
            entry=candidate,
            fn=check_load,
            stroke=stroke,
            l_cold=l_cold,
            mounting_length=mounting_length,
            l=l,
            l2=l2,
            l4=l4,
            type_=type_,
            l_final=l_final,

        )
        self.debug.append(
            f'#Подбор исполнения изделия: Возвращаем блок тип {type_}. '
            f'Исполнение {variant} (id={variant.id}) подходит.'
        )
        return variant, shock_result, items_for_specification

    def _build_shock_result_and_return(self, variant, candidate, check_load, stroke, l_cold, mounting_length, l, l2,
                                       l4, block_type,
                                       items_for_specification, sn_margin):
        """
        Возвращает результат с расчётом L_final, если монтажная длина не задана.
        """
        if sn_margin is None:
            self.debug.append('Не указано перемещение (Sn). Невозможно рассчитать расчётную длину системы.')
            return None, None, None

        l_final = l_cold + sn_margin / 2 + mounting_length
        self.debug.append(
            f'Расчётная длина системы (без заданной монтажной длины): '
            f'l_cold + Sn/2 = {l_cold} + {sn_margin}/2  + {mounting_length} = {l_final} мм'
        )

        shock_result = self._build_shock_result(
            variant=variant,
            entry=candidate,
            fn=check_load,
            stroke=stroke,
            l4=l4,
            l=l,
            l2=l2,
            l_cold=l_cold,
            l_final=l_final,
            mounting_length=None,
            type_=block_type
        )

        self.debug.append(
            f'#Подбор исполнения изделия: Возвращаем стандартный блок. '
            f'Исполнение {variant} (id={variant.id}) подходит.'
        )
        return variant, shock_result, items_for_specification

    def _get_base_items(self) -> Optional[List[Item]]:
        """
        Получает список базовых компонентов изделия: крепления A и B.
        Используются для расчёта монтажной длины.
        """
        base_items = []

        if self.is_clamp_a_required():
            clamp_a = self.get_pipe_clamp_a()
            if clamp_a:
                base_items.append(clamp_a)
            else:
                self.debug.append('Крепление A требуется, но не найдено.')

        if self.is_clamp_b_required():
            clamp_b = self.get_pipe_clamp_b()
            if clamp_b:
                base_items.append(clamp_b)
            else:
                self.debug.append('Крепление B требуется, но не найдено.')

        return base_items

    @staticmethod
    def _group_by(items, key):
        from collections import defaultdict
        grouped = defaultdict(list)
        for item in items:
            grouped[key(item)].append(item)
        return grouped

    def _check_base_counts(self, variant: Variant, items_for_spec: List[Item]) -> bool:
        required = Counter()  # (type_id, variant_id|None) -> need
        for it in items_for_spec:
            required[(it.type_id, getattr(it, 'variant_id', None))] += getattr(it, 'count', 1) or 1

        exact = Counter()  # (type_id, variant_id) -> count
        generic = Counter()  # type_id -> count
        total_by_type = Counter()  # type_id -> count (exact + generic)

        for bc in variant.get_base_compositions():
            c = bc.count or 1
            t_id, v_id = bc.base_child_id, bc.base_child_variant_id
            total_by_type[t_id] += c
            if v_id is None:
                generic[t_id] += c
            else:
                exact[(t_id, v_id)] += c

        for (t_id, v_id), need in required.items():
            if v_id is None:
                if total_by_type[t_id] < need:
                    return False
            else:
                if exact[(t_id, v_id)] + generic[t_id] < need:
                    return False

        return True