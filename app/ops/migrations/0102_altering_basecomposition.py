import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ops', '0101_working_with_basecomposition'),
    ]

    operations = [
        migrations.AlterField(
            model_name='basecomposition',
            name='base_parent',
            field=models.ForeignKey(
                limit_choices_to=models.Q(('category', 'assembly_unit'), ('category', 'detail'), _connector='OR'),
                on_delete=django.db.models.deletion.PROTECT, related_name='base_parent',
                to='ops.detailtype', verbose_name='Сборка'),
        ),
        migrations.AlterField(
            model_name='basecomposition',
            name='base_child',
            field=models.ForeignKey(
                limit_choices_to=models.Q(('category', 'assembly_unit'), ('category', 'detail'), _connector='OR'),
                on_delete=django.db.models.deletion.PROTECT, related_name='base_children',
                to='ops.detailtype', verbose_name='Комплектующий узел или деталь'),
        ),
    ]
