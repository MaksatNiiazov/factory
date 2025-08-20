from django.db import migrations, models

from catalog.choices import Standard


def change_items_pipediameter(apps, schema_editor):
    """
    Миграция для изменения параметра OD у элементов типа "хомут",
    чтобы он соответствовал диаметру трубопровода в стандарте РФ.
    """
    PipeDiameter = apps.get_model("catalog", "PipeDiameter")
    Item = apps.get_model("ops", "Item")

    en_pipe_diameters = PipeDiameter.objects.filter(standard=Standard.EN)

    for en_pipe_diameter in en_pipe_diameters:
        items = Item.objects.filter(
            type__name__icontains="хомут",
            parameters__OD=en_pipe_diameter.id,
        )

        if not items.exists():
            continue

        ru_pipe_diameter = PipeDiameter.objects.filter(
            dn=en_pipe_diameter.dn,
            standard=Standard.RF,
        ).first()

        for item in items:
            item.parameters["OD"] = ru_pipe_diameter.id

        Item.objects.bulk_update(items, ["parameters"], batch_size=1000)


class Migration(migrations.Migration):

    dependencies = [
        ("ops", "0116_alter_attribute_usage"),
    ]

    operations = [
        migrations.RunPython(change_items_pipediameter, reverse_code=migrations.RunPython.noop),
    ]
