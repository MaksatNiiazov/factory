from collections import defaultdict
from copy import copy
from typing import Optional, Dict, Any, List

from catalog.models import SSGCatalog, PipeDiameter, SupportDistance, PipeMountingGroup, PipeMountingRule, Material
from ops.api.serializers import VariantSerializer
from ops.models import Item, Variant, BaseComposition
from ops.choices import AttributeUsageChoices
from ops.services.base_selection import BaseSelectionAvailableOptions


class SpacerSelectionAvailableOptions(BaseSelectionAvailableOptions):
    """Selection logic for SSG spacers based on specification."""

    @classmethod
    def get_default_params(cls) -> Dict[str, Any]:
        params = {
            "product_class": None,
            "product_family": None,
            "load_and_move": {
                "installation_length": None,
                "load": None,
                "load_type": None,
                "mounting_length": 0,
            },
            "pipe_options": {
                "location": None,
                "spacer_counts": None,
            },
            "pipe_params": {
                "temperature": None,
                "pipe_diameter": None,
                "pipe_diameter_size_manual": None,
                "support_distance": None,
                "support_distance_manual": None,
                "mounting_group_a": None,
                "mounting_group_b": None,
                "material": None,
            },
            "pipe_clamp": {
                "pipe_clamp_a": None,
                "pipe_clamp_b": None,
            },
            "variant": None,
        }
        return params

    def get_catalog_block(self):
        """
        Возвращает первый блок, удовлетворяющий условиям:
        - fn >= заданной нагрузки
        """
        required_load = self.get_load()
        installation_length = self.get_installation_length()

        if required_load is None:
            self.debug.append("#get_load_and_move: Не задана нагрузка.")
            return None

        if installation_length is not None:
            self.debug.append(f"#get_load_and_move: Указана монтажная длина: {installation_length} мм.")

        # считаем монтажную длину как в амортизаторах: сумма INSTALLATION_SIZE у выбранных A/B
        mounting_length = self.get_mounting_length_from_items() or 0.0
        l_cold = (installation_length - mounting_length) if installation_length is not None else None

        candidates_by_load = (
            SSGCatalog.objects
            .filter(fn__gte=required_load)
            .order_by("fn")
        )

        grouped_by_fn = {}
        for c in candidates_by_load:
            grouped_by_fn.setdefault(c.fn, []).append(c)

        for fn, group in grouped_by_fn.items():
            self.debug.append(f"#get_load_and_move: Проверяем группу с нагрузкой FN = {fn}")

            for block_type in (1, 2):
                blocks = [b for b in group if b.type == block_type]
                blocks.sort(key=lambda b: (b.l_min or 0))

                for block in blocks:
                    # если L установки не задана — берём первый подходящий по FN
                    if l_cold is None:
                        self.debug.append("#get_load_and_move: installation_length не задан — возвращаем первый по FN.")
                        return block

                    if block_type == 1:
                        l1 = block.l1
                        if l1 is not None and l_cold <= l1 + 5:
                            self.debug.append(f"#get_load_and_move: Тип 1 подходит: {l_cold} ≤ {l1} + 5")
                            return block
                    else:
                        if block.l_min is not None and block.l_max is not None and block.l_min <= l_cold <= block.l_max:
                            self.debug.append(
                                f"#get_load_and_move: Тип 2 подходит: {block.l_min} ≤ {l_cold} ≤ {block.l_max}")
                            return block

            self.debug.append(f"#get_load_and_move: Для FN = {fn} по длине не подошло. Идём к следующей нагрузке.")

        self.debug.append("#get_load_and_move: Ничего не нашли.")
        return None

    def get_installation_length(self) -> Optional[int]:
        return self.params.get("load_and_move", {}).get("installation_length")

    def get_mounting_length(self) -> float:
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
            for attr in variant.get_attributes().filter(usage=AttributeUsageChoices.INSTALLATION_SIZE):
                value = item.parameters.get(attr.name)
                if value:
                    try:
                        mounting_length += float(value)
                    except (TypeError, ValueError):
                        self.debug.append(
                            f"#get_mounting_length_from_items: Неверное значение параметра {attr.name} у Item {item.id}"
                        )
        self.debug.append(f"#get_mounting_length_from_items: Расчётная монтажная длина = {mounting_length}")
        return mounting_length

    def get_load_type(self) -> Optional[str]:
        return self.params.get("load_and_move", {}).get("load_type")

    def get_spacer_counts(self) -> Optional[int]:
        return self.params.get("pipe_options", {}).get("spacer_counts")

    def get_pipe_location(self) -> Optional[str]:
        return self.params.get("pipe_options", {}).get("location")

    def get_available_pipe_locations(self):
        return ["horizontal", "vertical"]

    def get_available_spacer_counts(self):
        loc = self.get_pipe_location()
        if loc == "vertical":
            return [2]
        if loc == "horizontal":
            return [1, 2]
        return []

    def get_load(self) -> Optional[float]:
        load = self.params.get("load_and_move", {}).get("load")
        load_type = self.get_load_type()
        if load is None or load_type is None:
            self.debug.append("Не указана нагрузка или её тип")
            return None

        try:
            load = float(load)
        except (TypeError, ValueError):
            self.debug.append("Неверный формат значения нагрузки")
            return None

        # Проверка на ноль и отрицательные значения
        if load <= 0:
            self.debug.append("Нагрузка должна быть положительной")
            return None

        # Пересчёт по типу
        if load_type == "hz":
            load /= 1.5
        elif load_type == "hs":
            load /= 1.7

        # Деление на количество распорок
        count = self.get_spacer_counts()
        if count and count > 1:
            load /= count
        return load

    def get_mounting_group_a(self) -> Optional[PipeMountingGroup]:
        group_id = self.params.get("pipe_params", {}).get("mounting_group_a")
        if group_id:
            return PipeMountingGroup.objects.filter(id=group_id).first()
        return None

    def get_mounting_group_b(self) -> Optional[PipeMountingGroup]:
        group_id = self.params.get("pipe_params", {}).get("mounting_group_b")
        if group_id:
            return PipeMountingGroup.objects.filter(id=group_id).first()
        return None

    def get_available_pipe_clamps_a(self) -> List[int]:
        result = []
        group = self.get_mounting_group_a()
        if not group:
            self.debug.append("Не выбрана группа креплений A")
            return result

        diameter_id = self.params.get("pipe_params", {}).get("pipe_diameter")
        if not diameter_id:
            self.debug.append("Не задан диаметр трубы для крепления A")
            return result

        pipe_diameter = PipeDiameter.objects.filter(id=diameter_id).first()
        if not pipe_diameter:
            self.debug.append("Диаметр трубы не найден")
            return result

        load = self.get_load()
        for variant in group.variants.all():
            attributes = variant.detail_type.get_attributes()
            load_attr = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LOAD)
            diam_attr = self.get_pipe_diameter_attribute(attributes)
            if not (load_attr and diam_attr):
                continue
            items = Item.objects.filter(
                variant=variant,
                **{
                    f"parameters__{load_attr.name}__gte": load,
                    f"parameters__{diam_attr.name}": pipe_diameter.id
                }
            ).values_list("id", flat=True)
            result.extend(items)
        return list(result)

    def get_available_pipe_clamps_b(self) -> List[int]:
        result = []
        group = self.get_mounting_group_b()
        if not group:
            self.debug.append("Не выбрана группа креплений B")
            return result

        load = self.get_load()
        for variant in group.variants.all():
            attributes = variant.detail_type.get_attributes()
            load_attr = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LOAD)
            if not load_attr:
                continue
            items = Item.objects.filter(
                variant=variant,
                **{f"parameters__{load_attr.name}__gte": load}
            ).values_list("id", flat=True)
            result.extend(items)
        return list(result)

    def get_pipe_clamp_a(self) -> Optional[Item]:
        pipe_clamp_a_id = self.params.get("pipe_clamp", {}).get("pipe_clamp_a")
        if pipe_clamp_a_id:
            return Item.objects.filter(pk=pipe_clamp_a_id).first()

    def get_pipe_clamp_b(self) -> Optional[Item]:
        pipe_clamp_b_id = self.params.get("pipe_clamp", {}).get("pipe_clamp_b")
        if pipe_clamp_b_id:
            return Item.objects.filter(pk=pipe_clamp_b_id).first()

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

    def get_mounting_length_from_items(self) -> Optional[float]:
        base_items = self._get_base_items()
        if not base_items:
            return 0

        variant = self.get_variant()
        if not variant:
            self.debug.append("Не выбран variant. Не могу рассчитать монтажную длину.")
            return None

        attribute = variant.detail_type.get_attributes().filter(usage="install_size").first()
        if not attribute:
            self.debug.append("Нет атрибута монтажного размера для variant")
            return None

        ephemeral_item = Item(type=variant.detail_type, variant=variant, parameters={})
        value, errors = ephemeral_item.calculate_attribute(attribute, children=base_items)

        if errors:
            self.debug.append(f"Ошибка расчёта монтажной длины: {errors}")
            return None

        return value

    def get_suitable_entry(self) -> Optional[SSGCatalog]:
        load = self.get_load()
        if load is None:
            return None

        installation_length = self.get_installation_length()
        mounting_length = self.get_mounting_length_from_items() or 0

        if installation_length is not None:
            l_required = installation_length - mounting_length
            self.debug.append(
                f"#get_suitable_entry: Расчётная длина блока: installation_length = {installation_length}, "
                f"mounting_length = {mounting_length}, l_required = {l_required}"
            )

            fns = (
                SSGCatalog.objects
                .filter(fn__gte=load)
                .exclude(fn=None)
                .order_by("fn")
                .values_list("fn", flat=True)
                .distinct()
            )

            for fn in fns:
                self.debug.append(f"#get_suitable_entry: Проверяем FN = {fn}")
                for block_type in (1, 2):
                    candidates = (
                        SSGCatalog.objects
                        .filter(fn=fn, type=block_type)
                        .order_by("l_min")
                    )
                    for entry in candidates:
                        if entry.l_min is not None and entry.l_max is not None:
                            self.debug.append(
                                f"#get_suitable_entry: Проверка блока FN={fn}, type={block_type}, ID={entry.id}: "
                                f"{entry.l_min} ≤ {l_required} ≤ {entry.l_max}"
                            )
                            if entry.l_min <= l_required <= entry.l_max:
                                self.debug.append(
                                    f"#get_suitable_entry: Подходит блок ID={entry.id}, FN={fn}, type={block_type}")
                                return entry
                        else:
                            self.debug.append(f"#get_suitable_entry: У блока ID={entry.id} отсутствуют l_min/l_max")

            self.debug.append("#get_suitable_entry: Не найдено подходящего блока")
            return None

        return (
            SSGCatalog.objects
            .filter(fn__gte=load)
            .order_by("fn", "type", "l_min")
            .first()
        )

    def get_specification(self, variant: Variant, items, remove_empty: bool = False) -> List[Dict[str, Any]]:
        specification = super().get_specification(variant, items, remove_empty)

        existing_item_ids = {row['item'] for row in specification}
        if items:
            for it in items:
                if it.id not in existing_item_ids:
                    specification.append({
                        'detail_type': it.type_id,
                        'variant': it.variant_id,
                        'item': it.id,
                        'position': 1,
                        'material': it.parameters.get('material'),
                        'count': 1,
                    })

        return specification

    def get_available_load_types(self):
        return ["h", "hz", "hs"]

    def get_l_block_and_final(self, entry: SSGCatalog, installation_length: Optional[float],
                              mounting_length: float) -> (float, float):
        if installation_length is None:
            l_block = entry.l_min or 0
            l_final = l_block + mounting_length
        else:
            l_block = installation_length - mounting_length
            l_final = installation_length
        return round(l_block, 2), round(l_final, 2)

    def get_spacer_result(self, entry: Optional[SSGCatalog], installation_length: Optional[float],
                          mounting_length: float) -> Optional[Dict[str, Any]]:
        if not entry:
            return None

        l_block, l_final = self.get_l_block_and_final(entry, installation_length, mounting_length)

        return {
            "id": entry.id,
            "marking": f"SSG {entry.fn:04d}.{int(l_final):04d}.{entry.type}",
            "type": entry.type,
            "fn": entry.fn,
            "l_min": entry.l_min,
            "l_max": entry.l_max,
            "l1": entry.l1,
            "l2": entry.l2,
            "d": entry.d,
            "d1": entry.d1,
            "r": entry.r,
            "s": entry.s,
            "sw": entry.sw,
            "regulation": entry.regulation,
            "h": entry.h,
            "sw1": entry.sw1,
            "sw2": entry.sw2,
            "fixed_part": entry.fixed_part,
            "delta_l": entry.delta_l,
            "l_block": l_block,
            "l_final": l_final,
        }

    def get_available_pipe_diameters(self):
        pipe_diameters = PipeDiameter.objects.all()
        return pipe_diameters

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

        if not self.params.get('pipe_options', {}).get('spacer_counts'):
            self.debug.append('#Тип крепления A: Не выбран количество амортизаторов')

        if not self.params.get('pipe_options', {}).get('location'):
            self.debug.append('#Тип крепления A: Не выбран направление трубы')
            return PipeMountingGroup.objects.none()

        rules = PipeMountingRule.objects.filter(
            family=self.params['product_family'],
            num_spring_blocks=self.params.get('pipe_options', {}).get('spacer_counts'),
        )

        location = self.params.get('pipe_options', {}).get('location')

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

        if not self.params.get('pipe_options', {}).get('spacer_counts'):
            self.debug.append('#Тип крепления B: Не выбран количество амортизаторов')
            return PipeMountingGroup.objects.none()

        if not self.params.get('pipe_options', {}).get('location'):
            self.debug.append('#Тип крепления B: Не выбран направление трубы')
            return PipeMountingGroup.objects.none()

        rules = PipeMountingRule.objects.filter(
            family=self.params['product_family'],
            num_spring_blocks=self.params.get('pipe_options', {}).get('spacer_counts'),
        )

        location = self.params.get('pipe_options', {}).get('location')

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

    def get_pipe_params(self) -> Dict[str, List[int]]:
        return {
            "pipe_diameters": self.get_available_pipe_diameters(),
            "support_distances": self.get_available_support_distances(),
            "mounting_groups_a": self.get_available_mounting_groups_a(),
            "mounting_groups_b": self.get_available_mounting_groups_b(),
            "materials": self.get_available_materials(),
        }

    def get_spacer_item(self, variant, check_load, required_length: Optional[float] = None):
        """
        Получение распорки по нагрузке (check_load) и, по возможности, с учётом требуемой длины (required_length).
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
                    f'#Распорка: У базового состава {base_composition} отсутствуют Variant или DetailType.'
                )
                continue

            for variant_to_check in variants_to_check:
                attributes = variant_to_check.get_attributes()
                load_attribute = self.get_attribute_by_usage(attributes, AttributeUsageChoices.LOAD)

                if not load_attribute:
                    self.debug.append(
                        f'#Распорка: У Variant {variant_to_check} отсутствует атрибут LOAD.'
                    )
                    continue

                # Базовый фильтр по нагрузке
                qs = Item.objects.filter(
                    variant=variant_to_check,
                    **{f'parameters__{load_attribute.name}__gte': check_load}
                )

                # Попытка сузить по длине, если есть подходящий атрибут у Item.
                # Явного usage для "длины распорки" нет, поэтому пробуем эвристики:
                length_attr = (
                    # если у вас есть спец-usage — подставьте здесь
                        attributes.filter(usage=AttributeUsageChoices.SYSTEM_HEIGHT).first()
                        or attributes.filter(name__in=['L', 'L_block', 'length']).first()
                )

                if required_length is not None and length_attr:
                    # сначала пробуем >= требуемой длины (стандартный диапазон)
                    qs_len = qs.filter(**{f'parameters__{length_attr.name}__gte': required_length}) \
                        .order_by(f'parameters__{load_attribute.name}',
                                  f'parameters__{length_attr.name}')
                    item = qs_len.first()
                    if item:
                        self.debug.append(
                            f'#Распорка: Найден Item {item.id} по нагрузке и длине '
                            f'(LOAD≥{check_load}, {length_attr.name}≥{required_length}).'
                        )
                        return item

                    # если не нашлось — fallback: без ограничения по длине (сохранить прежнее поведение)
                    self.debug.append(
                        f'#Распорка: По длине ничего не нашлось, ослабляем до подбора только по нагрузке.'
                    )

                # Fallback/старый путь: только по нагрузке
                item = qs.order_by(f'parameters__{load_attribute.name}').first()
                if item:
                    self.debug.append(
                        f'#Распорка: Найден Item {item.id} по нагрузке (без учёта длины).'
                    )
                    return item

                self.debug.append(
                    f'#Распорка: Не найден Item для Variant {variant_to_check} с нагрузкой ≥ {check_load}.'
                )

        self.debug.append('#Распорка: Не найден подходящий Item.')
        return None

    def calculate_mounting_length(self, variant, items_for_specification):
        mounting_length = 0

        for item in items_for_specification:
            if item.variant.detail_type.product_family == self.get_product_family():
                continue

            for attribute in item.variant.get_attributes().filter(usage=AttributeUsageChoices.INSTALLATION_SIZE):
                value = item.parameters.get(attribute.name)
                if value:
                    mounting_length += float(value)

        return mounting_length, None

    def get_suitable_variant(self):
        load = self.get_load()
        spacer_counts = self.get_spacer_counts()
        installation_length = self.get_installation_length()

        if not load:
            self.debug.append('Не задана пользовательская нагрузка. Поиск исполнения невозможен.')
            return None, None, None

        if not spacer_counts:
            self.debug.append('Не задано количество распорок. Поиск невозможен.')
            return None, None, None

        product_family = self.get_product_family()
        if not product_family:
            self.debug.append('Не указано семейство изделия.')
            return None, None, None

        variants = Variant.objects.filter(detail_type__product_family=self.get_product_family())
        base_items_for_specification = self._get_base_items()

        for fn in sorted(set(
                SSGCatalog.objects.filter(fn__gte=load).exclude(fn=None).values_list('fn', flat=True)
        )):
            self.debug.append(f'=== Проверяем нагрузку FN = {fn} кН ===')

            for type_value in [1, 2]:
                self.debug.append(f'-- Проверка типа {type_value} --')
                group = SSGCatalog.objects.filter(fn=fn, type=type_value).order_by('l_min')

                for candidate in group:
                    for variant in variants:
                        self.debug.append(f'Проверяем вариант {variant} (id={variant.id})')

                        mounting_length, errors = self.calculate_mounting_length(variant, base_items_for_specification)
                        if errors:
                            self.debug.append(f'Ошибка расчета монтажной длины: {errors}; принимаем 0.')
                            mounting_length = 0

                        if installation_length is not None:
                            l_cold = installation_length
                            l_required = l_cold - mounting_length

                            self.debug.append(
                                f'L_req = {installation_length}, монтажный размер = {mounting_length}, '
                                f'длина распорки L = {l_required}'
                            )

                            if candidate.l_min <= l_required <= candidate.l_max:
                                # только теперь подбираем саму распорку, зная требуемую длину
                                spacer = self.get_spacer_item(variant, fn, required_length=l_required)
                                if not spacer:
                                    self.debug.append('Не найдена распорка для варианта (с учётом длины).')
                                    continue

                                items_for_specification = copy(base_items_for_specification)
                                items_for_specification.append(spacer)

                                l_final = l_cold
                                self.debug.append(
                                    f'Блок подходит по диапазону: {candidate.l_min} ≤ {l_required} ≤ {candidate.l_max}'
                                )
                                return variant, l_final, items_for_specification

                            self.debug.append('Кандидат не подошёл по длине. Переход к следующему варианту.')
                            continue

                        else:
                            block_length = candidate.l_min
                            spacer = self.get_spacer_item(variant, fn, required_length=block_length)
                            if not spacer:
                                self.debug.append('Не найдена распорка для варианта (без заданной длины).')
                                continue

                            items_for_specification = copy(base_items_for_specification)
                            items_for_specification.append(spacer)

                            l_final = block_length + mounting_length
                            self.debug.append(f'Без длины установки: берем минимальную L = {block_length}')
                            return variant, l_final, items_for_specification

                self.debug.append(f'Для FN = {fn}, тип {type_value} не удалось подобрать блок.')

        self.debug.append('Не найдено подходящих исполнений для всех вариантов нагрузки.')
        return None, None, None

    def get_specification_items(self, compositions: List[BaseComposition], variant=None) -> List[Item]:
        variant = self.get_variant()

        if not variant:
            self.debug.append('#Спецификация: Variant не указан — спецификация не может быть получена')
            return []

        items = list(
            Item.objects.filter(base_composition__in=compositions, variant=variant).distinct()
        )
        if items:
            self.debug.append(f"#Спецификация: Найдено {len(items)} Item(ов)")
        else:
            self.debug.append("#Спецификация: Список Item пуст.")
        return items

    def initialize_selection_params(self) -> bool:
        """
        Проверяет, что все необходимые параметры присутствуют и валидны.
        """
        success = True

        if not self.params.get("product_family"):
            self.debug.append("Не указано семейство изделия.")
            success = False

        if not self.get_pipe_location():
            self.debug.append("Не указано направление трубы.")
            success = False

        if not self.get_spacer_counts():
            self.debug.append("Не указано количество распорок.")
            success = False

        if self.get_load() is None:
            self.debug.append("Некорректная нагрузка или её тип.")
            success = False

        return success

    def get_available_options(self) -> Dict[str, Any]:
        """
        Возвращает все доступные варианты параметров для подбора распорок (SSG),
        а также подходящее исполнение и результат подбора (если возможно).
        """
        self.debug = []

        # Инициализируем параметры и проверяем корректность
        if not self.initialize_selection_params():
            return {
                "debug": self.debug,
                "suitable_variant": None,
                "spacer_result": None,
                "specifications": [],
                "load_and_move": {
                    "load_types": self.get_available_load_types(),
                },
                "pipe_options": {
                    "locations": self.get_available_pipe_locations(),
                    "spacer_counts": self.get_available_spacer_counts(),
                },
                "pipe_params": {
                    "pipe_diameters": list(PipeDiameter.objects.all().values_list("id", flat=True)),
                    "support_distances": list(SupportDistance.objects.all().values_list("id", flat=True)),
                    "mounting_groups_a": list(self.get_available_mounting_groups_a().values_list("id", flat=True)),
                    "mounting_groups_b": list(self.get_available_mounting_groups_b().values_list("id", flat=True)),
                    "materials": list(Material.objects.all().values_list("id", flat=True)),
                },
                "pipe_clamp": {
                    "pipe_clamps_a": [],
                    "pipe_clamps_b": [],
                },
            }

        # Подбор исполнения
        entry = self.get_suitable_entry()
        mounting_length = self.get_mounting_length() or 0
        installation_length = self.get_installation_length()

        result = self.get_spacer_result(entry, installation_length, mounting_length)
        suitable_variant, shock_result, items_for_specification = self.get_suitable_variant()

        specification = self.get_specification(suitable_variant, items_for_specification)

        return {
            "debug": self.debug,
            "suitable_variant": VariantSerializer(suitable_variant).data if suitable_variant else None,
            "spacer_result": result,
            "specifications": specification,
            "load_and_move": {
                "load_types": self.get_available_load_types(),
            },
            "pipe_options": {
                "locations": self.get_available_pipe_locations(),
                "spacer_counts": self.get_available_spacer_counts(),
            },
            "pipe_params": {
                "pipe_diameters": list(PipeDiameter.objects.all().values_list("id", flat=True)),
                "support_distances": list(SupportDistance.objects.all().values_list("id", flat=True)),
                "mounting_groups_a": list(self.get_available_mounting_groups_a().values_list("id", flat=True)),
                "mounting_groups_b": list(self.get_available_mounting_groups_b().values_list("id", flat=True)),
                "materials": list(Material.objects.all().values_list("id", flat=True)),
            },
            "pipe_clamp": {
                "pipe_clamps_a": self.get_available_pipe_clamps_a(),
                "pipe_clamps_b": self.get_available_pipe_clamps_b(),
            },
        }

    @staticmethod
    def _group_by(items, key):
        from collections import defaultdict
        grouped = defaultdict(list)
        for item in items:
            grouped[key(item)].append(item)
        return grouped
