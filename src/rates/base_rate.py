"""Міський курс читає базовий, доки його явно не перевизначили."""


def sync_inherits_base(quote):
    """Новий збіг із базою вмикає наслідування. Явний прапорець не збивається."""
    if not quote.city_id or not quote.pair_id or not quote.board:
        quote.inherits_base = False
        return
    model = type(quote)
    base = model.objects.filter(
        pair_id=quote.pair_id,
        board=quote.board,
        city__isnull=True,
    ).only('buy', 'sell', 'is_active').first()
    previous = None
    if quote.pk:
        previous = model.objects.filter(pk=quote.pk).values(
            'buy', 'sell', 'is_active', 'inherits_base',
        ).first()
    equals = _matches_base(quote, base)
    if previous is None:
        if quote.inherits_base:
            return
        quote.inherits_base = equals
        return
    rates_same = previous['buy'] == quote.buy and previous['sell'] == quote.sell
    if rates_same:
        if quote.inherits_base != previous['inherits_base']:
            return
        quote.inherits_base = previous['inherits_base']
        return
    quote.inherits_base = equals


def assign_inherits_base(apps, schema_editor):
    quote = apps.get_model('rates', 'Quote')
    bases = {
        (row.pair_id, row.board): row
        for row in quote.objects.filter(city__isnull=True)
    }
    for row in quote.objects.filter(city__isnull=False).iterator():
        base = bases.get((row.pair_id, row.board))
        inherits = bool(
            base is not None
            and row.buy == base.buy
            and row.sell == base.sell
            and row.is_active == base.is_active
        )
        if row.inherits_base != inherits:
            quote.objects.filter(pk=row.pk).update(inherits_base=inherits)


def _matches_base(quote, base):
    if base is None:
        return False
    return (
        quote.buy == base.buy
        and quote.sell == base.sell
        and quote.is_active == base.is_active
    )
