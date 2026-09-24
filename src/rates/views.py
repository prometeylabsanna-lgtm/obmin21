from django.shortcuts import get_object_or_404, render

from src.content.models import RatesPage
from src.core.breadcrumbs import safe_reverse, trail
from src.rates.models import CurrencyPair, RateBoard
from src.rates.selectors import get_quote, get_quotes_for_city


def rates_page(request):
    board = request.GET.get('board', RateBoard.RETAIL)
    if board not in RateBoard.values:
        board = RateBoard.RETAIL
    rows, updated_at = get_quotes_for_city(request.city, board)
    return render(request, 'rates/rates_page.html', {
        'page': RatesPage.load(),
        'rate_rows': rows,
        'rate_updated_at': updated_at,
        'active_board': board,
        'boards': RateBoard.choices,
    })


def pair_detail(request, slug):
    pair = get_object_or_404(CurrencyPair, slug=slug, is_active=True)
    quote = get_quote(pair, request.city, RateBoard.RETAIL)
    return render(request, 'rates/pair_detail.html', {
        'pair': pair,
        'quote': quote,
        'page_title': pair.seo_title or f'{pair.code} — курс обміну',
        'page_description': pair.seo_description or (pair.intro[:160] if pair.intro else ''),
        'breadcrumb_items': trail(
            ('Курси', safe_reverse('rates:rates_page')),
            (pair.code, None),
        ),
    })
