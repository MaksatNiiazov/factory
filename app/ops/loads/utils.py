import uuid
from typing import Tuple, Any, Dict, List, Optional

from catalog.models import Load, SpringStiffness
from ops.choices import EstimatedState

RATED_STROKE_50 = 50
RATED_STROKE_100 = 100
RATED_STROKE_200 = 200


def get_loads_by_size(loads, size):
    """
    Получить список объектов Load с указанным размером (size).

    :param loads: Список Load-объектов.
    :param size: Размер.
    :return: Возвращает список объектов Loads с указанным size.
    """
    loads_by_size = [load for load in loads if load.size == size]
    return loads_by_size


def get_spring_stiffness(spring_stiffness_list, size, rated_stroke):
    spring_stiffness = next((spring_stiffness for spring_stiffness in spring_stiffness_list if
                             spring_stiffness.size == size and spring_stiffness.rated_stroke == rated_stroke), None)
    return spring_stiffness


def get_nearest_design_load(loads, value):
    """
    Получить максимально близкое к искомому нагрузке.
    Пример: Указан value=92, для него берем 93.3, но не 90.0.

    :param loads: Список Load объектов.
    :param value: Нагрузка.
    :return: Возвращает объект Load, с полем design_load максимально близкое к искомому нагрузке (value).
    """
    nearest_load = min(loads, key=lambda load: abs(load.design_load - value))
    return nearest_load


def get_start_value(loads, rated_stroke):
    """
    Получить начальную нагрузку. Возвращает Load-объект

    :param loads: Список Load объектов.
    :param rated_stroke: Номинальный ход (50, 100, 200)
    :return: Возвращает начальную нагрузку (Load-объект)
    """
    start_load = min(loads, key=lambda load: getattr(load, f'rated_stroke_{rated_stroke}'))
    return start_load


