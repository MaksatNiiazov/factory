import django.core.validators
from django.db import migrations, models


def rename_permissions(apps, scheme_editor):
    Item = apps.get_model('ops', 'Item')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    item_content_type = ContentType.objects.get_for_model(Item)

    permissions = {
        'add_item': 'Может создавать изделия/детали/сборочные единицы всех пользователей',
        'change_item': 'Может изменять изделия/детали/сборочные единицы всех пользователей',
        'delete_item': 'Может удалять изделия/детали/сборочные единицы всех пользователей',
        'view_item': 'Может видеть изделия/детали/сборочные единицы всех пользователей',
    }

    for codename, new_name in permissions.items():
        try:
            permission = Permission.objects.get(codename=codename, content_type=item_content_type)
            permission.name = new_name
            permission.save()
        except Permission.DoesNotExist:
            Permission.objects.create(
                codename=codename,
                name=new_name,
                content_type=item_content_type
            )


class Migration(migrations.Migration):

    dependencies = [
        ('ops', '0074_variant_deleted_at_alter_attribute_position'),
    ]

    operations = [
        migrations.RunPython(rename_permissions),
    ]
