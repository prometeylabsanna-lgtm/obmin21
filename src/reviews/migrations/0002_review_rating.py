from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='review',
            name='rating',
            field=models.PositiveSmallIntegerField(default=5, verbose_name='Оцінка'),
        ),
    ]
