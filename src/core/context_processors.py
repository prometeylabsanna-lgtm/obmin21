from src.core.breadcrumbs import breadcrumbs_for_request
from src.core.models import SiteSettings


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
    }
