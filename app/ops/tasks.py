import copy
import traceback
from typing import List

from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from django.utils.module_loading import import_string
from tablib import Dataset

from catalog.models import DirectoryEntry
from kernel.consumers import send_event_to_all, send_event_to_users
from kernel.erp import ERPApi
from ops.choices import ERPSyncStatus, ERPSyncLogType, AttributeType, AttributeCatalog
from ops.resources import get_resources_list
from taskmanager.choices import TaskStatus
from taskmanager.models import Task

logger = get_task_logger('erp_task_logger')


@shared_task(ignore_result=True)
def recalculate_item_parameters(item_ids: List[int]) -> None:
    """
    Асинхронная задача перерасчёта параметров для переданных Item'ов.

    Если параметры изменились после пересчёта, обновляет их в базе данных.
    Логирует предупреждение в случае ошибки при перерасчёте.
    """
    from ops.models import Item

    items = Item.objects.filter(id__in=item_ids)

    changed_items = []

    for item in items:
        try:
            old_parameters = copy.deepcopy(item.parameters)
            item.clean()
            new_parameters = item.parameters

            if old_parameters != new_parameters:
                changed_items.append(item)
        except Exception as exc:
            logger.warning(f"Ошибка при перерасчёте параметров для Item(id={item.id}): {exc}")

    Item.objects.bulk_update(changed_items, fields=['parameters', 'parameters_errors'])


def sync_item_to_erp(api, erp_sync, item):
    from ops.models import Attribute

    if item.erp_id:
        erp_sync.add_log(
            ERPSyncLogType.DEBUG, f'Объект {item} (id={item.id}) уже был синхронизирован (erp_id={item.erp_id})',
        )
        return

    params = {}

    if item.material_id:  # материал
        params["materialname"] = item.material.name
        params["materialgroup"] = item.material.group

    if item.parameters:
        parameters = item.parameters
    else:
        parameters = {}

    for key, value in parameters.items():
        # Маппинг пока смотрим через Attribute
        # TODO: Попытаться найти лучший способ
        try:
            attr = Attribute.objects.get(name=key, variant_id=item.variant_id, variant__detail_type_id=item.type_id)
        except Attribute.DoesNotExist:
            raise Exception(f"Не найден атрибут с наименованием {key}")
        except Attribute.MultipleObjectsReturned:
            raise Exception(f"Существует дубликаты атрибута с наименованием {key}")

        if attr.type == AttributeType.CATALOG and value is not None:
            allowed_builtin_catalogues = [item for item in AttributeCatalog]

            if attr.catalog not in allowed_builtin_catalogues:
                directory_id = int(value)

                try:
                    instance = DirectoryEntry.objects.get(id=value, directory_id=directory_id)
                except DirectoryEntry.DoesNotExist:
                    raise Exception(f'Объект справочника с идентификатором {value} не существует')

                fields = {'id': instance.id, 'display_name': instance.display_name,
                          'display_name_errors': instance.display_name_errors}
                for value_obj in instance.values.select_related('directory_field'):
                    fields[value_obj.directory_field.name] = value_obj.value
                return fields

            else:
                package = f'catalog.models.{attr.catalog}'
                catalog_model = import_string(package)

                try:
                    instance = catalog_model.objects.get(pk=value)
                except catalog_model.DoesNotExist:
                    raise Exception(f"Объект справочника {catalog_model} с идентификатором {value} не существует")

                instance_str = str(instance)

                serializer_package = attr.CATALOG_SERIALIZERS[attr.catalog]
                serializer_class = import_string(serializer_package)

                serializer = serializer_class(instance)
                fields = serializer.data

            if attr.erp_name:
                if key in attr.erp_name:
                    name = attr.erp_name[key]
                    params[name] = instance_str
            else:
                params[key] = instance_str

            for field, field_value in fields.items():
                if not attr.erp_name:
                    continue

                name = f'{key}_{field}'

                if name in attr.erp_name:
                    name = attr.erp_name[name]
                    params[name] = field_value
        else:
            name = key
            if attr.erp_name and name in attr.erp_name:
                name = attr.erp_name[name]

            params[name] = value

        name = key
        if attr.erp_name:
            name = attr.erp_name

    erp_sync.add_log(ERPSyncLogType.DEBUG, f'Подготовлен params: {params}')

    erp_id = api.sync_product(
        idwicad=item.inner_id,
        modelslug=item.type.erp_modelslug,
        art=item.marking,
        name=item.name,
        weight=item.weight,
        params=params,
        erp_sync=erp_sync,
    )
    item.erp_id = erp_id
    item.save(update_fields=('erp_id',))
    erp_sync.add_log(ERPSyncLogType.DEBUG, f'Сохранили erp_id={erp_id} у {item}')


