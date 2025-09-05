from typing import Dict, Any, Optional, List
from collections import defaultdict

from ops.api.serializers import VariantSerializer
from ops.models import Variant, DetailType, Item

from catalog.models import ProductFamily

from .base_selection import BaseSelectionAvailableOptions


WVD_SELECTION_TYPE = "wvd_selection"


class WVDSelectionAvailableOptions(BaseSelectionAvailableOptions):
    """Селектор подбора табличного элемента WVD демпферов."""
    @classmethod
    def get_default_params(cls):
        """Вернуть возможные параметры для селектора."""
        return {
            "product_class": None,  # класс изделия
            "product_family": None,  # семейство изделия
            "load_and_move": {  # раздел Нагрузка и перемещение
                "load_minus_x": None,  # нагрузка горизонтальная -
                "load_minus_y": None,  # нагрузка вертикальная -
                "load_plus_x": None,  # нагрузка горизонтальная +
                "load_plus_y": None,  # нагрузка вертикальная +
                "move_minus_x": None,  # перемещение горизонтальное -
                "move_minus_y": None,  # перемещение вертикальное -
                "move_minus_d": None,  # перемещение угловое -
                "move_plus_x": None,  # перемещение горизонтальное +
                "move_plus_y": None,  # перемещение вертикальное +
                "move_plus_d": None,  # перемещение угловое +
            },
            "variant": None,
            "selected_assembly_unit": None,  # выбранный Item СБЕ
        }

    def get_available_options(self) -> Dict[str, Any]:
        """Возвращает полную структуру доступных для выбора параметров на фронте.
        Процесс:
        1) Сначала находим подходящие СБЕ демпферов по параметрам.
        2) Юзер выбирает selected_assembly_unit из листа СБЕ.
        3)
        """
        self.debug = []

        if not self.initialize_selection_params():
            return {
                "debug": self.debug,
                "suitable_variant": None,
                "assembly_units": [],
                "specification": []
            }
        assembly_units = self.get_available_assembly_units()
        if assembly_units:
            assembly_units_ids = [item.id for item in assembly_units]
        else:
            assembly_units_ids = []

        if self.params.get("selected_assembly_unit"):
            suitable_variant, items_for_specification = self.get_suitable_variant()
            specification = self.get_specification(suitable_variant, items_for_specification)
        else:
            suitable_variant = None
            specification = []

        return {
            "debug": self.debug,
            "suitable_variant": VariantSerializer(suitable_variant).data if suitable_variant else None,
            "assembly_units": assembly_units_ids,
            "specification": specification
        }

    def initialize_selection_params(self) -> bool:
        self.debug.append('#Инициализация: начинаем проверку входных данных.')
        product_family = self.params.get("product_family")
        selected_assembly_unit = self.params.get("selected_assembly_unit")

        if not product_family:
            self.debug.append("#Инициализация: не указано семейство изделий (product_family).")
            return False
        if selected_assembly_unit:
            if selected_assembly_unit not in Item.objects.filter(
                type__product_family=product_family,
                type__category=DetailType.ASSEMBLY_UNIT
            ).values_list("id", flat=True):
                self.debug.append("#Инициализация: неверный выбранный СБЕ (selected_assembly_unit).")
                return False
            if not self.calculate_load_and_move([self.get_selected_assembly_unit()]):
                self.debug.append("#Инициализация: выбранный СБЕ не подходит по параметрам (selected_assembly_unit).")
                return False

        self.debug.append("#Инициализация: входные данные корректны.")
        return True

    def get_suitable_variant(self):
        """Получить подобранный вариант."""
        selected_item = self.get_selected_assembly_unit()
        items_for_specification = [self.get_selected_assembly_unit()]

        variants = Variant.objects.all()
        # фильтр чтобы в исполнении в его базовом составе был СБЕ selected_item
        variants = self.filter_suitable_variants_via_child(variants, selected_item)

        if not variants.exists():
            self.debug.append("#Поиск DetailType: Не найдено ни одного подходящего исполнения.")
            return None, None

        total_variants = variants.count()
        self.debug.append(f"#Поиск DetailType: Нашли {total_variants} исполнений")

        # пока находим самый первый и берем от него все подходящие изделия
        for index, variant in enumerate(variants):
            self.debug.append(f"[{index + 1}/{total_variants}] {variant} (id={variant.id})")

            # ищем именно изделие, изделие именно из type исполнения
            items = Item.objects.filter(variant_id=variant.id, type=variant.detail_type)

            if not items:
                self.debug.append(f"#Поиск DetailType: У текущего исполнения нет подходящих Items. Пропускаю.")
                continue
            # first_item = items.first()  # как правило он один всегда
            # items_for_specification.append(first_item)
            self.debug.append(f"Найдено подходящее исполнение. Поиск завершен.")
            return variant, items_for_specification

        self.debug.append(f"#Поиск DetailType: Никаких исполнении не нашли. Завершаю поиск.")
        return None, None

    def get_selected_product_family(self) -> Optional[ProductFamily]:
        """Возвращает объект семейства изделий (ProductFamily) по выбранному идентификатору.
        Если идентификатор не задан - возвращает None.
        """
        if not self.params["product_family"]:
            return None
        return ProductFamily.objects.get(id=self.params["product_family"])

    def get_selected_assembly_unit(self):
        """Возвращает объект СБЕ (Item) по выбранному идентификатору.
        Если идентификатор не задан - возвращает None."""
        if not self.params["selected_assembly_unit"]:
            return None
        return Item.objects.get(id=self.params["selected_assembly_unit"])

    def calculate_load_and_move(self, items) -> list:
        """Выполняет расчёт по введённой нагрузке и перемещениям.
        Фильтрует по параметрам уже найденные items.
        """
        def _get_abs(*numbers):
            """Получить макс число по модулю (игнорируя None)."""
            existed_numbers = [n for n in numbers if n is not None]
            if not existed_numbers:
                return None
            return abs(max(existed_numbers, key=abs))

        result_items = []

        # все ранее введенные табличные значения
        load_minus_x = self.params["load_and_move"].get("load_minus_x")
        load_minus_y = self.params["load_and_move"].get("load_minus_y")
        load_plus_x = self.params["load_and_move"].get("load_plus_x")
        load_plus_y = self.params["load_and_move"].get("load_plus_y")

        move_minus_x = self.params["load_and_move"].get("move_minus_x")
        move_minus_y = self.params["load_and_move"].get("move_minus_y")
        move_minus_d = self.params["load_and_move"].get("move_minus_d")
        move_plus_x = self.params["load_and_move"].get("move_plus_x")
        move_plus_y = self.params["load_and_move"].get("move_plus_y")
        move_plus_d = self.params["load_and_move"].get("move_plus_d")

        checks = [
            ("Fh", load_minus_x, load_plus_x),
            ("Fv", load_minus_y, load_plus_y),
            ("Sh", move_minus_x, move_plus_x),
            ("Sv", move_minus_y, move_plus_y),
            ("Sa", move_minus_d, move_plus_d),
        ]

        for item in items:
            item_parameters = item.parameters

            # проверим формат
            if not item_parameters or not isinstance(item_parameters, dict):
                self.debug.append(
                    f"#Поиск Item: Не найдены параметры у Item СБЕ (id={item.id})"
                )
                continue

            # проверяем параметры по введенным значениям
            passed = True
            for param_name, minus_val, plus_val in checks:
                item_val = item_parameters.get(param_name)
                if item_val is None:  # нет значения в параметрах item
                    self.debug.append(
                        f"#Поиск Item: Не найден параметр {param_name} у Item СБЕ (id={item.id})"
                    )
                    continue

                if minus_val is not None and plus_val is not None:
                    # оба значения заданы - проверяем по модулю
                    max_mod = _get_abs(minus_val, plus_val)
                    if item_val <= max_mod:  # должно быть больше модуля обоих чисел
                        passed = False
                        break
                elif minus_val is not None:
                    if item_val >= minus_val:  # должно быть меньше - значения
                        passed = False
                        break
                elif plus_val is not None:
                    if item_val <= plus_val:  # должно быть больше + значения
                        passed = False
                        break

            # дошел сюда - прошел фильтр
            if passed:
                result_items.append(item)

        if not result_items:
            self.debug.append("#Поиск Item: Не найдено ни одной сборочной единицы по выбранным параметрам.")
        else:
            found_items_len = list(set(result_items))
            self.debug.append(f"#Поиск Item: Найдено {len(found_items_len)} СБЕ")

            if not self.params["selected_assembly_unit"]:
                self.debug.append("#Поиск Item: ожидание выбора СБЕ (selected_assembly_unit).")

        return result_items

    def get_available_assembly_units(self) -> list:
        """Возвращает список ID подходящих СБЕ (Item). Фильтрация выполняется по входящим параметрам load_and_move."""
        product_family = self.get_selected_product_family()

        all_items_assembly_unit = Item.objects.filter(
            type__product_family=product_family,  # выбранное семейство
            type__category=DetailType.ASSEMBLY_UNIT  # Обязательно именно сборочная единица
        )

        if not all_items_assembly_unit:
            self.debug.append("#Поиск Item: Не найдено ни одной сборочной единицы.")
        else:
            all_items_assembly_unit = self.calculate_load_and_move(all_items_assembly_unit)

        return all_items_assembly_unit or None
