from django.db import migrations


def reactivate_eur_usd(apps, schema_editor):
    Pair = apps.get_model('rates', 'CurrencyPair')
    Pair.objects.filter(slug='eur-usd').update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [
        ('rates', '0006_pair_meta_mode'),
    ]

    operations = [
        migrations.RunPython(reactivate_eur_usd, migrations.RunPython.noop),
    ]