def get_suitable_loads(
        series_name: str,
        max_size: int,
        load_minus: float,
        movement_plus: float,
        movement_minus: float,
        minimum_spring_travel: float,
        estimated_state: str = EstimatedState.COLD_LOAD,
        best_suitable_load: Optional[Dict[str, Any]] = None,
        test_load_x = None,
        test_load_y = None,
        test_load_z = None,
        has_rod = False,
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Алгоритм выбора пружинного блока.

    :param series_name: Наименование серии.
    :param max_size: Максимальный размер.
    :param load_minus: Нагрузка (минус).
    :param movement_plus: Перемещение (плюс).
    :param movement_minus: Перемещение (минус).
    :param minimum_spring_travel: Минимальный запас хода пружины.
    :param estimated_state: Расчетное состояние.
    :param best_suitable_load: Текущий подходящий пружинный блок.
    :return: Возвращает лучший подходящий пружинный блок и список всех подходящих.
    """
    loads_qs = Load.objects.filter(series_name=series_name, size__lte=max_size).order_by('size')
    stiffness_qs = SpringStiffness.objects.filter(series_name=series_name)

    loads_list = list(loads_qs)
    spring_stiffness_list = list(stiffness_qs)

    best_suitable_load = best_suitable_load
    suitable_loads = []

    # Когда указаны и верхнее и нижние перемещения, то нам надо учесть их в запасах хода
    minimum_spring_travel_up, minimum_spring_travel_down = minimum_spring_travel, minimum_spring_travel

    if movement_minus and not movement_plus:
        movement = - movement_minus
    elif not movement_minus and movement_plus:
        movement = movement_plus
    else:
        if abs(movement_minus) >= abs(movement_plus):
            movement = - movement_minus
            minimum_spring_travel_up += movement_plus
        else:
            movement = movement_plus
            minimum_spring_travel_down += movement_minus

    rod_stroke_map = {50: 35, 100: 45, 200: 75}

    for index in range(max_size):
        size = index + 1

        # Получаем все Load-объекты расположенные в одном столбце
        loads_by_size = get_loads_by_size(loads_list, size)

        if not loads_by_size:
            continue

        # Рассчитываем для каждого из вариантов пружины, подходит нам она или нет
        # (для вариантов 50, 100, 200 мм номинального хода)
        rated_strokes = (RATED_STROKE_50, RATED_STROKE_100, RATED_STROKE_200)

        for rated_stroke in rated_strokes:
            start_value = get_start_value(loads_by_size, rated_stroke).design_load
            spring_stiffness = get_spring_stiffness(spring_stiffness_list, size, rated_stroke)

            if spring_stiffness.value is None:
                continue

            # В зависимости от estimated_state меняем или не меняем знак перемещения для расчета нагрузки
            calc_movement = - movement if estimated_state == EstimatedState.HOT_LOAD else movement
            new_load = load_minus - (calc_movement * spring_stiffness.value) / 1000

            load_cold, load_hot = (load_minus, new_load) if estimated_state == EstimatedState.COLD_LOAD else (new_load, load_minus)

            # Рассчитаем положения курсора пружины на панели для обеих нагрузок от меньшей к большей:
            points = []
            for load in sorted([new_load, load_minus]):
                f = (load - start_value) * 1000 / spring_stiffness.value
                points.append(f)
            up_range = points[0]  # верхний запасик
            down_range = rated_stroke - points[1]  # нижний запасик

            # Выбираем самый ближайшую нагрузку
            # TODO: Если выбранный Load-объект не подошел, нужно циклично выбирать другие Load-объекты, реализовать потом
            design_load = get_nearest_design_load(loads_by_size, load_cold)

            # Проверяем, что запасы хода были в пределах номинального и были больше минимальных значений:
            #  TODO проверять в пределах номинального не потребуется, если откорректировать LOADS и сразу отсортировать по нагрузке
            if down_range > rated_stroke or down_range < minimum_spring_travel_down or up_range > rated_stroke or up_range < minimum_spring_travel_up:
                continue

            if test_load_x:
                if not (2 * design_load.design_load > test_load_x):
                    continue

            if test_load_y:
                if not (2 * design_load.design_load > test_load_y):
                    continue

            if test_load_z:
                if not (2 * design_load.design_load > test_load_z):
                    continue

            # Рассчитываем соотношение холодной к горячей нагрузке
            aspect = abs((1 - load_cold / load_hot) * 100)

            if has_rod:
                if not (up_range - movement_plus >= minimum_spring_travel):
                    continue

                rod_stroke = rod_stroke_map.get(rated_stroke)
                rod_check = min(rod_stroke, down_range + movement_minus)
                down_range = rod_check - movement_minus

                if not (down_range >= 5):
                    continue

            # TODO: Пока временно отправляю в template таким образом, нужно подумать над архитектурой в api
            prefix = 'F..-L' if series_name == 'l_series' else 'F..'
            suitable_load = {
                'name': series_name,
                'id': design_load.id,
                'size': size,
                'rated_stroke': rated_stroke,
                'aspect': round(aspect, 1),
                'up_range': int(round(up_range, 0)),
                'down_range': int(round(down_range, 0)),
                'load_initial': round(start_value, 1),
                'load_minus': round(load_cold, 1),
                'hot_design_load': round(load_hot, 1),
                'spring_stiffness': spring_stiffness.value,
                'movement_plus': abs(movement_plus) if movement_plus else movement_plus,
                'movement_minus': abs(movement_minus) if movement_minus else movement_minus,
                'load_group_lgv': design_load.load_group_lgv,
                'marking': f'{prefix} {size}.{rated_stroke}.{design_load.load_group_lgv}',
            }

            if not best_suitable_load:
                best_suitable_load = suitable_load
            elif suitable_load['aspect'] <= 25 and \
                    suitable_load['load_group_lgv'] < best_suitable_load['load_group_lgv']:
                best_suitable_load = suitable_load

            suitable_loads.append(suitable_load)

    return best_suitable_load, suitable_loads
