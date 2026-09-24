from django.conf import settings


def set_active_city(request, city):
    request.session['city_slug'] = city.slug
    request.city = city
    request.city_branches = list(city.branches.filter(is_active=True))
    return city


def apply_city_cookie(response, city):
    response.set_cookie(
        settings.CITY_COOKIE_NAME,
        city.slug,
        max_age=settings.CITY_COOKIE_MAX_AGE,
        samesite='Lax',
    )
    return response
