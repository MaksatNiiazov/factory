from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('ops', '0087_project_standard'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='detailtype',
            name='short_name',
        )
    ]