def sync_item(api, erp_sync, item):
    sync_item_to_erp(api, erp_sync, item)
    children = item.children.all()

    if not children.exists():
        erp_sync.add_log(ERPSyncLogType.DEBUG, f'У объекта {item} нет дочерних элементов.')
        return

    structure = []
    for child in children:
        erp_sync.add_log(
            ERPSyncLogType.DEBUG,
            f'Синхронизация дочерного элемента объекта {item} (id={item.id}): {child} (id={child.id})',
        )
        sync_item(api, erp_sync, child.child)
        structure.append({
            'idwicad': child.child.id,
            'iderp': child.child.erp_id,
            'count': child.count,
        })

    logger.info('Syncing specification of item %s (id=%d)', item, item.id)
    erp_sync.add_log(
        ERPSyncLogType.DEBUG,
        f'Синхронизация спецификации для объекта {item} (id={item.id}: {structure}',
    )
    json_data = api.sync_specifications(
        idwicad=item.id,
        iderp=item.erp_id,
        count=1,
        structure=structure,
        erp_sync=erp_sync,
    )
    nomspec = json_data['nomspec']
    erp_sync.add_log(ERPSyncLogType.DEBUG, f'Успешно отправлен спецификация, получен nomspec={nomspec}')

    item.erp_nomspec = nomspec
    item.save(update_fields=['erp_nomspec'])


def sync_project(api, erp_sync, project):
    project_items = project.items.all()

    for project_item in project_items:
        erp_sync.add_log(ERPSyncLogType.DEBUG, f'Синхронизация {project_item}')
        original_item = project_item.original_item

        if original_item is None:
            erp_sync.add_log(ERPSyncLogType.DEBUG, f'Отсутствует original_item у {project_item}')
            raise Exception(f'Отсутствует original_item у {project_item}')

        sync_item_to_erp(api, erp_sync, original_item)


@shared_task(ignore_result=True)
def task_sync_erp(erp_sync_id):
    from ops.models import ERPSync

    erp_sync = ERPSync.objects.get(id=erp_sync_id)
    item = erp_sync.item

    erp_sync.status = ERPSyncStatus.PENDING
    erp_sync.start_at = timezone.now()
    erp_sync.save(update_fields=['status', 'start_at'])
    erp_sync.add_log(ERPSyncLogType.DEBUG, 'Начало синхронизации ERP')

    api = ERPApi()
    send_event_to_all("sync_erp", erp_sync.to_json())

    try:
        sync_item(api, erp_sync, item)
        erp_sync.status = ERPSyncStatus.SUCCESS
        erp_sync.finished_at = timezone.now()
        erp_sync.save(update_fields=['status', 'finished_at'])
        erp_sync.add_log(ERPSyncLogType.DEBUG, 'Синхронизация завершена')
        send_event_to_all("sync_erp", erp_sync.to_json())
    except Exception as exc:
        erp_sync.status = ERPSyncStatus.ERROR
        erp_sync.finished_at = timezone.now()
        erp_sync.save(update_fields=['status', 'finished_at'])
        erp_sync.add_log(
            ERPSyncLogType.EXCEPTION,
            request=f'Произошла ошибка при синхронизации: {exc}',
            response=exc,
        )
        send_event_to_all("sync_erp", erp_sync.to_json())


