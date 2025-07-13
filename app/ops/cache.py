from typing import List

from django.core.cache import cache

from django.utils.module_loading import import_string

from catalog.models import DirectoryEntry


CACHE_TIME = 3600  # 1 час


def get_cached_item_children(item_id: int) -> List:
    """
    Получает дочерние элементы для указанного item_id из кэша или базы данных.
    """
    from ops.models import ItemChild

    cache_key = f"item:{item_id}:children"

    def get_children():
        return list(ItemChild.objects.select_related("parent", "child").filter(parent_id=item_id))
    
    return cache.get_or_set(
        cache_key,
        get_children,
        timeout=CACHE_TIME,
    )


def get_cached_attributes(variant) -> List:
    """
    Получает атрибуты варианта из кэша или базы данных.
    """
    from ops.models import Attribute
    cache_key = f"variant:{variant.id}:attrs"

    def get_attrs():
        return list(Attribute.objects.for_variant(variant))

    return cache.get_or_set(
        cache_key,
        get_attrs,
        timeout=CACHE_TIME,
    )


def get_cached_attributes_with_topological_sort(variant) -> List:
    from ops.models import Attribute
    from ops.utils import topological_sort

    cache_key = f"variant:{variant.id}:sorted_attrs"

    def get_attrs():
        attributes = Attribute.objects.for_variant(variant)
        attributes = topological_sort(attributes)
        return attributes

    return cache.get_or_set(
        cache_key,
        get_attrs,
        timeout=CACHE_TIME,
    )


def get_cached_catalog_entry(model_path: str, pk):
    """
    Получает запись каталога по модели и первичному ключу.
    """
    cache_key = f"catalog_entry:{model_path}:{pk}"

    def get_entry():
        model = import_string(model_path)
        return model.objects.get(pk=pk)

    return cache.get_or_set(
        cache_key,
        get_entry,
        timeout=CACHE_TIME,
    )


def get_cached_directory_entry(directory_id: int, entry_id: int):
    """
    Получает запись каталога по ID каталога и ID записи.
    """
    cache_key = f"directory_entry:{directory_id}:{entry_id}"

    return cache.get_or_set(
        cache_key,
        lambda: DirectoryEntry.objects.get(id=entry_id, directory_id=directory_id),
        timeout=CACHE_TIME,
    )
