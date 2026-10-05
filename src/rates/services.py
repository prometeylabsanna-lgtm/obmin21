from src.rates.models import Quote


def ensure_city_quotes(city) -> int:
    created = 0
    globals_qs = Quote.objects.filter(city__isnull=True, is_active=True)
    for quote in globals_qs:
        _, was_created = Quote.objects.get_or_create(
            pair=quote.pair,
            board=quote.board,
            city=city,
            defaults={
                'buy': quote.buy,
                'sell': quote.sell,
                'is_active': True,
            },
        )
        if was_created:
            created += 1
    return created
