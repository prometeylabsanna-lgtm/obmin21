from django.db.models import Q

from src.core.crypto_visibility import crypto_enabled, pair_is_crypto
from src.rates.models import CurrencyPair, Quote, RateBoard


def get_active_pairs():
    qs = CurrencyPair.objects.filter(is_active=True)
    if crypto_enabled():
        return qs
    kept = [pair.pk for pair in qs if not pair_is_crypto(pair)]
    return qs.filter(pk__in=kept)


def public_board(board):
    if board == RateBoard.CRYPTO and not crypto_enabled():
        return RateBoard.RETAIL
    return board


def public_boards():
    if crypto_enabled():
        return RateBoard.choices
    return [item for item in RateBoard.choices if item[0] != RateBoard.CRYPTO]


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
        if quote.buy <= 0 or quote.sell <= 0:
            continue
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
        rows.append({'pair': pair, 'quote': quote})

    return rows, updated_at


def get_quote(pair, city, board=RateBoard.RETAIL):
    city_id = city.id if city else None
    qs = Quote.objects.filter(pair=pair, board=board, is_active=True)
    city_quote = qs.filter(city_id=city_id).first() if city_id else None
    if city_quote and city_quote.buy > 0 and city_quote.sell > 0:
        return city_quote
    global_quote = qs.filter(city__isnull=True).first()
    if global_quote and global_quote.buy > 0 and global_quote.sell > 0:
        return global_quote
    return None
