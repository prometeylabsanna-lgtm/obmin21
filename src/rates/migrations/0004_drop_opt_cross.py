from django.db import migrations, models


def drop_opt_and_cross(apps, schema_editor):
    Quote = apps.get_model('rates', 'Quote')
    Quote.objects.filter(board__in=('wholesale', 'cross')).delete()
    Pair = apps.get_model('rates', 'CurrencyPair')
    Pair.objects.filter(slug='eur-usd').update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [
        ('rates', '0003_seo_field_labels'),
    ]

    operations = [
        migrations.RunPython(drop_opt_and_cross, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='quote',
            name='board',
            field=models.CharField(
                choices=[('retail', 'Готівка'), ('crypto', 'Крипто')],
                default='retail',
                max_length=16,
                verbose_name='Дошка',
            ),
        ),
    ]
