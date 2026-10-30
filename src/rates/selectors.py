from django.db.models import Q

from src.core.exchange_mode import exchange_only
from src.rates.models import CurrencyPair, Quote, RateBoard


def get_active_pairs():
    return CurrencyPair.objects.filter(is_active=True).visible()


def public_board(board):
    if board == RateBoard.CRYPTO and exchange_only():
        return RateBoard.RETAIL
    return board


def public_boards():
    if not exchange_only():
        return RateBoard.choices
    return [item for item in RateBoard.choices if item[0] != RateBoard.CRYPTO]


def _quote_visible(quote):
    return bool(
        quote
        and quote.is_active
        and quote.buy > 0
        and quote.sell > 0
    )


def get_quotes_for_city(city, board=RateBoard.RETAIL):
    city_id = city.id if city else None
    pairs = list(get_active_pairs())
    if not pairs:
        return [], None

    quotes = (
        Quote.objects.filter(
            pair__in=pairs,
            board=board,
        )
        .filter(Q(city_id=city_id) | Q(city__isnull=True))
        .select_related('pair', 'city')
    )

    city_rows = {}
    global_rows = {}
    for quote in quotes:
        if quote.city_id:
            city_rows[quote.pair_id] = quote
        else:
            global_rows[quote.pair_id] = quote

    rows = []
    updated_at = None
    for pair in pairs:
        if pair.id in city_rows:
            quote = city_rows[pair.id]
        else:
            quote = global_rows.get(pair.id)
        if not _quote_visible(quote):
            continue
        rows.append({'pair': pair, 'quote': quote})
        if updated_at is None or quote.updated_at > updated_at:
            updated_at = quote.updated_at

    return rows, updated_at


def get_quote(pair, city, board=RateBoard.RETAIL):
    if pair is None or not getattr(pair, 'pk', None):
        return None
    if not CurrencyPair.objects.visible().filter(pk=pair.pk).exists():
        return None
    city_id = city.id if city else None
    if city_id:
        city_quote = Quote.objects.filter(
            pair=pair,
            board=board,
            city_id=city_id,
        ).first()
        if city_quote is not None:
            return city_quote if _quote_visible(city_quote) else None
    global_quote = Quote.objects.filter(
        pair=pair,
        board=board,
        city__isnull=True,
    ).first()
    return global_quote if _quote_visible(global_quote) else None
