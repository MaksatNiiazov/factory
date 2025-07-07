from django.db import migrations
from django.db.models import Q


def populate_item_name(apps, scheme_editor):
    Item = apps.get_model('ops', 'Item')

    items = Item.objects.select_related('type').filter(Q(name__isnull=True) | Q(name=''))

    for item in items:
        short_name = item.type.get_short_name_display()
        marking = item.marking

        name = f'{short_name} {marking}'
        item.name = name

    Item.objects.bulk_update(items, fields=['name'])


class Migration(migrations.Migration):

    dependencies = [
        ('ops', '0028_remove_variant_is_fallback'),
    ]

    operations = [
        migrations.RunPython(populate_item_name),
    ]
