from django.conf import settings

from src.network.selectors import get_active_cities, get_city_by_slug, get_default_city


class CityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        cities = list(get_active_cities())
        request.cities = cities

        slug = request.session.get('city_slug') or request.COOKIES.get(
            settings.CITY_COOKIE_NAME,
            '',
        )
        city = get_city_by_slug(slug) if slug else None
        if city is None:
            city = get_default_city()

        request.city = city
        request.city_branches = list(city.branches.filter(is_active=True)) if city else []

        response = self.get_response(request)

        if city and request.COOKIES.get(settings.CITY_COOKIE_NAME) != city.slug:
            response.set_cookie(
                settings.CITY_COOKIE_NAME,
                city.slug,
                max_age=settings.CITY_COOKIE_MAX_AGE,
                samesite='Lax',
            )
        return response
