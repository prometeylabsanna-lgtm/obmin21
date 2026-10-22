from django.db import migrations

from src.core.exchange_safe_approve import (
    clear_approved_exchange_safe,
    mark_approved_exchange_safe,
)


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0008_exchange_safe_currency_help'),
        ('rates', '0006_pair_meta_mode'),
        ('reviews', '0006_exchange_safe_currency_help'),
    ]

    operations = [
        migrations.RunPython(
            mark_approved_exchange_safe,
            clear_approved_exchange_safe,
        ),
    ]
