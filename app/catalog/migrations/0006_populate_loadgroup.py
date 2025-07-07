from django.db import migrations


def populate_loadgroup(apps, scheme_editor):
    LoadGroup = apps.get_model('catalog', 'LoadGroup')

    items = [
        LoadGroup(lgv=12, kn=7),
        LoadGroup(lgv=16, kn=12),
        LoadGroup(lgv=20, kn=20),
        LoadGroup(lgv=24, kn=33),
        LoadGroup(lgv=30, kn=50),
        LoadGroup(lgv=36, kn=70),
        LoadGroup(lgv=42, kn=100),
        LoadGroup(lgv=48, kn=132),
        LoadGroup(lgv=56, kn=180),
        LoadGroup(lgv=64, kn=240),
        LoadGroup(lgv=72, kn=300),
        LoadGroup(lgv=80, kn=400),
        LoadGroup(lgv=90, kn=500),
    ]

    LoadGroup.objects.bulk_create(items)


class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0005_loadgroup'),
    ]

    operations = [
        migrations.RunPython(populate_loadgroup),
    ]
