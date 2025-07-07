from django.db import migrations, models


def set_item_weight(apps, scheme_editor):
    Item = apps.get_model('ops', 'Item')

    items = Item.objects.filter(tmp_parent__isnull=False)

    for item in items:
        compositions = item.tmp_parent.all()

        item_weight = 0

        for composition in compositions:
            if composition.weight:
                item_weight += composition.weight

        if item_weight:
            item.weight = item_weight
            item.save()


class Migration(migrations.Migration):

    dependencies = [
        ('ops', '0081_temporarycomposition_lgv_temporarycomposition_name_and_more'),
    ]

    operations = [
        migrations.RunPython(set_item_weight),
    ]
