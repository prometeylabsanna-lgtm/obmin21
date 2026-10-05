from src.content.models import Service
from src.core.breadcrumbs import breadcrumbs_for_request
from src.core.models import SiteSettings
from src.core.theme import URL_THEME_MAP, theme_version


def site_chrome(request):
    settings = SiteSettings.load()
    city = getattr(request, 'city', None)
    phone = ''
    if city and city.phone:
        phone = city.phone
    elif settings.default_phone:
        phone = settings.default_phone

    return {
        'site_settings': settings,
        'active_city': city,
        'active_phone': phone,
        'cities': getattr(request, 'cities', []),
        'city_branches': getattr(request, 'city_branches', []),
        'breadcrumb_items': breadcrumbs_for_request(request),
        'footer_services': Service.objects.filter(is_active=True)[:6],
        'theme_version': theme_version(),
    }


def page_theme(request):
    match = getattr(request, 'resolver_match', None)
    url_name = ''
    if match and match.namespace and match.url_name:
        url_name = f'{match.namespace}:{match.url_name}'
    elif match and match.url_name:
        url_name = match.url_name
    return {
        'page_theme': URL_THEME_MAP.get(url_name, 'home'),
    }
