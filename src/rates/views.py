from django.http import Http404
from django.shortcuts import render

from src.content.models import RatesPage
from src.core.breadcrumbs import safe_reverse, trail
from src.core.exchange_mode import exchange_only, raise_hidden
from src.rates.models import CurrencyPair, RateBoard
from src.rates.selectors import get_quote, get_quotes_for_city, public_board, public_boards


def rates_page(request):
    board = public_board(request.GET.get('board', RateBoard.RETAIL))
    if board not in (RateBoard.RETAIL, RateBoard.CRYPTO):
        board = RateBoard.RETAIL
    rows, updated_at = get_quotes_for_city(request.city, board)
    page = RatesPage.load()
    return render(request, 'rates/rates_page.html', {
        'page': page,
        'rate_rows': rows,
        'rate_updated_at': updated_at,
        'active_board': board,
        'boards': public_boards(),
        'page_title': page.seo_title or page.title,
        'page_description': page.seo_description or (page.intro[:160] if page.intro else ''),
    })


def pair_detail(request, slug):
    active = CurrencyPair.objects.filter(slug=slug, is_active=True)
    pair = active.visible().first()
    if pair is None:
        if exchange_only() and active.exists():
            raise_hidden()
        raise Http404
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
