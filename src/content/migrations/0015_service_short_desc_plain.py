from html import unescape
import re

from django.db import migrations, models


def _plain(value: str) -> str:
    text = unescape(re.sub(r'<[^>]+>', '', str(value or '')))
    return re.sub(r'\s+', ' ', text.replace('\xa0', ' ')).strip()[:400]


def strip_short_desc(apps, schema_editor):
    Service = apps.get_model('content', 'Service')
    for row in Service.objects.all().only('id', 'short_desc'):
        cleaned = _plain(row.short_desc)
        if cleaned != (row.short_desc or ''):
            Service.objects.filter(pk=row.pk).update(short_desc=cleaned)


class Migration(migrations.Migration):

    dependencies = [
        ('content', '0014_color_highlight'),
    ]

    operations = [
        migrations.RunPython(strip_short_desc, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='service',
            name='short_desc',
            field=models.CharField(max_length=400, verbose_name='Короткий опис'),
        ),
    ]
