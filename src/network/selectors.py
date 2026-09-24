from src.network.models import Branch, City


def get_active_cities():
    return City.objects.filter(is_active=True)


def get_city_by_slug(slug):
    if not slug:
        return None
    return City.objects.filter(slug=slug, is_active=True).first()


def get_default_city():
    return get_active_cities().first()


def get_city_branches(city):
    if city is None:
        return Branch.objects.none()
    return city.branches.filter(is_active=True)
