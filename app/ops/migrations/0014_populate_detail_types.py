from django.db import migrations

DETAIL = 'detail'
ASSEMBLY_UNIT = 'assembly_unit'
PRODUCT = 'product'
BILLET = 'billet'


def populate_detail_types(apps, scheme_editor):
    DetailType = apps.get_model('ops', 'DetailType')

    detail_types = [
        DetailType(designation='FHD', short_name='Пружинные блоки', name='Пружинные блоки', category=ASSEMBLY_UNIT),
        DetailType(designation='FHG', short_name='Пружинные блоки', name='Пружинные блоки', category=ASSEMBLY_UNIT),
        DetailType(designation='FHS', short_name='Пружинные блоки', name='Пружинные блоки', category=ASSEMBLY_UNIT),
        DetailType(designation='FSS', short_name='Пружинные блоки', name='Пружинные блоки', category=ASSEMBLY_UNIT),
        DetailType(designation='FSP', short_name='Пружинные блоки', name='Пружинные блоки', category=ASSEMBLY_UNIT),
        DetailType(designation='RLA', short_name='Подвес жесткий', name='Подвес жесткий', category=DETAIL),
        DetailType(designation='MSN', short_name='Хомут', name='Хомут', category=ASSEMBLY_UNIT),
        DetailType(designation='LSx', short_name='Хомут', name='Хомут', category=ASSEMBLY_UNIT),
        DetailType(designation='ZTN', short_name='Траверса', name='Траверса', category=ASSEMBLY_UNIT),
        DetailType(designation='ZRM', short_name='Шпилька', name='Шпилька', category=DETAIL),
        DetailType(designation='HDH', short_name='Полухомут', name='Полухомут', category=ASSEMBLY_UNIT),
        DetailType(designation='Пружины', short_name='Пружина', name='Пружина', category=DETAIL),
        DetailType(designation='FQT', short_name='Фланец', name='Фланец', category=DETAIL),
        DetailType(designation='FRF', short_name='Фланец', name='Фланец', category=DETAIL),
        DetailType(designation='FRM', short_name='Патрубок', name='Патрубок', category=DETAIL),
        DetailType(designation='FRT', short_name='Патрубок', name='Патрубок', category=DETAIL),
        DetailType(designation='PFS', short_name='Пластина', name='Пластина', category=DETAIL),
        DetailType(designation='PLT', short_name='Пластина', name='Пластина', category=DETAIL),
        DetailType(designation='LUG', short_name='Втулка', name='Втулка', category=DETAIL),
        DetailType(designation='RNG', short_name='Кольцо', name='Кольцо', category=DETAIL),
        DetailType(designation='SPT', short_name='Труба опораная', name='Труба опораная', category=DETAIL),
        DetailType(designation='RNF', short_name='Кольцо направляющее', name='Кольцо направляющее', category=DETAIL),
        DetailType(designation='RNG_SPT', short_name='Кольцо', name='Кольцо', category=DETAIL),
        DetailType(designation='RIB', short_name='Стенка', name='Стенка', category=DETAIL),
        DetailType(designation='LGA', short_name='Ложемент', name='Ложемент', category=DETAIL),
        DetailType(designation='SWS', short_name='Ребро боковое', name='Ребро боковое', category=DETAIL),
        DetailType(designation='LBK', short_name='Упор', name='Упор', category=DETAIL),
        DetailType(designation='UBT', short_name='U-болт', name='U-болт', category=DETAIL),
        DetailType(designation='PLU', short_name='Пластина', name='Пластина', category=DETAIL),
        DetailType(designation='LIN', short_name='Прокладка', name='Прокладка', category=DETAIL),
        DetailType(designation='EDG', short_name='Ребро', name='Ребро', category=DETAIL),
        DetailType(designation='FWS', short_name='Ребро фронтальное', name='Ребро фронтальное', category=DETAIL),
        DetailType(designation='EDG', short_name='Ребро', name='Ребро', category=DETAIL),
        DetailType(designation='LAW', short_name='Лапка', name='Лапка', category=DETAIL),
        DetailType(designation='ZTF', short_name='Плита', name='Плита', category=DETAIL),
        DetailType(designation='ZTP', short_name='Плита', name='Плита', category=DETAIL),
        DetailType(designation='ZTR', short_name='Ребро', name='Ребро', category=DETAIL),
        DetailType(designation='EDK', short_name='Ребро', name='Ребро', category=DETAIL),
        DetailType(designation='INL', short_name='Прокладка', name='Прокладка', category=DETAIL),
        DetailType(designation='PLQ', short_name='Основание', name='Основание', category=DETAIL),
        DetailType(designation='HVF', short_name='Полухомут', name='Полухомут', category=ASSEMBLY_UNIT),
    ]

    DetailType.objects.bulk_create(detail_types)


class Migration(migrations.Migration):
    dependencies = [
        ('ops', '0013_remove_projectitem_revision_alter_item_inner_id_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_detail_types),
    ]
