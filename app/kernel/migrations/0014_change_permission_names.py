from django.db import migrations

TARGET_APPS = {"catalog", "kernel", "ops"}

def sync_custom_permissions(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    existing_models_by_app = {app: set() for app in TARGET_APPS}
    models_with_custom_perms = []

    for model in apps.get_models():
        app_label = model._meta.app_label
        if app_label not in TARGET_APPS:
            continue
        model_name = model._meta.model_name
        existing_models_by_app[app_label].add(model_name)

        custom_perms = getattr(model._meta, "permissions", None) or []
        if custom_perms:
            models_with_custom_perms.append(
                (app_label, model_name, dict(custom_perms))
            )

    for app_label, model_name, perm_map in models_with_custom_perms:
        ct, _ = ContentType.objects.get_or_create(
            app_label=app_label, model=model_name
        )
        for codename, new_name in perm_map.items():
            try:
                p = Permission.objects.get(content_type=ct, codename=codename)
                if p.name != new_name:
                    p.name = new_name
                    p.save(update_fields=["name"])
            except Permission.DoesNotExist:
                Permission.objects.create(
                    content_type=ct, codename=codename, name=new_name
                )

    for ct in ContentType.objects.filter(app_label__in=TARGET_APPS):
        if ct.model not in existing_models_by_app.get(ct.app_label, set()):
            Permission.objects.filter(content_type=ct).delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("kernel", "0013_alter_apitoken_options_alter_organization_options_and_more"),
        ("catalog", "0070_alter_clampselectionentry_options"),
        ("catalog", "0071_rename_clampselectionentry_permissions"),
        ("catalog", "0072_alter_clampmaterialcoefficient_options_and_more"),
        ("ops", "0118_alter_attribute_options_and_more"),
    ]

    operations = [
        migrations.RunPython(sync_custom_permissions, reverse_code=noop_reverse),
    ]
