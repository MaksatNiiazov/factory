import logging

from openpyxl.reader.excel import load_workbook

from catalog.models import PipeDiameter, Material
from ops.choices import EstimatedState
from ops.models import DetailType, Variant, Item, ProjectItem, TemporaryComposition

logger = logging.getLogger(__file__)


def process_opory_sheet(project, sheet):
    project_items = []
    row = 4

    while sheet[f'A{row}'].value:
        project_item_data = {
            'type': 'opory',
            'position_number': sheet[f'A{row}'].value,
            "item_name": sheet[f"B{row}"].value,
            "question_list": sheet[f"C{row}"].value,
            "tag_id": sheet[f"D{row}"].value,
            'nominal_diameter': sheet[f'E{row}'].value,
            'pipe_diameter': sheet[f'F{row}'].value,  # Не используется
            'max_temperature': sheet[f'G{row}'].value,
            'min_temperature': sheet[f'H{row}'].value,
            'ambient_temperature': sheet[f'I{row}'].value,
            'insulation_thickness': sheet[f'J{row}'].value,
            'estimated_state': sheet[f'K{row}'].value,
            'load_z': sheet[f'L{row}'].value,
            'load_x': sheet[f'M{row}'].value,
            'load_y': sheet[f'N{row}'].value,
            'move_z': sheet[f'O{row}'].value,
            'max_move_z': sheet[f'P{row}'].value,
            'move_x': sheet[f'Q{row}'].value,
            'move_y': sheet[f'R{row}'].value,
            'test_load': sheet[f'S{row}'].value,
            'count': sheet[f'T{row}'].value,
            'hot_load': sheet[f'U{row}'].value,
            'cold_load': sheet[f'V{row}'].value,
            'load_change': sheet[f'W{row}'].value,
            'load_adjustment': sheet[f'X{row}'].value,
            'spring_travel_up': sheet[f'Y{row}'].value,
            'spring_travel_down': sheet[f'Z{row}'].value,
            'regulation_range_plus': sheet[f'AA{row}'].value,
            'regulation_range_minus': sheet[f'AB{row}'].value,
            'chain_weight': sheet[f'AC{row}'].value,
            'detail_type': sheet[f'AF{row}'].value,
            'category': sheet[f'AG{row}'].value,
            'spring_stiffness': sheet[f'AI{row}'].value,
            'parameters': {
                'Hs': sheet[f'AJ{row}'].value,
                'E': sheet[f'AK{row}'].value,
                'H': sheet[f'AL{row}'].value,
                'H1': sheet[f'AM{row}'].value,
                'm': sheet[f'AN{row}'].value,
                't': sheet[f'AO{row}'].value,
                'k': sheet[f'AP{row}'].value,
                's': sheet[f'AQ{row}'].value,
                'p': sheet[f'AR{row}'].value,
                'd': sheet[f'AS{row}'].value,
            },
            'comment': sheet[f'AT{row}'].value,
        }
        project_items.append(project_item_data)
        row += 1

    return project_items


def process_opory_specifications_sheet(sheet, project_items):
    row = 2

    while True:
        # Если 10 строк подряд пустые, завершаем
        if all(not sheet[f'A{row + i}'].value for i in range(10)):
            break

        position = sheet[f'A{row}'].value
        matching_item = next((item for item in project_items if item['position_number'] == position and item['type'] == 'opory'), None)

        if matching_item:
            specification = {
                'tag_number': sheet[f'B{row}'].value,
                'position': sheet[f'C{row}'].value,
                'name': sheet[f'D{row}'].value,
                'lgv': sheet[f'E{row}'].value,
                'clamp_diameter': sheet[f'F{row}'].value,
                'material': sheet[f'G{row}'].value,
                'count': sheet[f'H{row}'].value,
                'weight': sheet[f'I{row}'].value,
                'total_weight': sheet[f'J{row}'].value,
            }

            if 'specifications' not in matching_item:
                matching_item['specifications'] = []
            matching_item['specifications'].append(specification)

        row += 1


