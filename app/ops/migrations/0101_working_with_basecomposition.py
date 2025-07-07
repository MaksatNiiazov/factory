import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


def populate_base_parent_and_child(apps, scheme_editor):
    BaseComposition = apps.get_model('ops', 'BaseComposition')

    base_compositions = BaseComposition.objects.filter(Q(base_parent__isnull=True) | Q(base_child__isnull=True))

    for base_composition in base_compositions:
        base_composition.base_parent_id = base_composition.base_parent_variant.detail_type_id
        base_composition.base_child_id = base_composition.base_child_variant.detail_type_id

    BaseComposition.objects.bulk_update(base_compositions, fields=['base_parent', 'base_child'])


class Migration(migrations.Migration):

    dependencies = [
        ('ops', '0100_remove_basecomposition_base_child_detail_type_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_base_parent_and_child),
    ]
