import csv
import os

from django.db import migrations
from django.conf import settings


NAME = 1
TYPE = 4
ASTM_SPEC = 5
ASME_TYPE = 6
ASME_UNS = 7
SOURCE = 8
MIN_TEMP = 9
MAX_TEMP = 10
MAX_EXHAUST_GAS_TEMP = 11
LZ = 12
DENSITY = 13
SPRING_CONSTANT = 17
RP0 = 18

FIELDS = {
    'name_ru': NAME,
    'type': TYPE,
    'astm_spec': ASTM_SPEC,
    'asme_type': ASME_TYPE,
    'asme_uns': ASME_UNS,
    'source': SOURCE,
    'min_temp': MIN_TEMP,
    'max_temp': MAX_TEMP,
    'max_exhaust_gas_temp': MAX_EXHAUST_GAS_TEMP,
    'lz': LZ,
    'density': DENSITY,
    'spring_constant': SPRING_CONSTANT,
    'rp0': RP0,
}


def populate_materials(apps, scheme_editor):
    Material = apps.get_model('catalog', 'Material')

    file_path = os.path.join(
        settings.BASE_APP_DIR,
        'catalog',
        'fixtures',
        'materials.csv',
    )

    with open(file_path, 'r') as f:
        reader = csv.reader(f, delimiter=';', quotechar='"')

        for row in list(reader)[1:]:
            material = Material.objects.filter(name=row[NAME]).first()

            if not material:
                material = Material()

            for field_name, field_index in FIELDS.items():
                value = row[field_index]

                if not value or value == '-':
                    continue

                setattr(material, field_name, value)

            material.save()


def reverse_code(apps, scheme_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0022_material_asme_type_material_asme_uns_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_materials, reverse_code=reverse_code),
    ]
