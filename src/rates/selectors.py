from django.db.models import Q

from src.rates.models import CurrencyPair, Quote, RateBoard


def get_active_pairs():
    return CurrencyPair.objects.filter(is_active=True)


def get_pair_by_slug(slug):
    return CurrencyPair.objects.filter(slug=slug, is_active=True).first()


def get_quotes_for_city(city, board=RateBoard.RETAIL):
    city_id = city.id if city else None
    pairs = list(get_active_pairs())
    if not pairs:
        return [], None

    quotes = (
        Quote.objects.filter(
            pair__in=pairs,
            board=board,
            is_active=True,
        )
        .filter(Q(city_id=city_id) | Q(city__isnull=True))
        .select_related('pair', 'city')
    )

    by_pair = {}
    updated_at = None
    for quote in quotes:
        existing = by_pair.get(quote.pair_id)
        prefer_city = quote.city_id is not None
        if existing is None:
            by_pair[quote.pair_id] = quote
        elif prefer_city and existing.city_id is None:
            by_pair[quote.pair_id] = quote
        if updated_at is None or quote.updated_at > updated_at:
            updated_at = quote.updated_at

    rows = []
    for pair in pairs:
        quote = by_pair.get(pair.id)
        if quote is None:
            continue
        if board in (RateBoard.CROSS, RateBoard.CRYPTO) or pair.base_code == 'UAH' or board != RateBoard.RETAIL:
            rows.append({'pair': pair, 'quote': quote})
        else:
            rows.append({'pair': pair, 'quote': quote})

    # Filter pairs that belong to board visually: show all with quotes for board
    return rows, updated_at


def get_quote(pair, city, board=RateBoard.RETAIL):
    city_id = city.id if city else None
    qs = Quote.objects.filter(pair=pair, board=board, is_active=True)
    city_quote = qs.filter(city_id=city_id).first() if city_id else None
    if city_quote:
        return city_quote
    return qs.filter(city__isnull=True).first()
