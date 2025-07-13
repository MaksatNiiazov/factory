from copy import copy
from typing import Optional, List, Dict, Any, Tuple

from django.db.models import Q, OuterRef, Exists, Count

from constance import config

from catalog.models import (
    PipeDiameter, SupportDistance, PipeMountingGroup, PipeMountingRule, Material, SSBCatalog,
)

from ops.api.constants import FN_ON_REQUEST
from ops.api.serializers import VariantSerializer
from ops.choices import AttributeUsageChoices
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
            self.debug.append(f'Не найдено расстояние между опорами трубы с id={support_distance_id}. Возможно оно было удалено.')
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

        # TODO: Проверить что будет если pipe_diameter_size_manual указан
        pipe_diameter = PipeDiameter.objects.filter(id=self.params['pipe_params']['pipe_diameter']).first()

        if not pipe_diameter:
            self.debug.append("#Список креплений A: Не выбран или не найден диаметр трубы. Поиск невозможен.")
            return []

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

            # Найти хомута по нагрузке и диаметру трубы
            if self.is_clamp(attributes):
                # Это хомут
                self.debug.append(f"#Список креплений A: Исполнение {variant} является хомутом")
                load_attribute = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LOAD)
                pipe_diameter_attribute = self.get_pipe_diameter_attribute(attributes)

                filter_params = {
                    'variant': variant,
                    f'parameters__{load_attribute.name}': self.get_load(),
                    f'parameters__{pipe_diameter_attribute.name}': pipe_diameter.id,
                }
                clamp_items = list(items.filter(**filter_params).values_list('id', flat=True))

                self.debug.append(f"#Список креплений A: Найдено {len(clamp_items)} хомутов для исполнения {variant}")
                found_items.extend(clamp_items)

        if not found_items:
            self.debug.append("#Список креплений A: Не найдено подходящих хомутов.")
            return []

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
                    f'parameters__{load_attribute.name}__lte': self.get_load(),
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

                filter_params = {
                    f'parameters__{load_attribute.name}': check_load,
                    f'parameters__{rated_stroke_attribute.name}': rated_stroke_value,
                }

                item = Item.objects.filter(variant=variant_to_check).filter(**filter_params).first()

                if item:
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

    def get_suitable_variant(self):
        """
        Выполняет пошаговый подбор подходящего Variant (исполнений) изделия
        на основе выбранных компонентов.
        """
        load = self.get_load()

        if not load:
            self.debug.append('Не задана пользовательская нагрузка. Поиск исполнения изделия невозможен.')
            return None, None, None

        sn_margin = self.get_sn_margin()

        if not sn_margin:
            self.debug.append('Не задано перемещение с запасом. Поиск исполнения изделия невозможен.')
            return None, None, None

        shock_counts = self.get_shock_counts()

        if not shock_counts:
            self.debug.append('Не задано количество амортизаторов. Поиск исполнения изделия невозможен.')
            return None, None, None

        installation_length = self.get_installation_length()

        base_items_for_specification = []
        required_base_composition = 0
        suitable_variants = Variant.objects.all()

        pipe_clamp_a = self.get_pipe_clamp_a()

        if not pipe_clamp_a and self.is_clamp_a_required():
            self.debug.append('#Поиск исполнения изделия: Не выбран крепление A.')
            return None, None, None

        if pipe_clamp_a:
            base_items_for_specification.append(pipe_clamp_a)
            required_base_composition += 1
            pipe_clamp_a_variants = BaseComposition.objects.filter(
                Q(base_child=pipe_clamp_a.type) | Q(base_child_variant=pipe_clamp_a.variant), count=1,
            ).values_list('base_parent_variant', flat=True)
            suitable_variants = suitable_variants.filter(id__in=pipe_clamp_a_variants)

        pipe_clamp_b = self.get_pipe_clamp_b()

        if not pipe_clamp_b and self.is_clamp_b_required():
            self.debug.append('#Поиск исполнения изделия: Не выбран крепление B.')
            return None, None, None

        if pipe_clamp_b:
            base_items_for_specification.append(pipe_clamp_b)
            required_base_composition += 1

            pipe_clamp_b_variants = BaseComposition.objects.filter(
                Q(base_child=pipe_clamp_b.type) | Q(base_child_variant=pipe_clamp_b.variant), count=1,
            ).values_list('base_parent_variant', flat=True)
            suitable_variants = suitable_variants.filter(id__in=pipe_clamp_b_variants)

        has_load_attr = Attribute.objects.filter(
            Q(variant=OuterRef('pk')) | Q(detail_type=OuterRef('detail_type')),
            usage=AttributeUsageChoices.LOAD,
        )
        has_rated_stroke_attr = Attribute.objects.filter(
            Q(variant=OuterRef('pk')) | Q(detail_type=OuterRef('detail_type')),
            usage=AttributeUsageChoices.RATED_STROKE,
        )

        self.debug.append('#Поиск исполнения изделия: Проверяем чтобы в базовом составе был гидроамортизатор с атрибутами LOAD и RATED_STROKE.')
        shock_variants = Variant.objects.annotate(
            has_load_attr=Exists(has_load_attr),
            has_rated_stroke_attr=Exists(has_rated_stroke_attr),
        ).filter(
            has_load_attr=True,
            has_rated_stroke_attr=True,
        )

        if shock_variants.exists():
            required_base_composition += 1
            shock_parent_variants = BaseComposition.objects.filter(
                Q(base_child__variants__in=shock_variants) | Q(base_child_variant__in=shock_variants), count=shock_counts,
            ).values_list('base_parent_variant', flat=True)
            suitable_variants = suitable_variants.filter(id__in=shock_parent_variants)
        else:
            self.debug.append(f'#Поиск исполнения изделия: Не найдено подходящих исполнений гидроамортизаторов с атрибутами LOAD и RATED_STROKE.')
            return None, None, None

        installation_size_attr = Attribute.objects.filter(
            Q(variant=OuterRef('pk')) | Q(detail_type=OuterRef('detail_type')),
            usage=AttributeUsageChoices.INSTALLATION_SIZE,
        )

        self.debug.append(f'#Поиск исполнения изделия: Проверяем наличие атрибута INSTALLATION_SIZE в исполнениях изделия.')
        suitable_variants = suitable_variants.annotate(
            has_installation_size_attr=Exists(installation_size_attr),
        ).filter(
            has_installation_size_attr=True,
        )

        self.debug.append(f'#Поиск исполнения изделия: Проверяем что количество в базовом составе равно {required_base_composition}.')
        suitable_variants = suitable_variants.annotate(
            base_compositions_count=Count('base_parent', filter=Q(base_parent__deleted_at=None))
        ).filter(
            base_compositions_count=required_base_composition
        )

        total_variants = suitable_variants.count()

        self.debug.append(f'Поиск исполнения изделия: Нашли {total_variants} исполнении, начинаю циклично проверять.')

        candidates = SSBCatalog.objects.filter(
            fn__gte=load,
            stroke__gte=sn_margin,
        ).exclude(fn=FN_ON_REQUEST).order_by('fn', 'stroke')

        for candidate in candidates:
            check_load = candidate.fn

            self.debug.append(f'Проверяю исполнение изделия для нагрузки {check_load} Н.')
            for index, variant in enumerate(suitable_variants):
                self.debug.append(f'[{index + 1}/{total_variants}] {variant} (id={variant.id}) (detail_type_id={variant.detail_type_id})')

                shock = self.get_shock_item(variant, check_load)

                if not shock:
                    self.debug.append(
                        'Не найден амортизатор. Пропускаем поиск этого исполнения.'
                    )
                    continue

                items_for_specification = copy(base_items_for_specification)
                items_for_specification.append(shock)
                shock_counts = self.get_shock_counts()

                mounting_length, errors = self.calculate_mounting_length(variant, items_for_specification)

                if errors:
                    self.debug.append(f'Ошибка при расчете монтажной длины: {errors}')
                    continue

                l_block = None
                if installation_length is not None:
                    l_block = installation_length - mounting_length
                    self.debug.append(f'Полная монтажная длина: {installation_length}, монтажная длина: {mounting_length}, ')
                    self.debug.append(f'Требуемая длина блока: {l_block}')

                    if l_block is None:
                        self.debug.append(f'#Подбор исполнения изделия: Нашли блок без длины: FN={check_load}, stroke={candidate.stroke}')
                        shock_result = self._build_shock_result(variant, candidate, check_load, candidate.stroke, l_block, mounting_length, type_=2)
                        self.debug.append('#Подбор исполнения изделия: Возвращаем блок без длины. Исполнение {variant} (id={variant.id}) подходит.')
                        return variant, shock_result, items_for_specification

                    if candidate.l2_min and abs(l_block - candidate.l2_min) <= 5:
                        self.debug.append(f'Нашли подходящий блок по L2_min: {candidate.l2_min}')
                        shock_result = self._build_shock_result(variant, candidate, check_load, candidate.stroke, l_block, mounting_length, type_=2)
                        self.debug.append(f'#Подбор исполнения изделия: Возвращаем блок по L2_min. Исполнение {variant} (id={variant.id}) подходит.')
                        return variant, shock_result, items_for_specification

                    if candidate.l2_max and abs(l_block - candidate.l2_max) <= 5:
                        self.debug.append(f'Нашли подходящий блок по L2_max: {candidate.l2_max}')
                        shock_result = self._build_shock_result(variant, candidate, check_load, candidate.stroke, l_block, mounting_length, type_=2)
                        self.debug.append(f'#Подбор исполнения изделия: Возвращаем блок по L2_max. Исполнение {variant} (id={variant.id}) подходит.')
                        return variant, shock_result, items_for_specification

                    l1 = (candidate.l3_min or 0) + (candidate.l4 or 0)
                    if abs(l_block - l1) <= 5:
                        self.debug.append(f'Нашли подходящий блок по L1: {l1}')
                        shock_result = self._build_shock_result(variant, candidate, check_load, candidate.stroke, l_block, mounting_length, type_=1)
                        self.debug.append(f'#Подбор исполнения изделия: Возвращаем блок по L1. Исполнение {variant} (id={variant.id}) подходит.')
                        return variant, shock_result, items_for_specification

                    # Нестандартный подбор через регулировку длины за счёт хода штока
                    if self.is_valid_by_stroke_adjustment(l_block, self.get_move(), candidate.stroke, l1):
                        self.debug.append('#Внимание: Применён нестандартный подбор с регулировкой длины за счёт хода штока!')
                        shock_result = self._build_shock_result(variant, candidate, check_load, candidate.stroke, l_block, mounting_length, type_=1)
                        self.debug.append(f'#Подбор исполнения изделия: Возвращаем нестандартный блок. Исполнение {variant} (id={variant.id}) подходит.')
                        return variant, shock_result, items_for_specification
                else:
                    if candidate.l3_min is not None and candidate.l4 is not None:
                        l_block = candidate.l3_min + candidate.l4
                        self.debug.append(f'Тип 1: стандартная длина блока (L1): {l_block}')
                        block_type = 1
                    elif candidate.l2_min is not None:
                        l_block = candidate.l2_min
                        self.debug.append(f'Тип 2: стандартная длина блока (L2_min): {l_block}')
                        block_type = 2
                    else:
                        self.debug.append('Не удалось определить стандартную длину блока (нет l3_min/l4 и l2_min).')
                        continue

                    l_final = l_block + sn_margin / 2
                    self.debug.append(f'Расчётная длина системы: {l_block} + {sn_margin}/2 = {l_final} мм')

                    shock_result = self._build_shock_result(
                        variant=variant,
                        entry=candidate,
                        fn=check_load,
                        stroke=candidate.stroke,
                        l_block=l_block,
                        mounting_length=mounting_length,
                        type_=block_type,
                    )
                    self.debug.append(f'#Подбор исполнения изделия: Возвращаем стандартный блок. Исполнение {variant} (id={variant.id}) подходит.')
                    return variant, shock_result, items_for_specification

                self.debug.append(f'Это исполнение не подходит.')

            self.debug.append(f'Не нашли никаких подходящих исполнений для нагрузки {check_load} Н. Перехожу к следующему значению FN.')
        
        self.debug.append('Не найдено подходящих исполнений для всех вариантов нагрузки.')

        return None, None, None

    def calculate_mounting_length(self, variant, items_for_specification):
        attribute = Attribute.objects.for_variant(variant).filter(
            usage=AttributeUsageChoices.INSTALLATION_SIZE
        ).first()

        ephemeral_item = Item(
            type=variant.detail_type,
            variant=variant,
            parameters={},
        )

        value, errors = ephemeral_item.calculate_attribute(attribute, children=items_for_specification)

        if errors:
            return None, errors

        return value, errors

    def is_valid_by_stroke_adjustment(self, l_block, move, stroke, standard_l) -> bool:
        """
        Проверяет, находится ли фактический диапазон длин (штока) в допустимых пределах с учетом запаса.
        """
        if None in [l_block, move, stroke, standard_l]:
            return False

        reserve_coef = config.SSB_EXTRA_MARGIN_PERCENT
        reserve_mm = stroke * reserve_coef

        l_cold = l_block
        l_hot = l_block + move

        l_real_min = min(l_cold, l_hot)
        l_real_max = max(l_cold, l_hot)

        l_min = standard_l - stroke / 2 + reserve_mm
        l_max = standard_l + stroke / 2 - reserve_mm

        self.debug.append('#Нестандартный подбор: расчет диапазона штока')
        self.debug.append(f'#Допустимый диапазона: {l_min:.2f} - {l_max:.2f} мм, фактически: {l_real_min:.2f} - {l_real_max:.2f} мм')

        return l_real_min >= l_min and l_real_max <= l_max

    def _build_shock_result(self, variant, entry, fn, stroke, l_block, mounting_length, type_):
        marking = f"{variant.detail_type.designation} {fn:04.0f}.{stroke:03.0f}.0000.{type_}"

        return {
            'marking': marking,
            'stroke': stroke,
            'type': type_,
            'extender': max(0, l_block - (entry.l2_min if type_ == 2 else (entry.l3_min + entry.l4))),
            'mounting_length': mounting_length,
            'l_req': l_block,
            'l1': entry.l1,
            'l2_min': entry.l2_min,
            'l2_max': entry.l2_max,
            'l3_min': entry.l3_min,
            'l3_max': entry.l3_max,
            'l4': entry.l4,
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
