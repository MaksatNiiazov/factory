from django.db import migrations

SSG_DATA = [
    # fn, l_min, l_max, l1, d, d1, r, s, sw, regulation
    [5, 440, 750, 125, 60, 12, 17, 35, 10, 20],
    [13, 440, 750, 135, 60, 15, 20, 40, 12, 20],
    [32, 500, 940, 180, 76, 20, 26, 50, 16, 20],
]

def populate_ssgcatalog(apps, schema_editor):
    SSGCatalog = apps.get_model('catalog', 'SSGCatalog')
    new_instances = [
        SSGCatalog(
            fn=row[0], l_min=row[1], l_max=row[2], l1=row[3], d=row[4], d1=row[5],
            r=row[6], s=row[7], sw=row[8], regulation=row[9]
        )
        for row in SSG_DATA
    ]
    SSGCatalog.objects.bulk_create(new_instances)


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0054_ssgcatalog"),
    ]

    operations = [
        migrations.RunPython(populate_ssgcatalog),
    ]