def process_podvesy_sheet(project, sheet):
    project_items = []
    row = 4

    while sheet[f'A{row}'].value:
        project_item_data = {
            'type': 'podvesy',
            'position_number': sheet[f'A{row}'].value,
            "item_name": sheet[f"B{row}"].value,
            "question_list": sheet[f"C{row}"].value,
            "tag_id": sheet[f"D{row}"].value,
            'nominal_diameter': sheet[f'E{row}'].value,
            'pipe_diameter': sheet[f'F{row}'].value,  # Не используется
            'max_temperature': sheet[f'G{row}'].value,
            'min_temperature': sheet[f'H{row}'].value,
            'ambient_temperature': sheet[f'I{row}'].value,
            'insulation_thickness': sheet[f'J{row}'].value,
            'estimated_state': sheet[f'K{row}'].value,
            'load_z': sheet[f'L{row}'].value,
            'load_x': sheet[f'M{row}'].value,
            'load_y': sheet[f'N{row}'].value,
            'move_z': sheet[f'O{row}'].value,
            'max_move_z': sheet[f'P{row}'].value,
            'move_x': sheet[f'Q{row}'].value,
            'move_y': sheet[f'R{row}'].value,
            'test_load': sheet[f'S{row}'].value,
            'count': sheet[f'T{row}'].value,
            'hot_load': sheet[f'U{row}'].value,
            'cold_load': sheet[f'V{row}'].value,
            'load_change': sheet[f'W{row}'].value,
            'load_adjustment': sheet[f'X{row}'].value,
            'spring_travel_up': sheet[f'Y{row}'].value,
            'spring_travel_down': sheet[f'Z{row}'].value,
            'regulation_range_plus': sheet[f'AA{row}'].value,
            'regulation_range_minus': sheet[f'AB{row}'].value,
            'chain_weight': sheet[f'AC{row}'].value,
            'detail_type': sheet[f'AF{row}'].value,
            'category': sheet[f'AG{row}'].value,
            'spring_stiffness': sheet[f'AI{row}'].value,
            'parameters': {
                'Hs': sheet[f'AJ{row}'].value,
                'E': sheet[f'AK{row}'].value,
                'm': sheet[f'AL{row}'].value,
            },
            'comment': sheet[f'AM{row}'].value,
        }
        project_items.append(project_item_data)
        row += 1

    return project_items


def process_podvesy_specifications_sheet(sheet, project_items):
    row = 2

    while True:
        # Если 10 строк подряд пустые, завершаем
        if all(not sheet[f'A{row + i}'].value for i in range(10)):
            break

        position = sheet[f'A{row}'].value
        matching_item = next((item for item in project_items if item['position_number'] == position and item['type'] == 'podvesy'), None)

        if matching_item:
            specification = {
                'tag_number': sheet[f'B{row}'].value,
                'position': sheet[f'C{row}'].value,
                'name': sheet[f'D{row}'].value,
                'lgv': sheet[f'E{row}'].value,
                'clamp_diameter': sheet[f'F{row}'].value,
                'material': sheet[f'G{row}'].value,
                'count': sheet[f'H{row}'].value,
                'weight': sheet[f'I{row}'].value,
                'total_weight': sheet[f'J{row}'].value,
            }

            if 'specifications' not in matching_item:
                matching_item['specifications'] = []
            matching_item['specifications'].append(specification)

        row += 1


def get_load_adjustment(item_data):
    load_adjustment = item_data['load_adjustment']

    if load_adjustment == '-':
        return None

    return load_adjustment


def get_estimated_state(item_data):
    estimated_state = item_data['estimated_state']

    if estimated_state == 'холодное':
        return EstimatedState.COLD_LOAD
    elif estimated_state == 'горячее':
        return EstimatedState.HOT_LOAD
    else:
        raise Exception(f'Расчетное состояние пустое или содержит не правильное значение: {estimated_state}')


def get_category(item_data):
    category = item_data['category']

    if category == 'Изделие':
        return DetailType.PRODUCT
    elif category == 'Деталь':
        return DetailType.DETAIL
    elif category == 'Сборочная единица':
        return DetailType.ASSEMBLY_UNIT
    elif category == 'Заготовка':
        return DetailType.BILLET
    else:
        raise Exception(f'Невозможно найти категорию "{category}". Возможные категории: "Изделие", "Деталь", "Сборочная единица", "Заготовка"')


def check_defis(value):
    if value == '-':
        return None

    return value


