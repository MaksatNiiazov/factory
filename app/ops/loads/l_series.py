from typing import List, Tuple, Optional

from ops.loads.utils import SpringStiffness, Load

LOAD_GROUP_LGV_LIST = (12, 12, 12, 12, 12, 16, 20, 24, 30, 36, 42, 48, 64, 72, 80, 90)
MAX_SIZE = len(LOAD_GROUP_LGV_LIST)


def load_iterator(rated_stroke_50, rated_stroke_100, rated_stroke_200, design_loads):
    total = len(design_loads)
    loads = []

    for index in range(total):
        size = index + 1
        load_group_lgv = LOAD_GROUP_LGV_LIST[index]
        design_load = design_loads[index]

        loads.append(
            Load(size, rated_stroke_50, rated_stroke_100, rated_stroke_200, load_group_lgv, design_load)
        )

    return loads


# TODO на мой взгляд, для loads нужно сохранить размер, нагрузочную группу, мин и макс нагрузки. Сейчас у нас сохранены рассчитываемые значения.
#  В принципе сразу можно добавить и жесткости и номинальный ход, но они и отдельно хорошо смотрятся.


LOADS = []
LOADS += load_iterator(0, 0, 0, (0.04, 0.12, 0.41, 0.83, 1.66, 3.33, 6.7, 13.3, 20, 27, 33, 53, 80, 107, 133, 167))
LOADS += load_iterator(2.5, 5, 10, (0.05, 0.14, 0.45, 0.91, 1.83, 3.66, 7.3, 14.7, 22, 29, 37, 59, 88, 117, 147, 183))
LOADS += load_iterator(5.0, 10, 20, (0.06, 0.16, 0.49, 1.00, 1.99, 4.00, 8.0, 16.0, 24, 32, 40, 64, 96, 128, 160, 200))
LOADS += load_iterator(7.5, 15, 30, (0.07, 0.18, 0.53, 1.08, 2.16, 4.33, 8.7, 17.3, 26, 35, 43, 69, 104, 139, 173, 217))
LOADS += load_iterator(10.0, 20, 40, (0.08, 0.20, 0.58, 1.16, 2.33, 4.66, 9.3, 18.7, 28, 37, 47, 75, 112, 149, 187, 233))
LOADS += load_iterator(12.5, 25, 50, (0.09, 0.22, 0.62, 1.25, 2.49, 5.00, 10.0, 20.0, 30, 40, 50, 80, 120, 160, 200, 250))
LOADS += load_iterator(15.0, 30, 60, (0.10, 0.24, 0.66, 1.33, 2.66, 5.33, 10.7, 21.3, 32, 43, 53, 85, 128, 171, 213, 267))
LOADS += load_iterator(17.5, 35, 70, (0.11, 0.26, 0.70, 1.41, 2.83, 5.66, 11.3, 22.7, 34, 45, 57, 91, 136, 181, 227, 283))
LOADS += load_iterator(20.0, 40, 80, (0.12, 0.28, 0.74, 1.49, 2.99, 5.99, 12.0, 24.0, 36, 48, 60, 96, 144, 192, 240, 300))
LOADS += load_iterator(22.5, 45, 90, (0.13, 0.30, 0.78, 1.58, 3.16, 6.33, 12.7, 25.3, 38, 51, 63, 101, 152, 203, 253, 317))
LOADS += load_iterator(25.0, 50, 100, (0.15, 0.32, 0.83, 1.66, 3.32, 6.66, 13.3, 26.7, 40, 53, 67, 107, 160, 213, 267, 333))
LOADS += load_iterator(27.5, 55, 110, (0.16, 0.35, 0.87, 1.74, 3.49, 6.99, 14.0, 28.0, 42, 56, 70, 112, 168, 224, 280, 350))
LOADS += load_iterator(30.0, 60, 120, (0.17, 0.37, 0.91, 1.83, 3.66, 7.33, 14.7, 29.3, 44, 59, 73, 117, 176, 235, 293, 367))
LOADS += load_iterator(32.5, 65, 130, (0.18, 0.39, 0.95, 1.91, 3.82, 7.66, 15.3, 30.7, 46, 61, 77, 123, 184, 245, 307, 383))
LOADS += load_iterator(35.0, 70, 140, (0.19, 0.41, 0.99, 1.99, 3.99, 7.99, 16.0, 32.0, 48, 64, 80, 128, 192, 256, 320, 400))
LOADS += load_iterator(37.5, 75, 150, (0.20, 0.43, 1.03, 2.08, 4.16, 8.33, 16.7, 33.3, 50, 67, 83, 133, 200, 267, 333, 417))
LOADS += load_iterator(40.0, 80, 160, (0.21, 0.45, 1.07, 2.16, 4.32, 8.66, 17.3, 34.7, 52, 69, 87, 139, 208, 277, 347, 433))
LOADS += load_iterator(42.5, 85, 170, (0.22, 0.47, 1.12, 2.24, 4.49, 8.99, 18.0, 36.0, 54, 72, 90, 144, 216, 288, 360, 450))
LOADS += load_iterator(45.0, 90, 180, (0.23, 0.49, 1.16, 2.32, 4.66, 9.32, 18.7, 37.3, 56, 75, 93, 149, 224, 299, 373, 467))
LOADS += load_iterator(47.5, 95, 190, (0.24, 0.51, 1.20, 2.41, 4.82, 9.66, 19.3, 38.7, 58, 77, 97, 155, 232, 309, 387, 483))
LOADS += load_iterator(50.0, 100, 200, (0.25, 0.52, 1.25, 2.50, 5.00, 10.0, 20.0, 40.0, 60, 80, 100, 160, 240, 320, 400, 500))


def stiffness_iterator(rated_stroke: int, values: Tuple[Optional[float], ...]) -> List[SpringStiffness]:
    """
    Подготавливает список объектов SpringStiffness на основе заданного номинального хода и кортежа значений жесткости.

    Args:
        rated_stroke (int): Номинальный ход для пружин.
        values (Tuple[Optional[float], ...]): Кортеж, содержащий значения жесткости для различных размеров.
                                              Если значение отсутствует, оно должно быть установлено в None.

    Returns:
        List[SpringStiffness]: Список объектов SpringStiffness, созданных на основе входных значений.
    """
    stiffness_list = []

    for index, value in enumerate(values):
        size = index + 1
        stiffness_list.append(SpringStiffness(size, rated_stroke, value))

    return stiffness_list


# Список жесткости пружин R
SPRING_STIFFNESS_LIST = []
SPRING_STIFFNESS_LIST += stiffness_iterator(50, (
    None, 8.3, 16.6, 33.3, 66.6, 133.3, 266.6, 533.3, 800.0, 1067, 1333, 2133, 3200, 4266, 5333, 6667))
SPRING_STIFFNESS_LIST += stiffness_iterator(100, (
    2.1, 4.1, 8.3, 16.6, 33.3, 66.6, 133.3, 266.6, 400.0, 533, 667, 1066, 1600, 2133, 2666, 3333))
SPRING_STIFFNESS_LIST += stiffness_iterator(200, (
    None, 2.1, 4.1, 8.3, 16.6, 33.3, 66.6, 133.3, 200, 267, 333, 533, 800, 1066, 1333, 1667))
