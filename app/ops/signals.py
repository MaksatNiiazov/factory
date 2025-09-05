import re

from django.dispatch import receiver

from django.db.models import Q
from django.db.models.signals import post_save, pre_save

from django.core.cache import cache

from ops.constants import STALE_SET_KEY, STALE_LOCK
from ops.models import DetailType, Item, Attribute, ItemChild, Variant, BaseComposition
from ops.tasks import batch_recalculate_items


def _mark_items_as_stale(qs):
    """
    Помечает изделия/детали как устаревшие, добавляя их ID в кэш.
    """
    ids = list(qs.values_list("id", flat=True))

    if not ids:
        return

    # cache.sadd(STALE_SET_KEY, *ids)

    # if cache.add(STALE_LOCK, "1", timeout=300):
    #     batch_recalculate_items.delay()


@receiver(post_save, sender=Attribute)
def trigger_item_recalculation_on_attribute_save(sender, instance, **kwargs):
    """
    Сигнал, который вызывается после сохранения атрибута.

    Находит все детали/изделия, связанные с атрибутом, и инициирует их перерасчет.
    """
    cond = Q()

    if instance.detail_type_id:
        cond |= Q(type=instance.detail_type_id)
    if instance.variant_id:
        cond |= Q(variant=instance.variant_id)
    
    _mark_items_as_stale(Item.objects.filter(cond))


@receiver(post_save, sender=ItemChild)
def trigger_item_recalculation_on_item_child_save(sender, instance, **kwargs):
    """
    Сигнал, который вызывается после изменения состава изделия/детали.
    """
    items = Item.objects.filter(id=instance.parent_id)
    _mark_items_as_stale(items)


@receiver(post_save, sender=Item)
def trigger_items_recalculation_on_item_save(sender, instance, **kwargs):
    """
    Сигнал, который вызывается после сохранения изделия/детали.
    """
    items = Item.objects.filter(children__child=instance)
    _mark_items_as_stale(items)


@receiver(pre_save, sender=BaseComposition)
def update_attribute_calculated_value_on_position_change(sender, instance, **kwargs):
    """
    Сигнал, который вызывается после изменения позиции в BaseComposition.
    """
    if not instance.pk:
        return

    # Получаем старую позицию
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        old_instance = None

    if old_instance is None or old_instance.position == instance.position:
        return  # Позиция не изменилась

    if instance.base_child_variant:
        category = instance.base_child_variant.detail_type.category
        designation = instance.base_child_variant.detail_type.designation
    else:
        category = instance.base_child.category
        designation = instance.base_child.designation

    old_pos = old_instance.position
    new_pos = instance.position

    # Образец вида: <assembly_unit_FHD>.3.h или <assembly_unit_FHD>.h
    if old_pos == 1:
        pattern = re.compile(rf"<{category}_{designation}>\.([A-Za-z_][A-Za-z0-9_]*)")
    else:
        pattern = re.compile(rf"<{category}_{designation}>\.{old_pos}\.([A-Za-z0-9_]+)")

    attrs = Attribute.objects.filter(
        calculated_value__icontains=f"<{category}_{designation}>"
    ).filter(
        Q(detail_type=instance.base_parent) | Q(variant=instance.base_parent_variant)
    )

    for attr in attrs:
        orig = attr.calculated_value

        if not orig:
            continue

        def replacer(match):
            attr_name = match.group(1)
            return f"<{category}_{designation}>.{new_pos}.{attr_name}"

        updated = re.sub(pattern, replacer, orig)

        if updated != orig:
            attr.calculated_value = updated
            attr.save(update_fields=["calculated_value"])


@receiver(post_save, sender=Variant)
def trigger_item_recalculation_on_variant_save(sender, instance, **kwargs):
    """
    Сигнал, который вызывается после сохранения исполнения.

    Находит все детали/изделия, связанные с исполнением, и инициирует их перерасчет.
    """
    items = Item.objects.filter(variant=instance)
    _mark_items_as_stale(items)


@receiver(post_save, sender=DetailType)
def trigger_item_recalculation_on_detail_type_save(sender, instance, **kwargs):
    """
    Сигнал, который вызывается после сохранения типа детали.

    Находит все изделия/детали, связанные с типом детали, и инициирует их перерасчет.
    """
    items = Item.objects.filter(type=instance)
    _mark_items_as_stale(items)


@receiver(post_save, sender=ItemChild)
def remove_item_children_cache(sender, instance: ItemChild, **kwargs):
    """
    Удаляет кэш дочерних элементов после сохранения изменения в ItemChild.
    """
    cache_key = f"item:{instance.parent_id}:children"
    cache.delete(cache_key)


@receiver(post_save, sender=Attribute)
def remove_attribute_cache(sender, instance: Attribute, **kwargs):
    """
    Удаляет кэш атрибутов варианта после сохранения изменения в Attribute.
    """
    if instance.variant_id:
        cache_key = f"variant:{instance.variant_id}:attrs"
        cache.delete(cache_key)

        cache_key_sorted = f"variant:{instance.variant_id}:sorted_attrs"
        cache.delete(cache_key_sorted)
    elif instance.detail_type_id:
        variants_ids = list(Variant.objects.filter(detail_type=instance.detail_type_id).values_list('id', flat=True))

        for variant_id in variants_ids:
            cache_key = f"variant:{variant_id}:attrs"
            cache.delete(cache_key)

            cache_key_sorted = f"variant:{variant_id}:sorted_attrs"
            cache.delete(cache_key_sorted)


@receiver(post_save, sender=Variant)
def reset_series_if_needed(sender, instance: Variant, **kwargs):
    if not instance.has_series() and instance.series:
        instance.series = None
        Variant.objects.filter(pk=instance.pk).update(series=None)
