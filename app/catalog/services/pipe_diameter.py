from catalog.models import PipeDiameter
from rest_framework import status
from rest_framework.response import Response

def get_dn_by_diameter_service(size_values, standard_values):
    """
    Получает DN по списку внешних диаметров и стандартов.

    :param size_values: строка с размерами труб (может быть None)
    :param standard_values: строка со стандартами (обязательный параметр)
    :return: JSON-ответ с данными или ошибкой
    """
    if not standard_values:
        return Response({"error": "Параметр 'standard' обязателен."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        standard_list = [int(s) for s in standard_values.split(',')]
    except ValueError:
        return Response(
            {"error": "Некорректное значение standard. Оно должно содержать числа, разделенные запятой."},
            status=status.HTTP_400_BAD_REQUEST
        )

    size_list = []
    if size_values:
        try:
            size_list = [float(s) for s in size_values.split(',') if float(s) > 0]
        except ValueError:
            return Response({
                "error": "Некорректное значение size. Оно должно содержать положительные числа, разделенные запятой."
            }, status=status.HTTP_400_BAD_REQUEST)

    filters = {"standard__in": standard_list}
    if size_list:
        filters["size__in"] = size_list

    pipe_diameters = PipeDiameter.objects.filter(**filters).select_related('dn')

    if pipe_diameters.exists():
        results = [
            {
                "size": pd.size,
                "standard": pd.standard,
                "dn": pd.dn.dn
            } for pd in pipe_diameters
        ]
        return Response(results, status=status.HTTP_200_OK)

    return Response({"error": "DN не найден"}, status=status.HTTP_404_NOT_FOUND)
