from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_color_highlight'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='crypto_enabled',
            field=models.BooleanField(
                default=True,
                verbose_name='Показувати криптовалюту на сайті',
            ),
        ),
    ]