@shared_task(ignore_result=True)
def task_sync_project_to_erp(erp_sync_id):
    from ops.models import ERPSync

    erp_sync = ERPSync.objects.get(id=erp_sync_id)
    project = erp_sync.project

    erp_sync.status = ERPSyncStatus.PENDING
    erp_sync.start_at = timezone.now()
    erp_sync.save(update_fields=['status', 'start_at'])
    erp_sync.add_log(ERPSyncLogType.DEBUG, 'Начало синхронизации ERP')

    api = ERPApi()
    send_event_to_all('sync_erp', erp_sync.to_json())

    try:
        sync_project(api, erp_sync, project)
        erp_sync.status = ERPSyncStatus.SUCCESS
        erp_sync.finished_at = timezone.now()
        erp_sync.save(update_fields=['status', 'finished_at'])
        erp_sync.add_log(ERPSyncLogType.DEBUG, 'Синхронизация завершена')
        send_event_to_all('sync_erp', erp_sync.to_json())
    except Exception as exc:
        erp_sync.status = ERPSyncStatus.ERROR
        erp_sync.finished_at = timezone.now()
        erp_sync.save(update_fields=['status', 'finished_at'])
        erp_sync.add_log(
            ERPSyncLogType.EXCEPTION,
            request=f'Произошла ошибка при синхронизации: {exc}',
            response=exc,
        )

        send_event_to_all('sync_erp', erp_sync.to_json())


def format_row_errors(result):
    errors = []
    for row, error in result.row_errors():
        row_errors = [str(err.error) for err in error]
        errors.append({
            'row': row,
            'errors': row_errors
        })
    return errors


def notify_task_status(task):
    """
    Отправляет уведомление владельцу задачи с информацией о таске.
    """
    data = {
        "id": task.id,
        "status": task.status,
        "status_details": task.status_details,
    }
    send_event_to_users(task.owner.id, command_type="task_updated", data=data)


@shared_task
def process_import_task(task_id: int) -> None:
    """
    Celery-задача для асинхронного импорта данных.

    При запуске:
        - Статус задачи обновляется на Processing.
        - Извлекаются параметры импорта и файл из TaskAttachment (slug = 'imported_file').
        - Производится вызов метода импорта ресурса.
        - При успешном импорте статус меняется на Done.
        - Если возникает ошибка, статус меняется на Error и traceback записывается в status_details.
    """
    task = Task.objects.get(id=task_id)
    task.status = TaskStatus.PROCESSING
    task.save()
    notify_task_status(task)

    try:
        params = task.parameters or {}
        category = params.get('category')
        designation = params.get('designation')
        file_format = params.get('file_format')
        is_dry_run = params.get('is_dry_run', False)

        resource_name = f"{category}_{designation}"
        resources = get_resources_list()
        resource_cls = next((r for r in resources if r.__name__ == resource_name), None)
        if resource_cls is None:
            raise ValueError(f"Ресурс '{resource_name}' не найден")

        resource_obj = resource_cls()
        resource_obj.category = category
        resource_obj.designation = designation

        attachment = task.attachments.get(slug='imported_file')
        if not attachment.file:
            raise Exception("Файл для импорта не найден")

        raw = attachment.file.read()
        dataset = Dataset().load(raw, format=file_format)

        resource_obj.before_import(dataset, user=task.owner)

        result = resource_obj.import_data(
            dataset,
            dry_run=is_dry_run,
            user=task.owner,
            use_transactions=True
        )

        if result.has_errors():
            task.status = TaskStatus.ERROR
            task.status_details = format_row_errors(result)
        else:
            task.status = TaskStatus.DONE
            task.status_details = {}
        task.save()

    except Exception as exc:
        task.status = TaskStatus.ERROR
        task.status_details = {'exception': traceback.format_exc()}
        logger.error(f"Ошибка импорта: {traceback.format_exc()}")
        task.save()

    notify_task_status(task)
