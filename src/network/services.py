from django.conf import settings

from src.network.selectors import pick_active_branch


def set_active_city(request, city, branch=None):
    request.session['city_slug'] = city.slug
    request.city = city
    request.city_branches = list(city.branches.filter(is_active=True))
    active = branch if branch is not None else pick_active_branch(city, None)
    if active is not None and active.city_id != city.pk:
        active = pick_active_branch(city, None)
    request.active_branch = active
    if active is not None:
        request.session['branch_id'] = active.pk
    else:
        request.session.pop('branch_id', None)
    return city


def apply_city_cookie(response, city, branch=None):
    response.set_cookie(
        settings.CITY_COOKIE_NAME,
        city.slug,
        max_age=settings.CITY_COOKIE_MAX_AGE,
        samesite='Lax',
    )
    if branch is not None:
        response.set_cookie(
            settings.BRANCH_COOKIE_NAME,
            str(branch.pk),
            max_age=settings.CITY_COOKIE_MAX_AGE,
            samesite='Lax',
        )
    return response
