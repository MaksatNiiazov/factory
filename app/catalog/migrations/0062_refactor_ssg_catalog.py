from django.db import migrations


def load_full_ssg_data(apps, schema_editor):
    SSGCatalog = apps.get_model('catalog', 'SSGCatalog')

    # Удаляем старые данные
    SSGCatalog.objects.all().delete()

    DATA = [

        # Таблица 1 (type=0)
    # type, fn, l_min,l_max,l1,    l2,     d,   d1, r,    s,  sw, regulation,
        #                                                             h,    sw1,  sw2, fixed_part,
        #                                                                                     delta_l
        [1, 5,   135, 500,  31,    71,     20,  12, 17,   10, 17, 20, None, None, None, 0.26, 2.47],
        [1, 13,  150, 500,  36.5,  81.5,   20,  15, 20,   12, 17, 20, None, None, None, 0.35, 2.47],
        [1, 32,  180, 550,  45,    100,    30,  20, 26.5, 16, 27, 20, None, None, None, 0.9, 5.55],
        [1, 45,  230, 550,  53.5,  123.5,  34,  25, 32,   20, 27, 20, None, None, None, 1.65, 4.67],
        [1, 78,  250, 600,  60,    140,    45,  30, 36.5, 22, 36, 40, None, None, None, 3.02, 8.51],
        [1, 130, 330, 750,  95,    205,    61,  45, 51,   32, 50, 40, None, None, None, 8.35, 14.8],
        [1, 234, 425, 850,  122.5, 252.5,  77,  60, 67.5, 44, 65, 40, None, None, None, 17.56, 23.7],
        [1, 380, 500, 900,  142.5, 282.5,  102, 70, 80,   49, 90, 40, None, None, None, 29.1, 47.5],
        [1, 600, 570, 1000, 165,   320,    108, 80, 90,   55, 90, 40, None, None, None, 39.93, 51.4],

        # Таблица 2 (type=1)
    # type, fn, l_min,l_max, l1,  l2,   d,   d1, r,    s,   sw,   regulation,
        #                                                             h,  sw1, sw2, fixed_part,
    #                                                                                      delta_l
        [2, 5,   440,  750,  125, None, 60,  12, 17,   10,  None, 20, 35,  75,  36,  2.32,  5.07],
        [2, 5,   680,  2000, 180, None, 60,  12, 17,   10,  None, 20, 35,  75,  36,  3.22,  5.07],
        [2, 13,  440,  750,  135, None, 60,  15, 20,   12,  None, 20, 40,  75,  36,  2.54,  5.07],
        [2, 13,  700,  2500, 191, None, 60,  15, 20,   12,  None, 20, 40,  75,  36,  3.35,  5.07],
        [2, 32,  500,  940,  180, None, 76,  20, 26.5, 16,  None, 20, 50,  90,  75,  8.64,  12.1],
        [2, 32,  850,  3000, 235, None, 76,  20, 26.5, 16,  None, 20, 50,  90,  75,  12.34, 12.1],
        [2, 45,  500,  940,  192, None, 76,  25, 32,   20,  None, 20, 60,  90,  75,  9.14,  12.1],
        [2, 45,  850,  3000, 252, None, 76,  25, 32,   20,  None, 20, 60,  90,  75,  13.04, 12.1],
        [2, 78,  540,  980,  213, None, 76,  30, 36.5, 22,  None, 40, 70,  90,  75,  10.14, 12.1],
        [2, 78,  870,  3000, 268, None, 76,  30, 36.5, 22,  None, 40, 70,  90,  75,  13.94, 12.1],
        [2, 130, 690,  1050, 283, None, 102, 45, 51,   32,  None, 40, 85,  120, 95,  24.69, 22.6],
        [2, 130, 1020, 3000, 345, None, 102, 45, 51,   32,  None, 40, 85,  120, 95,  31.99, 22.6],
        [2, 234, 800,  1100, 310, None, 140, 60, 67.5, 44,  None, 40, 120, 18, 105,  46.38, 32],
        [2, 234, 1050, 3000, 365, None, 140, 60, 67.5, 44,  None, 40, 120, 18, 105,  53.88, 32],
        [2, 380, 850,  1160, 335, None, 140, 70, 80,   49,  None, 40, 140, 18, 105,  52.58, 32.5],
        [2, 380, 1100, 3000, 390, None, 140, 70, 80,   49,  None, 40, 140, 18, 105,  59.98, 32.5],
        [2, 600, 950,  1260, 375, None, 168, 80, 90,   55,  None, 40, 155, 18, 115,  80.73, 39],
        [2, 600, 1200, 3000, 430, None, 168, 80, 90,   55,  None, 40, 155, 18, 115,  90.03, 39],
    ]

    records = []
    for row in DATA:
        base_fields = {
            'type': row[0],
            'fn': row[1],
            'l_min': row[2],
            'l_max': row[3],
            'l1': row[4],
            'l2': row[5],
            'd': row[6],
            'd1': row[7],
            'r': row[8],
            's': row[9],
            'sw': row[10],
            'regulation': row[11],
            'fixed_part': row[15],
            'delta_l': row[16],
        }

        if row[0] == 2:
            base_fields.update({
                'h': row[11],
                'sw1': row[12],
                'sw2': row[13],
            })

        records.append(SSGCatalog(**base_fields))

    SSGCatalog.objects.bulk_create(records)


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0061_alter_ssgcatalog_options_ssgcatalog_delta_l_and_more'),
    ]

    operations = [
        migrations.RunPython(load_full_ssg_data),
    ]
