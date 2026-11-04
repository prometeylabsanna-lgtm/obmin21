import re

from django.conf import settings as django_settings

from src.content.models import Service
from src.content.visit_steps import VisitSteps, minutes_phrase
from src.core.breadcrumbs import breadcrumbs_for_request
from src.core.exchange_mode import exchange_only
from src.core.models import SiteSettings
from src.core.phones import get_contacts
from src.core.site_chrome import footer_columns, header_cta, header_menu, site_icons
from src.core.theme import URL_THEME_MAP, theme_version


def site_chrome(request):
    settings = SiteSettings.load()
    city = getattr(request, 'city', None)
    contacts = get_contacts(request, settings)
    services = list(Service.objects.filter(is_active=True).visible()[:6])

    gtm_id = getattr(django_settings, 'GTM_ID', '') or ''
    return {
        'gtm_id': gtm_id if re.fullmatch(r'GTM-[A-Z0-9]+', gtm_id) else '',
        'site_settings': settings,
        'active_city': city,
        'active_phone': contacts['phone'],
        'phone_href': contacts['phone_href'],
        'telegram_href': contacts['telegram_url'],
        'telegram_display': contacts['telegram_display'],
        'site_contacts': contacts,
        'cities': getattr(request, 'cities', []),
        'city_branches': getattr(request, 'city_branches', []),
        'list_branches': getattr(request, 'list_branches', []),
        'active_branch': getattr(request, 'active_branch', None),
        'breadcrumb_items': breadcrumbs_for_request(request),
        'exchange_only': exchange_only(request),
        'visit_steps': VisitSteps.load(),
        'rate_hold_label': minutes_phrase(settings.rate_hold_minutes),
        'footer_services': services,
        # CMS шапки/підвалу (FE підключає в partials/header, mobile_nav, footer, base).
        'header_menu': header_menu(request),
        'header_cta': header_cta(settings),
        'footer_columns': footer_columns(request, services),
        'site_icons': site_icons(settings),
        'theme_version': theme_version(),
    }


_PAGE_STYLES = {
    'core:home': frozenset({'rates', 'faq', 'home'}),
    'content:faq': frozenset({'faq', 'home'}),
    'content:services': frozenset({'home', 'faq', 'pages'}),
    'content:advantages': frozenset({'home', 'faq', 'pages', 'advantages'}),
    'content:contacts': frozenset({'contacts'}),
    'content:privacy': frozenset({'legal'}),
    'content:offer': frozenset({'legal'}),
    'content:cookies': frozenset({'legal'}),
    'rates:rates_page': frozenset({'rates', 'pages'}),
    'rates:pair_detail': frozenset({'pages'}),
    'blog:post_list': frozenset({'blog'}),
    'blog:category': frozenset({'blog'}),
    'blog:post_detail': frozenset({'article'}),
    'network:city_list': frozenset({'pages'}),
    'network:city_detail': frozenset({'pages'}),
    'reviews:review_list': frozenset({'pages'}),
}
_DEFAULT_PAGE_STYLES = frozenset({'pages'})


def page_theme(request):
    match = getattr(request, 'resolver_match', None)
    url_name = ''
    if match and match.namespace and match.url_name:
        url_name = f'{match.namespace}:{match.url_name}'
    elif match and match.url_name:
        url_name = match.url_name
    return {
        'page_theme': URL_THEME_MAP.get(url_name, 'home'),
        'page_styles': _PAGE_STYLES.get(url_name, _DEFAULT_PAGE_STYLES),
    }
