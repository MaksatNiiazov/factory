from django.db import migrations


def rename_perms(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")

    mapping = {
        "add_clampselectionentry": "Может добавлять записи в справочник таблицы собираемости",
        "change_clampselectionentry": "Может изменять записи в справочник таблицы собираемости",
        "delete_clampselectionentry": "Может удалять записи в справочник таблицы собираемости",
        "view_clampselectionentry": "Может просматривать записи в справочник таблицы",
    }

    for codename, new_name in mapping.items():
        try:
            perm = Permission.objects.get(codename=codename)
            perm.name = new_name
            perm.save()
        except Permission.DoesNotExist:
            pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0070_alter_clampselectionentry_options"),
    ]

    operations = [
        migrations.RunPython(rename_perms, migrations.RunPython.noop),
    ]
