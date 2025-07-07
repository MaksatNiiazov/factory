from catalog.models import Material
from rest_framework import status
from rest_framework.response import Response


def get_materials_by_temperature_service(temperature_values):
    """
    Фильтрует материалы по температурному диапазону.

    :param temperature_values: строка с температурами, разделёнными запятой
    :return: JSON-ответ с материалами или ошибкой
    """
    if not temperature_values:
        return Response({"error": "Параметр 'temperature' обязателен."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        temperature_list = [float(t) for t in temperature_values.split(',')]
    except ValueError:
        return Response(
            {"error": "Некорректное значение temperature. Оно должно содержать числа, разделенные запятой."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Фильтрация материалов
    materials = Material.objects.filter(
        min_temp__lte=min(temperature_list),
        max_temp__gte=max(temperature_list)
    )

    if materials.exists():
        results = [
            {
                "id": mat.id,
                "name": mat.name,
                "group": mat.group,
                "min_temp": mat.min_temp,
                "max_temp": mat.max_temp,
            } for mat in materials
        ]
        return Response(results, status=status.HTTP_200_OK)

    return Response({"error": "Материалы не найдены"}, status=status.HTTP_404_NOT_FOUND)
