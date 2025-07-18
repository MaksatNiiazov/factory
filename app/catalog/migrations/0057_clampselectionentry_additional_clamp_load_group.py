from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0056_merge_20250714_1655"),
    ]

    operations = [
        migrations.AddField(
            model_name="clampselectionentry",
            name="additional_clamp_load_group",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="Дополнительная нагрузочная группа хомута для переходника",
            ),
        ),
    ]
