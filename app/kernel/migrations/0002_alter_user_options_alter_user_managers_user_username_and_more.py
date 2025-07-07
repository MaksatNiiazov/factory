import django.contrib.auth.models
import django.contrib.auth.validators
from django.db import migrations, models


def populate_username(apps, scheme_editor):
    User = apps.get_model("kernel", "User")

    users = User.objects.filter(username__isnull=True)

    for user in users:
        email_split = user.email.split("@")
        username = email_split[0]

        user.username = username

    User.objects.bulk_update(users, fields=["username"])


class Migration(migrations.Migration):
    dependencies = [
        ('kernel', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'verbose_name': 'user', 'verbose_name_plural': 'users'},
        ),
        migrations.AlterModelManagers(
            name='user',
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.AddField(
            model_name='user',
            name='username',
            field=models.CharField(
                null=True,
                error_messages={'unique': 'A user with that username already exists.'},
                help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.',
                max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                verbose_name='username'
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(blank=True, max_length=254, verbose_name='email address'),
        ),
        migrations.RunPython(populate_username),
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(
                error_messages={'unique': 'A user with that username already exists.'},
                help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.',
                max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                verbose_name='username'
            ),
        )
    ]
