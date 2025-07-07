from django.db import migrations


def populate_materials(apps, scheme_editor):
    Material = apps.get_model('catalog', 'Material')

    materials = [
        Material(name='09Г2С'),
    ]

    Material.objects.bulk_create(materials)


class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0007_material'),
    ]

    operations = [
        migrations.RunPython(populate_materials),
    ]