def import_project_from_file(project, import_file, user):
    try:
        workbook = load_workbook(filename=import_file, data_only=True)
    except Exception as exc:
        logger.exception('Exception raised when import project with wrong xlsx file.')
        raise Exception('Ошибка чтения файла: убедитесь, что это корректный xlsx-файл.')

    project_items = []

    for sheet in workbook.worksheets:
        if sheet.title == 'Опоры':
            project_items.extend(process_opory_sheet(project, sheet))
        elif sheet.title == 'Опоры - спецификация':
            process_opory_specifications_sheet(sheet, project_items)
        elif sheet.title == 'Подвесы':
            project_items.extend(process_podvesy_sheet(project, sheet))
        elif sheet.title == 'Подвесы - спецификация':
            process_podvesy_specifications_sheet(sheet, project_items)

    for item_data in project_items:
        try:
            detail_type = DetailType.objects.get(designation=item_data['detail_type'], category=get_category(item_data))
        except DetailType.DoesNotExist as exc:
            raise Exception('Нет тип детали с обозначением {detail_type} и категорией {category}'.format(
                detail_type=item_data['detail_type'],
                category=get_category(item_data),
            ))

        variant = Variant.objects.filter(detail_type=detail_type).first()

        item = Item.objects.create(
            type=detail_type,
            variant=variant,
            parameters=item_data['parameters'],
            author=user,
        )

        item_weight = 0

        for child_item_data in item_data['specifications']:
            name = child_item_data['name']
            designation = name.split(' ')[0]

            tmp_child = DetailType.objects.filter(designation=designation, category__in=[DetailType.ASSEMBLY_UNIT, DetailType.DETAIL]).first()

            if not tmp_child:
                raise Exception(f'DetailType с {designation} не найден в базе.')


            material_name = child_item_data['material']

            if material_name and material_name != '-':
                material = Material.objects.filter(name_ru=material_name).first()

                if not material:
                    raise Exception(f'Материал с наименованием "{material_name}" не найден.')
            else:
                material = None

            temporary_composition = TemporaryComposition.objects.create(
                tmp_parent=item,
                tmp_child=tmp_child,
                position=child_item_data['position'],
                material=material,
                count=child_item_data['count'],
                tag_id=child_item_data['tag_number'],
                name=child_item_data['name'],
                lgv=child_item_data['lgv'],
                weight=child_item_data['weight'],
            )

            if child_item_data['weight']:
                item_weight += child_item_data['weight']

        item.weight = item_weight
        item.save()

        nominal_diameter = PipeDiameter.objects.get(dn__dn=item_data['nominal_diameter'], standard=PipeDiameter.Standard.RF)

        additional_params = {}

        if item_data['load_z']:
            if item_data['load_z'] >= 0:
                additional_params['load_plus_z'] = item_data['load_z']
            elif item_data['load_z'] < 0:
                additional_params['load_minus_z'] = abs(item_data['load_z'])

        if item_data['load_x']:
            if item_data['load_x'] >= 0:
                additional_params['load_plus_x'] = item_data['load_x']
            elif item_data['load_x'] < 0:
                additional_params['load_minus_x'] = abs(item_data['load_x'])

        if item_data['load_y']:
            if item_data['load_y'] >= 0:
                additional_params['load_plus_y'] = item_data['load_y']
            elif item_data['load_y'] < 0:
                additional_params['load_minus_y'] = abs(item_data['load_y'])

        if item_data['move_z']:
            if item_data['move_z'] >= 0:
                additional_params['move_plus_z'] = item_data['move_z']
            elif item_data['move_z'] < 0:
                additional_params['move_minus_z'] = abs(item_data['move_z'])

        if item_data['move_x']:
            if item_data['move_x'] >= 0:
                additional_params['move_plus_x'] = item_data['move_x']
            elif item_data['move_x'] < 0:
                additional_params['move_minus_x'] = abs(item_data['move_x'])

        if item_data['move_y']:
            if item_data['move_y'] >= 0:
                additional_params['move_plus_y'] = item_data['move_y']
            elif item_data['move_y'] < 0:
                additional_params['move_minus_y'] = abs(item_data['move_y'])

        project_item = ProjectItem.objects.create(
            project=project,
            original_item=item,
            position_number=item_data['position_number'],
            question_list=item_data['question_list'],
            tag_id=item_data['tag_id'],
            count=item_data['count'],
            nominal_diameter=nominal_diameter,
            max_temperature=item_data['max_temperature'],
            min_temperature=item_data['min_temperature'],
            ambient_temperature=item_data['ambient_temperature'],
            insulation_thickness=item_data['insulation_thickness'],
            estimated_state=get_estimated_state(item_data),
            max_move_z=item_data['max_move_z'],
            test_load_z=item_data['test_load'],
            hot_load=item_data['hot_load'],
            cold_load=item_data['cold_load'],
            load_change=item_data['load_change'],
            load_adjustment=get_load_adjustment(item_data),
            spring_travel_up=item_data['spring_travel_up'],
            spring_travel_down=item_data['spring_travel_down'],
            regulation_range_plus=check_defis(item_data['regulation_range_plus']),
            regulation_range_minus=check_defis(item_data['regulation_range_minus']),
            chain_weight=item_data['chain_weight'],
            spring_stiffness=item_data['spring_stiffness'],
            comment=item_data['comment'],
            **additional_params,
        )
