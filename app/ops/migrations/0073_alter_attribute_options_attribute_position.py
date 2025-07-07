from django.db import migrations, models


def populate_position(apps, scheme_editor):
    Variant = apps.get_model('ops', 'Variant')
    Attribute = apps.get_model('ops', 'Attribute')

    variants = Variant.objects.all()

    for variant in variants:
        attributes = variant.attributes.all()

        position = 1

        for attribute in attributes:
            attribute.position = position
            position += 1

        Attribute.objects.bulk_update(attributes, fields=['position'])


class Migration(migrations.Migration):

    dependencies = [
        ('ops', '0072_remove_item_load_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='attribute',
            name='position',
            field=models.IntegerField(null=True, verbose_name='Позиция'),
        ),
        migrations.RunPython(populate_position),
        migrations.AlterModelOptions(
            name='attribute',
            options={'ordering': ['variant', 'position'], 'verbose_name': 'Атрибут', 'verbose_name_plural': 'Атрибуты'},
        ),
        migrations.AlterField(
            model_name='attribute',
            name='position',
            field=models.IntegerField(verbose_name='Позиция'),
        )
    ]
