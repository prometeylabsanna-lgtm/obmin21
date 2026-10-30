from urllib.parse import quote_plus

from django.db import migrations, models


def _embed(address):
    text = (address or '').strip()
    if not text:
        return ''
    return (
        'https://maps.google.com/maps?q='
        f'{quote_plus(f"{text}, Ukraine")}&z=15&hl=uk&output=embed'
    )


def fill_empty_map_embeds(apps, schema_editor):
    Branch = apps.get_model('network', 'Branch')
    for branch in Branch.objects.all().iterator():
        if str(branch.map_embed_url or '').strip():
            continue
        filled = _embed(branch.address)
        if not filled:
            continue
        branch.map_embed_url = filled
        branch.save(update_fields=['map_embed_url'])


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
