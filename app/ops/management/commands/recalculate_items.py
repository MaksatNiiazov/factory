from django.core.management.base import BaseCommand

from ops.signals import _mark_items_as_stale


class Command(BaseCommand):
    help = "Перерасчёт всех изделии/деталей"

    def add_arguments(self, parser):
        category_choices = ["detail", "assembly_unit", "product", "billet"]
        parser.add_argument(
            "--category",
            type=str,
            choices=category_choices,
            help="Категория изделия (detail, assembly_unit, product, billet)",
        )
        parser.add_argument(
            "--designation",
            type=str,
            help="Обозначение изделия",
        )

    def handle(self, *args, **options):
        from ops.models import Item, ItemChild

        designation = options.get("designation")
        category = options.get("category")

        items_qs = Item.objects.all()
        if category:
            items_qs = items_qs.filter(type__category=category)
        if designation:
            items_qs = items_qs.filter(type__designation=designation)

        parent_ids = set(ItemChild.objects.values_list("parent_id", flat=True))

        items = Item.objects.exclude(id__in=parent_ids)
        _mark_items_as_stale(items)
