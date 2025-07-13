from django.dispatch import receiver

from django.db.models.signals import post_save, post_delete

from catalog.models import Material


# TODO: Тут надо по другому, если Material изменен, то надо найти все атрибуты с каталогом, потом смотреть у каких Item'ов есть и там менять параметры и маркировку.
@receiver(post_save, sender=Material)
def update_marking_on_items(sender, instance, **kwargs):
    """
    В случае изменения материала, заново генерируем маркировку в Item, так-как он зависит от данных в материале
    """
    from ops.models import Item

    # TODO: Возможно можно оптимизировать, если сначала искать в DetailType.marking_template слова содержащий
    #  material.name и material.group. На будущее
    items = Item.objects.filter(material=instance)
    items.generate_marking()