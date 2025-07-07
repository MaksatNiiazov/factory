from django.db import migrations


def populate_covering_type(apps, scheme_editor):
    CoveringType = apps.get_model('catalog', 'CoveringType')

    items = [
        CoveringType(name='Гальваника', description='Покрытие: Ц15 хр. бцв по ГОСТ 9.306-85 (гальваника)'),
        CoveringType(name='Цинк', description='Покрытие: Гор.Ц. не менее 50 мкм по ГОСТ 9.307-89 (ИСО 1461-89). '
                                              'Допускается термодиффузионное цинковое покрытие'),
        CoveringType(name='Эмаль', description='Покрытие: Окрасить эмалью серого цвета КО 8101. '
                                               'Болты и гайки обработать медной смазкой МС1640'),
    ]

    CoveringType.objects.bulk_create(items)


class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0016_rename_newpipediameter_pipediameter'),
    ]

    operations = [
        migrations.RunPython(populate_covering_type),
    ]
