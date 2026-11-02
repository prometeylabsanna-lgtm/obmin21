from decimal import Decimal

from django.db import migrations, models
from django.db.models import F, Q


def _fix_invalid_quotes(apps, schema_editor):
    Quote = apps.get_model('rates', 'Quote')
    max_value = Decimal('100000000')
    for quote in Quote.objects.all().iterator():
        buy = quote.buy
        sell = quote.sell
        changed = False
        if buy is None or buy <= 0:
            buy = Decimal('0.0001')
            changed = True
        if sell is None or sell <= 0:
            sell = Decimal('0.0001')
            changed = True
        if buy > max_value:
            buy = max_value
            changed = True
        if sell > max_value:
            sell = max_value
            changed = True
        if buy > sell:
            sell = buy
            changed = True
        if changed:
            quote.buy = buy
            quote.sell = sell
            quote.save(update_fields=['buy', 'sell'])


class Migration(migrations.Migration):

    dependencies = [
        ('rates', '0009_quote_inherits_base'),
    ]

    operations = [
        migrations.RunPython(_fix_invalid_quotes, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='quote',
            constraint=models.CheckConstraint(
                condition=Q(buy__gt=0),
                name='quote_buy_positive',
            ),
        ),
        migrations.AddConstraint(
            model_name='quote',
            constraint=models.CheckConstraint(
                condition=Q(sell__gt=0),
                name='quote_sell_positive',
            ),
        ),
        migrations.AddConstraint(
            model_name='quote',
            constraint=models.CheckConstraint(
                condition=Q(buy__lte=F('sell')),
                name='quote_buy_lte_sell',
            ),
        ),
        migrations.AddConstraint(
            model_name='quote',
            constraint=models.CheckConstraint(
                condition=Q(buy__lte=Decimal('100000000')),
                name='quote_buy_max',
            ),
        ),
        migrations.AddConstraint(
            model_name='quote',
            constraint=models.CheckConstraint(
                condition=Q(sell__lte=Decimal('100000000')),
                name='quote_sell_max',
            ),
        ),
    ]
