import base64
import os
import re
from datetime import date, datetime
from io import BytesIO
from collections import defaultdict, deque

from PIL import Image, ImageDraw, ImageFont
from django.shortcuts import render
from django.utils import timezone

from ops.exceptions import TopologicalSortException
from project.settings import BASE_PRJ_DIR
from ops.models import DetailType, TemporaryComposition

# Отношение пикселя к мм
PX_TO_MM = 0.26458333
# запасик, чтобы поднять размер над размерной линией
UP_OF_SIZE_LINE = 3


def extract_dependencies(expression: str) -> set:
    """
    Извлекает переменные из выражения, заключенного в фигурные скобки.
    """
    expression = expression.strip()

    if expression.startswith("{{") and expression.endswith("}}"):
        expression = expression[2:-2].strip()

    expression = re.sub(r'\|[a-zA-Z_]\w*(\([^)]*\))?', '', expression)

    tokens = re.split(r'[\s\+\-\*/\(\),|]+', expression)

    variables = {
        token for token in tokens
        if re.match(r"^[a-zA-Z_]\w*$", token) and not token.isnumeric()
    }

    return variables


def topological_sort(attributes):
    """
    Выполняет топологическую сортировку атрибутов на основе их зависимостей.
    """
    graph = defaultdict(set)
    in_degree = defaultdict(int)
    name_to_attr = {attr.name: attr for attr in attributes}

    for attr in attributes:
        if attr.calculated_value:
            deps = extract_dependencies(attr.calculated_value)
            deps = deps & name_to_attr.keys()
            for dep in deps:
                graph[dep].add(attr.name)
                in_degree[attr.name] += 1

    queue = deque([attr.name for attr in attributes if in_degree[attr.name] == 0])
    sorted_names = []

    while queue:
        current = queue.popleft()
        sorted_names.append(current)
        for neighbor in graph[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_names) != len(attributes):
        cycle_attrs = set(name_to_attr.keys()) - set(sorted_names)
        raise TopologicalSortException(
            message=f"Циклическая зависимость между атрибутами: {', '.join(cycle_attrs)}",
            fields=list(cycle_attrs),
        )

    return [name_to_attr[name] for name in sorted_names]


def calculate_image_position(image_width, image_height, center_x, center_y):
    image_x = round(center_x - image_width * PX_TO_MM / 2)
    image_y = round(center_y - image_height * PX_TO_MM / 2)
    return image_x, image_y


# Подгоняет размер эскиза, сохраненного в Variant, для корректного отображения в требуемой области эскиза
def work_with_image(sketch_path, pji, double=False, coords=None):
    if isinstance(sketch_path, str):
        sketch = Image.open(sketch_path)
    else:
        sketch = sketch_path

    width_px, height_px = sketch.width, sketch.height
    image_width_mm = width_px * PX_TO_MM
    image_height_mm = height_px * PX_TO_MM

    # Ограничения по размеру
    max_mm = 650
    scale_factor = min(max_mm / image_width_mm, max_mm / image_height_mm, 1.0)

    # Применим масштабирование
    scaled_width_mm = image_width_mm * scale_factor
    scaled_height_mm = image_height_mm * scale_factor

    # Смещение от центра
    center_x, center_y = coords or (80, 100)
    image_x = 80
    image_y = 50

    # Масштабированное изображение в пикселях (если хочешь реально уменьшить)
    if scale_factor < 1.0:
        new_width_px = int(width_px * scale_factor)
        new_height_px = int(height_px * scale_factor)
        sketch = sketch.resize((new_width_px, new_height_px), Image.Resampling.LANCZOS)

    # Подпись для двойных изделий
    horizontal_size_y = center_y + scaled_height_mm / 2 - UP_OF_SIZE_LINE if double else None

    # Преобразуем в base64
    buffer = BytesIO()
    sketch.save(buffer, format="PNG")
    buffer.seek(0)
    new_image = base64.b64encode(buffer.read()).decode("utf-8")

    return {
        'image_x': "{:.2f}".format(image_x),
        'image_y': "{:.2f}".format(image_y),
        'image_width': "{:.2f}".format(scaled_width_mm),
        'image_height': "{:.2f}".format(scaled_height_mm),
        'center_x': center_x,
        'center_y': center_y,
        'sketch': new_image,
        'horizontal_size_y': "{:.2f}".format(horizontal_size_y) if horizontal_size_y else None
    }

def wrap_words(comment):
    if comment is None:
        return

    # Конвертация размеров
    dpi = 72  # Стандартная плотность точек для SVG
    max_width_mm = 132
    font_path = 'Arial.ttf'
    font_size_pt = 8
    mm_per_pt = 0.3527
    font_size_mm = font_size_pt * mm_per_pt

    # Создаем шрифт с нужным размером
    font = ImageFont.truetype(font_path, font_size_pt)

    # Максимальная ширина в пикселях (размер SVG и пикселей зависит от контекста рендера)
    max_width_px = max_width_mm / mm_per_pt * dpi / 72  # mm -> pt -> px

    # Создаём временное изображение, чтобы иметь контекст для текста
    img = Image.new('RGB', (1000, 1000))
    draw = ImageDraw.Draw(img)

    final_lines = []

    for line in comment:
        words = line.split(' ')
        current_line = ''

        for word in words:
            # Рассчитываем длину текущей линии с новым словом
            test_line = current_line + ('' if current_line == '' else ' ') + word
            bbox = draw.textbbox((0, 0), test_line, font=font)  # Используем getbbox для получения размеров
            width = bbox[2] - bbox[0]  # Ширина строки

            if width <= max_width_px:
                current_line = test_line
            else:
                # Добавляем текущую строку в финальные и начинаем новую строку
                final_lines.append(current_line)
                current_line = word

        if current_line:
            final_lines.append(current_line)

    return final_lines


def render_sketch(request, project_item, composition_type="temporary_composition"):
    """
    Формирование эскиза
    """
    # Соберем инфу для отображения на эскизе
    if not project_item.original_item.variant.sketch:
        # Если нет эскиза в админке, то и эскиз с параметрами не дадим сделать
        raise Exception('У выбранного типа продукта не заведен эскиз.')

    sketch_path = project_item.original_item.variant.generate_sketch(project_item.original_item)

    if composition_type == "temporary_composition":
        composition_objects = TemporaryComposition.objects.filter(tmp_parent=project_item.original_item)
    else:
        composition_objects = project_item.original_item.children.all()

    today = date.today().strftime('%d.%m.%y')
    last_name = request.user.last_name
    double = project_item.original_item.type.branch_qty == DetailType.BranchQty.TWO

    # Для подгона вывода комментариев построчно
    comment = project_item.comment.split('\n') if project_item.comment else None
    comment = wrap_words(comment)
    image_data = work_with_image(sketch_path, project_item, double)

    # Сформируем эскиз и раскодируем
    context = {
        'pji': project_item,
        'composition_type': composition_type,
        'composition_objects': composition_objects,
        'comment': comment,
        'date': today,
        'user': last_name,
        'image_data': image_data,
    }
    response = render(request, 'ops/preview_svg.html', context=context)

    # Информация для имени файла
    tz = timezone.get_current_timezone()
    aware_datetime = timezone.make_aware(datetime.now(), tz)
    when_formed = aware_datetime.strftime('%d.%m.%y_%H.%M.%S')
    filename = f'{project_item.position_number}_{project_item.project.number}_{when_formed}.svg'

    return response.content, filename
