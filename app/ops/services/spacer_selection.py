from copy import copy
from typing import Optional, List

from constance import config
from django.db.models import OuterRef, Q, Exists, Count

from catalog.models import SSGCatalog, PipeDiameter, Material, PipeMountingGroup, PipeMountingRule, SupportDistance, \
    SSBCatalog
from ops.api.constants import FN_ON_REQUEST
from ops.choices import AttributeUsageChoices
from ops.models import Item, BaseComposition, Variant, Attribute
from ops.services.base_selection import BaseSelectionAvailableOptions


class SpacerSelectionAvailableOptions(BaseSelectionAvailableOptions):
    """Подбор распорок SSG согласно ТЗ."""

    @classmethod
    def get_default_params(cls):
        """
        Возвращает структуру параметров по умолчанию.
        """
        return {
            'product_class': None,
            'product_family': None,
            'load_and_move': {
                'installation_length': None,
                'load': None,
                'load_type': None,
                'mounting_length': 0,
            },
            'pipe_options': {
                'location': None,
                'spacer_counts': None,
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

    def get_installation_length(self) -> Optional[int]:
        return self.params['load_and_move']['installation_length']

    def get_mounting_length(self) -> int:
        """
        Старый метод — возвращает ручной монтаж, если был указан.
        Используется только как fallback.
        """
        return self.params['load_and_move'].get('mounting_length') or 0

    def get_load_type(self) -> Optional[str]:
        return self.params['load_and_move']['load_type']

    def get_spacer_counts(self) -> Optional[int]:
        return self.params['pipe_options']['spacer_counts']

    def get_pipe_location(self) -> Optional[str]:
        return self.params['pipe_options']['location']

    def get_available_pipe_locations(self):
        return ['horizontal', 'vertical']

    def get_available_spacer_counts(self):
        location = self.get_pipe_location()
        if location == 'vertical':
            return [2]
        elif location == 'horizontal':
            return [1, 2]
        return []

    def get_clamp(self, key: str) -> Optional[Item]:
        """
        Получает объект Item для зажима A или B.
        """
        clamp_id = self.params.get('pipe_clamp', {}).get(key)
        if clamp_id:
            return Item.objects.filter(id=clamp_id).first()
        return None

    def get_total_mounting_length(self) -> int:
        """
        Складывает монтажные размеры зажимов A и B, если они заданы.
        """
        total = 0
        for key in ['pipe_clamp_a', 'pipe_clamp_b']:
            clamp = self.get_clamp(key)
            if clamp and clamp.mounting_size:
                self.debug.append(f'Монтажный размер {key}: {clamp.mounting_size}')
                total += clamp.mounting_size
            else:
                self.debug.append(f'Монтажный размер {key} отсутствует или 0')
        self.debug.append(f'Суммарный монтажный размер: {total}')
        return total

    def get_load(self) -> Optional[float]:
        """
        Возвращает приведённую нагрузку с учётом типа (H/HZ/HS) и количества распорок.
        """
        load_type = self.get_load_type()
        load = self.params['load_and_move']['load']

        if load_type is None or load is None:
            self.debug.append(' Не указана нагрузка или её тип')
            return None

        self.debug.append(f'Исходная нагрузка: {load}, тип: {load_type}')
        if load_type == 'hz':
            load /= 1.5
            self.debug.append(f'Нагрузка пересчитана для HZ: {load}')
        elif load_type == 'hs':
            load /= 1.7
            self.debug.append(f'Нагрузка пересчитана для HS: {load}')

        counts = self.get_spacer_counts()
        if counts and counts > 1:
            load /= counts
            self.debug.append(f'Нагрузка делится на {counts} распорки: {load}')

        return load

    def get_suitable_entry(self) -> Optional[SSGCatalog]:
        """
        Подбирает подходящий элемент из таблицы SSGCatalog по нагрузке и длине.
        """
        load = self.get_load()
        if load is None:
            return None

        installation_length = self.get_installation_length()
        mount_len = self.get_total_mounting_length()
        block_length = (installation_length - mount_len) if installation_length else None

        self.debug.append(f'Длина установки: {installation_length}')
        self.debug.append(f'Длина блока (ΔL): {block_length}')

        candidates = (
            SSGCatalog.objects.filter(fn__gte=load).order_by('fn', 'l_min')
        )

        by_fn = {}
        for c in candidates:
            by_fn.setdefault(c.fn, []).append(c)

        for fn in sorted(by_fn.keys()):
            ranges = by_fn[fn]
            for entry in ranges:
                if block_length is None:
                    self.debug.append(f' Возврат первого варианта без проверки длины: fn={fn}')
                    return entry
                if entry.l_min <= block_length <= entry.l_max:
                    self.debug.append(
                        f' Найдено исполнение fn={fn}, ΔL={block_length}, диапазон=({entry.l_min}-{entry.l_max})'
                    )
                    return entry

        self.debug.append(' Не найдено подходящее исполнение')
        return None

    def get_available_load_types(self) -> List[str]:
        """
        Возвращает список доступных типов нагрузки.
        """
        return ['h', 'hz', 'hs']

    def get_available_pipe_clamps_a(self) -> List[int]:
        """
        Получает список доступных креплений A для текущих параметров.
        """
        self.debug.append('#Список креплений A: Начинаю поиск доступных креплений A')

        # Получаем диаметр трубы
        pipe_diameter_id = self.params['pipe_params']['pipe_diameter']
        pipe_diameter = PipeDiameter.objects.filter(id=pipe_diameter_id).first()

        if not pipe_diameter:
            self.debug.append(
                f"#Список креплений A: Не выбран или не найден диаметр трубы с id={pipe_diameter_id}. Поиск невозможен.")
            return []

        # Получаем группу креплений A
        mounting_group_a = self.get_mounting_group_a()
        if not mounting_group_a:
            self.debug.append("#Список креплений A: Не выбрана группа креплений A. Поиск невозможен.")
            return []

        variants = mounting_group_a.variants.all()
        items = Item.objects.filter(variant__in=variants)
        found_items = []

        for variant in variants:
            self.debug.append(f"#Список креплений A: Проверяю исполнение {variant} (id={variant.id})")
            attributes = variant.detail_type.get_attributes()

            if not attributes:
                self.debug.append(f"#Список креплений A: У варианта id={variant.id} нет атрибутов.")
                continue

            if self.is_clamp(attributes):
                self.debug.append(f"#Список креплений A: Исполнение {variant} является хомутом")

                load_attribute = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LOAD)
                pipe_diameter_attribute = self.get_pipe_diameter_attribute(attributes)

                if not load_attribute or not pipe_diameter_attribute:
                    self.debug.append(
                        f"#Список креплений A: У варианта {variant.id} отсутствует нужный атрибут: "
                        f"LOAD={bool(load_attribute)}, DIAMETER={bool(pipe_diameter_attribute)}"
                    )
                    continue

                load_value = self.get_load()
                diameter_id = pipe_diameter.id

                self.debug.append(
                    f"#Список креплений A: Фильтрация по параметрам: "
                    f"{load_attribute.name}={load_value}, {pipe_diameter_attribute.name}={diameter_id}"
                )

                filter_params = {
                    'variant': variant,
                    f'parameters__{load_attribute.name}': load_value,
                    f'parameters__{pipe_diameter_attribute.name}': diameter_id,
                }

                matching_items = list(items.filter(**filter_params).values_list('id', flat=True))

                self.debug.append(
                    f"#Список креплений A: Найдено {len(matching_items)} хомутов для исполнения {variant}.")

                found_items.extend(matching_items)
            else:
                self.debug.append(f"#Список креплений A: Исполнение {variant} не является хомутом.")

        if not found_items:
            self.debug.append("#Список креплений A: Не найдено подходящих хомутов.")
        else:
            self.debug.append(f"#Список креплений A: Итоговое количество найденных хомутов: {len(found_items)}")

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
            attributes = variant.detail_type.get_attributes()

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

    def get_available_materials(self):
        materials = Material.objects.all()
        return materials

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

    def get_available_support_distances(self):
        support_distances = SupportDistance.objects.all()
        return support_distances

    def get_available_pipe_diameters(self):
        pipe_diameters = PipeDiameter.objects.all()
        return pipe_diameters

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

        self.debug.append(
            '#Поиск исполнения изделия: Проверяем чтобы в базовом составе был гидроамортизатор с атрибутами LOAD и RATED_STROKE.')
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
                Q(base_child__variants__in=shock_variants) | Q(base_child_variant__in=shock_variants),
                count=shock_counts,
            ).values_list('base_parent_variant', flat=True)
            suitable_variants = suitable_variants.filter(id__in=shock_parent_variants)
        else:
            self.debug.append(
                f'#Поиск исполнения изделия: Не найдено подходящих исполнений гидроамортизаторов с атрибутами LOAD и RATED_STROKE.')
            return None, None, None

        installation_size_attr = Attribute.objects.filter(
            Q(variant=OuterRef('pk')) | Q(detail_type=OuterRef('detail_type')),
            usage=AttributeUsageChoices.INSTALLATION_SIZE,
        )

        self.debug.append(
            f'#Поиск исполнения изделия: Проверяем наличие атрибута INSTALLATION_SIZE в исполнениях изделия.')
        suitable_variants = suitable_variants.annotate(
            has_installation_size_attr=Exists(installation_size_attr),
        ).filter(
            has_installation_size_attr=True,
        )

        self.debug.append(
            f'#Поиск исполнения изделия: Проверяем что количество в базовом составе равно {required_base_composition}.')
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
                self.debug.append(
                    f'[{index + 1}/{total_variants}] {variant} (id={variant.id}) (detail_type_id={variant.detail_type_id})')

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
                    # Вычисляем требуемую длину блока (L_req) как разность полной монтажной
                    # длины и суммарного монтажного размера крепежа:contentReference[oaicite:0]{index=0}.
                    l_block = installation_length - mounting_length
                    self.debug.append(
                        f'Полная монтажная длина: {installation_length}, '
                        f'монтажный размер крепежа: {mounting_length}, '
                        f'требуемая длина блока: {l_block}'
                    )

                    if l_block is None:
                        self.debug.append(
                            f'#Подбор исполнения изделия: Требуемая длина блока не определена '
                            f'(FN={check_load}, stroke={candidate.stroke})'
                        )
                        shock_result = self._build_shock_result(
                            variant, candidate, check_load, candidate.stroke,
                            l_block, mounting_length, type_=2
                        )
                        self.debug.append(
                            f'#Подбор исполнения изделия: Возвращаем блок без стандартной длины. '
                            f'Исполнение {variant} (id={variant.id}) подходит.'
                        )
                        return variant, shock_result, items_for_specification

                    # Проверяем попадание L_req в допустимые пределы для типа 2 (с удлинителем)
                    if candidate.l2_min is not None and candidate.l2_max is not None:
                        if candidate.l2_min <= l_block <= candidate.l2_max:
                            # Если L_req близок к границам диапазона (±5 мм), фиксируем отдельные сообщения
                            if abs(l_block - candidate.l2_min) <= 5:
                                self.debug.append(f'Нашли подходящий блок по L2_min: {candidate.l2_min}')
                            elif abs(l_block - candidate.l2_max) <= 5:
                                self.debug.append(f'Нашли подходящий блок по L2_max: {candidate.l2_max}')
                            else:
                                self.debug.append(
                                    f'Требуемая длина блока {l_block} попадает в диапазон '
                                    f'{candidate.l2_min}–{candidate.l2_max} (тип 2, с удлинителем)'
                                )
                            shock_result = self._build_shock_result(
                                variant, candidate, check_load, candidate.stroke,
                                l_block, mounting_length, type_=2
                            )
                            self.debug.append(
                                f'#Подбор исполнения изделия: Возвращаем блок тип 2 (с удлинителем). '
                                f'Исполнение {variant} (id={variant.id}) подходит.'
                            )
                            return variant, shock_result, items_for_specification

                    # Проверяем соответствие L_req стандартной длине типа 1 (L1) ±5 мм
                    l1 = (candidate.l3_min or 0) + (candidate.l4 or 0)
                    if abs(l_block - l1) <= 5:
                        self.debug.append(f'Нашли подходящий блок по L1: {l1}')
                        shock_result = self._build_shock_result(
                            variant, candidate, check_load, candidate.stroke,
                            l_block, mounting_length, type_=1
                        )
                        self.debug.append(
                            f'#Подбор исполнения изделия: Возвращаем блок тип 1 (без удлинителя). '
                            f'Исполнение {variant} (id={variant.id}) подходит.'
                        )
                        return variant, shock_result, items_for_specification

                    # Проверяем возможность нестандартного подбора за счет регулировки хода штока
                    if self._is_stroke_adjustment_allowed() and self.is_valid_by_stroke_adjustment(
                            l_block, self.get_move(), candidate.stroke, l1
                    ):
                        self.debug.append(
                            '#Внимание: Применён нестандартный подбор с регулировкой длины за счёт хода штока!'
                        )
                        shock_result = self._build_shock_result(
                            variant, candidate, check_load, candidate.stroke,
                            l_block, mounting_length, type_=1
                        )
                        self.debug.append(
                            f'#Подбор исполнения изделия: Возвращаем нестандартный блок тип 1. '
                            f'Исполнение {variant} (id={variant.id}) подходит.'
                        )
                        return variant, shock_result, items_for_specification

                else:
                    # Пользователь не задал монтажную длину – используем стандартные длины
                    if candidate.l3_min is not None and candidate.l4 is not None:
                        l_block = candidate.l3_min + candidate.l4
                        self.debug.append(f'Тип 1: стандартная длина блока (L_req): {l_block}')
                        block_type = 1
                    elif candidate.l2_min is not None:
                        l_block = candidate.l2_min
                        self.debug.append(f'Тип 2: стандартная длина блока (L2_min): {l_block}')
                        block_type = 2
                    else:
                        self.debug.append(
                            'Не удалось определить стандартную длину блока (нет l3_min/l4 и l2_min).'
                        )
                        continue

                    l_final = l_block + sn_margin / 2
                    self.debug.append(f'Расчётная длина системы: {l_block} + {sn_margin}/2 = {l_final} мм')
                    shock_result = self._build_shock_result(
                        variant=variant, entry=candidate, fn=check_load, stroke=candidate.stroke,
                        l_block=l_block, mounting_length=mounting_length, type_=block_type
                    )
                    self.debug.append(
                        f'#Подбор исполнения изделия: Возвращаем стандартный блок. '
                        f'Исполнение {variant} (id={variant.id}) подходит.'
                    )
                    return variant, shock_result, items_for_specification

                self.debug.append('Это исполнение не подходит.')

            self.debug.append(
                f'Не нашли никаких подходящих исполнений для нагрузки {check_load} Н. Перехожу к следующему значению FN.')

        self.debug.append('Не найдено подходящих исполнений для всех вариантов нагрузки.')

        return None, None, None

    def get_shock_counts(self) -> Optional[int]:
        return self.params['pipe_options']['shock_counts']

    def is_clamp(self, attributes: List[Attribute]) -> bool:
        """
        Проверяет, является ли деталь хомутом по атрибутам.
        """
        found_load = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LOAD)
        found_pipe_diameter = self.get_pipe_diameter_attribute(attributes)

        return bool(found_load and found_pipe_diameter)

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

    def is_bracket(self, attributes: List[Attribute]) -> bool:
        """
        Проверяет, является ли деталь скобой по атрибутам.
        """
        found_load = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LOAD)

        return bool(found_load)

    def get_sn_margin(self) -> float:
        """
        Возвращает перемещение с запасом.
        """
        move = self.get_move()

        if move is None:
            self.debug.append('Не задано значение перемещения (Sn). Возвращаю 0.')
            return 0.0

        return abs(move) * config.SSB_SN_MARGIN_COEF

    def get_move(self) -> Optional[int]:
        """
        Возвращает значение перемещение (Sn).
        Если значение не указано, возвращает None.
        """
        return self.params['load_and_move']['move']


    def get_available_options(self):
        available_pipe_diameters = self.get_available_pipe_diameters()  #
        available_support_distances = self.get_available_support_distances()  #
        available_mounting_groups_a = self.get_available_mounting_groups_a()  #
        available_mounting_groups_b = self.get_available_mounting_groups_b()  #
        available_materials = self.get_available_materials()  #

        available_pipe_clamps_a = self.get_available_pipe_clamps_a()
        available_pipe_clamps_b = self.get_available_pipe_clamps_b()

        available_pipe_locations = self.get_available_pipe_locations()
        available_spacer_counts = self.get_available_spacer_counts()
        available_load_types = self.get_available_load_types()

        suitable_entry = self.get_suitable_entry()
        suitable_variant, shock_result, items_for_specification = self.get_suitable_variant()

        specification = self.get_specification(suitable_variant, items_for_specification)

        available_options = {
            'debug': self.debug,
            'load_and_move': {
                'load_types': available_load_types,
            },
            'pipe_options': {
                'locations': available_pipe_locations,
                'spacer_counts': available_spacer_counts,
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
            'suitable_entry': {
                'id': suitable_entry.id,
                'fn': suitable_entry.fn,
                'marking': f'SSG {suitable_entry.fn:04d}.{int(self.get_installation_length() or 0):04d}',
            } if suitable_entry else None,
            'shock_result': None,
            'specifications': specification,
        }

        return available_options
