from django.conf import settings

from src.network.selectors import (
    get_active_cities,
    get_city_by_slug,
    get_default_city,
    get_visible_branches,
    pick_active_branch,
)


class CityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        cities = list(get_active_cities())
        request.cities = cities
        request.list_branches = list(get_visible_branches())

        slug = request.session.get('city_slug') or request.COOKIES.get(
            settings.CITY_COOKIE_NAME,
            '',
        )
        city = get_city_by_slug(slug) if slug else None
        if city is None:
            city = get_default_city()

        branch_id = request.session.get('branch_id') or request.COOKIES.get(
            settings.BRANCH_COOKIE_NAME,
            '',
        )
        request.city = city
        request.city_branches = list(city.branches.filter(is_active=True)) if city else []
        request.active_branch = pick_active_branch(city, branch_id)
        if request.active_branch is not None:
            request.session['branch_id'] = request.active_branch.pk

        response = self.get_response(request)

        city = getattr(request, 'city', None)
        branch = getattr(request, 'active_branch', None)
        if city and request.COOKIES.get(settings.CITY_COOKIE_NAME) != city.slug:
            response.set_cookie(
                settings.CITY_COOKIE_NAME,
                city.slug,
                max_age=settings.CITY_COOKIE_MAX_AGE,
                samesite='Lax',
            )
        if (
            branch is not None
            and request.COOKIES.get(settings.BRANCH_COOKIE_NAME) != str(branch.pk)
        ):
            response.set_cookie(
                settings.BRANCH_COOKIE_NAME,
                str(branch.pk),
                max_age=settings.CITY_COOKIE_MAX_AGE,
                samesite='Lax',
            )
        return response
