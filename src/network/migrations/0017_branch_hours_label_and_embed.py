from django.db import migrations, models


def fill_empty_map_embeds(apps, schema_editor):
    from src.network.map_embed_fill import fill_empty_map_embeds as fill_embeds

    fill_embeds(apps, schema_editor)


class Migration(migrations.Migration):
    dependencies = [
        ('network', '0016_city_banner_suffix_blank'),
    ]

    operations = [
        migrations.AlterField(
            model_name='branch',
            name='hours',
            field=models.CharField(
                blank=True,
                help_text='Наприклад: Пн–Нд, 8:00–21:00',
                max_length=120,
                verbose_name='Графік роботи',
            ),
        ),
        migrations.RunPython(fill_empty_map_embeds, migrations.RunPython.noop),
    ]
