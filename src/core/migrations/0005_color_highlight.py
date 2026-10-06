from django.core.validators import RegexValidator
from django.db import migrations, models

HELP = 'Натисніть квадратик, щоб обрати колір. Зміна з’явиться на сайті після збереження.'
HEX = RegexValidator(message='Оберіть колір у палітрі.', regex='^#[0-9A-Fa-f]{6}$')


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0004_restore_gold_accent'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitesettings',
            name='header_color_accent',
            field=models.CharField(
                default='#ca8d42',
                help_text=HELP,
                max_length=7,
                validators=[HEX],
                verbose_name='Колір акценту шапки',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='header_color_highlight',
            field=models.CharField(
                default='#b87b2c',
                help_text=HELP,
                max_length=7,
                validators=[HEX],
                verbose_name='Колір підсвітки шапки',
            ),
        ),
        migrations.AlterField(
            model_name='sitesettings',
            name='footer_color_accent',
            field=models.CharField(
                default='#ca8d42',
                help_text=HELP,
                max_length=7,
                validators=[HEX],
                verbose_name='Колір акценту підвалу',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='footer_color_highlight',
            field=models.CharField(
                default='#b87b2c',
                help_text=HELP,
                max_length=7,
                validators=[HEX],
                verbose_name='Колір підсвітки підвалу',
            ),
        ),
    ]
