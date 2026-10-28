from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import render
from django.utils.html import strip_tags
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap as django_sitemap
import logging

from src.core.exchange_mode import is_exchange_only, mode_text
from src.core.sitemaps import sitemaps
from src.core.theme import theme_css_cached

from src.blog.selectors import get_published_posts
from src.content.faq_defaults import public_faq_items
from src.content.models import HomePage, HomeStat, Service
from src.network.selectors import get_city_by_slug
from src.rates.models import RateBoard
from src.rates.selectors import get_quotes_for_city, public_board, public_boards
from src.reviews.selectors import get_published_reviews

logger = logging.getLogger(__name__)

_RETAIL_ORDER = {'USD': 0, 'EUR': 1, 'PLN': 2}
_CRYPTO_ORDER = {'BTC': 0, 'ETH': 1, 'USDT': 2}


def _ordered_rows(rows, preferred):
    return sorted(rows, key=lambda row: preferred.get(row['pair'].flag_code, 90))


def _home_retail_rows(city):
    rows, updated_at = get_quotes_for_city(city, RateBoard.RETAIL)
    return _ordered_rows(rows, _RETAIL_ORDER), updated_at


def _home_stat_cards(page, request):
    cards = []
    in_mode = is_exchange_only(request)
    for item in HomeStat.objects.filter(page=page, is_active=True).visible():
        title = strip_tags(mode_text(item, 'number', request) or '').strip()
        text = strip_tags(mode_text(item, 'text', request) or '').strip()
        if in_mode:
            if not text:
                continue
            card = {'text': text}
            if title:
                card['title'] = title
            cards.append(card)
            continue
        if title or text:
            cards.append({'title': title, 'text': text})
    return cards


def _calc_currencies(rows):
    items = [{'code': 'UAH', 'name': 'Гривня', 'buy': '1', 'sell': '1', 'pair_id': ''}]
    seen = {'UAH'}
    for row in rows:
        code = (row['pair'].flag_code or '').upper()
        if not code or code in seen:
            continue
        seen.add(code)
        items.append({
            'code': code,
            'name': row['pair'].name,
            'buy': str(row['quote'].buy),
            'sell': str(row['quote'].sell),
            'pair_id': row['pair'].pk,
        })
    return items


class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        city = self.request.city
        board = public_board(self.request.GET.get('board', RateBoard.RETAIL))
        if board not in RateBoard.values:
            board = RateBoard.RETAIL
        if board == RateBoard.CRYPTO:
            rows, updated_at = _home_retail_rows(city)
        else:
            rows, updated_at = get_quotes_for_city(city, board)
        if board == RateBoard.RETAIL:
            rows = _ordered_rows(rows, _RETAIL_ORDER)
        page = HomePage.load()
        ctx.update({
            'page': page,
            'rate_rows': rows,
            'calc_currencies': _calc_currencies(rows),
            'rate_updated_at': updated_at,
            'active_board': board,
            'boards': public_boards(),
            'home_rates_compact': True,
            'services': Service.objects.filter(
                is_active=True,
                show_on_home=True,
            ).visible()[:6],
            'faq_items': public_faq_items(limit=8),
            'news_posts': list(get_published_posts()[:10]),
            'home_reviews': get_published_reviews(8),
            'home_stats': _home_stat_cards(page, self.request),
        })
        return ctx


def rates_partial(request):
    board = public_board(request.GET.get('board', RateBoard.RETAIL))
    if board not in RateBoard.values:
        board = RateBoard.RETAIL
    home_compact = request.GET.get('home') == '1'
    if home_compact and board == RateBoard.CRYPTO:
        rows, updated_at = _home_retail_rows(request.city)
    else:
        rows, updated_at = get_quotes_for_city(request.city, board)
    if home_compact and board == RateBoard.RETAIL:
        rows = _ordered_rows(rows, _RETAIL_ORDER)
    elif board == RateBoard.CRYPTO and not home_compact:
        rows = _ordered_rows(rows, _CRYPTO_ORDER)
    return render(request, 'partials/rates_table.html', {
        'rate_rows': rows,
        'rate_updated_at': updated_at,
        'active_board': board,
        'boards': public_boards(),
        'hide_full_table_link': request.GET.get('hide_full') == '1',
        'home_rates_compact': home_compact,
    })


def _home_branch_phone(city):
    if city and city.phone:
        return city.phone
    from src.core.models import SiteSettings

    return SiteSettings.load().default_phone or ''


@require_GET
@never_cache
def home_branch(request):
    city = getattr(request, 'city', None)
    return render(request, 'partials/home_branch.html', {
        'eo': is_exchange_only(request),
        'cities': getattr(request, 'cities', []),
        'active_city': city,
        'city_branches': getattr(request, 'city_branches', []),
        'page': HomePage.load(),
        'active_phone': _home_branch_phone(city),
    })


def _quotes_city(request):
    slug = (request.GET.get('city') or '').strip()
    if slug:
        city = get_city_by_slug(slug)
        if city is not None:
            return city
    return request.city


def quotes_json(request):
    board = public_board(request.GET.get('board', RateBoard.RETAIL))
    if board not in RateBoard.values:
        board = RateBoard.RETAIL
    rows, _updated = get_quotes_for_city(_quotes_city(request), board)
    if board == RateBoard.CRYPTO:
        rows = _ordered_rows(rows, _CRYPTO_ORDER)
    payload = []
    for row in rows:
        payload.append({
            'id': row['pair'].pk,
            'code': row['pair'].flag_code,
            'buy': str(row['quote'].buy),
            'sell': str(row['quote'].sell),
        })
    return JsonResponse({'quotes': payload})


def robots_txt(request):
    return render(
        request,
        'core/robots.txt',
        {'disallow_default_admin': settings.ADMIN_URL == 'admin/'},
        content_type='text/plain',
    )


@require_GET
def safe_sitemap(request):
    try:
        return django_sitemap(request, sitemaps=sitemaps)
    except Exception:
        logger.exception('sitemap.xml failed')
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
        )
        return HttpResponse(xml, content_type='application/xml')


@require_GET
def theme_css(request):
    response = HttpResponse(theme_css_cached(), content_type='text/css')
    response['Cache-Control'] = 'public, max-age=300'
    return response


def page_not_found(request, exception):
    return render(request, 'core/404.html', status=404)


def tinymce_disabled(request):
    return HttpResponseNotFound()
