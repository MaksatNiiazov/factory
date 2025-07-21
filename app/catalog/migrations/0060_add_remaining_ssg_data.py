from django.db import migrations

ADDITIONAL_SSG_DATA = [
    [45, 500, 940, 192, 76, 25, 32, 60, 20, 20],
    [78, 540, 980, 213, 76, 30, 36, 70, 22, 40],
    [130, 690, 1050, 283, 102, 45, 51, 85, 32, 40],
    [234, 800, 1100, 310, 140, 60, 67, 120, 44, 40],
    [380, 850, 1160, 335, 140, 70, 80, 140, 49, 40],
    [600, 950, 1260, 375, 168, 80, 90, 155, 55, 40],
]

def add_ssg_data(apps, schema_editor):
    SSGCatalog = apps.get_model('catalog', 'SSGCatalog')
    new_instances = [
        SSGCatalog(
            fn=row[0], l_min=row[1], l_max=row[2], l1=row[3], d=row[4], d1=row[5],
            r=row[6], s=row[7], sw=row[8], regulation=row[9]
        )
        for row in ADDITIONAL_SSG_DATA
    ]
    SSGCatalog.objects.bulk_create(new_instances)

class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0059_clampselection_populate'),
    ]

    operations = [
        migrations.RunPython(add_ssg_data),
    ]