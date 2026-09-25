from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from src.network.models import City
from src.network.selectors import get_city_branches
from src.network.services import apply_city_cookie, set_active_city
from src.content.models import CitiesPage
from src.core.breadcrumbs import safe_reverse, trail


def city_list(request):
    return render(request, 'network/city_list.html', {
        'page': CitiesPage.load(),
        'cities_list': request.cities,
    })


def city_detail(request, slug):
    city = get_object_or_404(City, slug=slug, is_active=True)
    return render(request, 'network/city_detail.html', {
        'city': city,
        'branches': get_city_branches(city),
        'page_title': city.seo_title or city.name,
        'page_description': city.seo_description,
        'breadcrumb_items': trail(
            ('Міста', safe_reverse('network:city_list')),
            (city.name, None),
        ),
    })


@require_POST
def set_city(request):
    slug = request.POST.get('city') or request.POST.get('slug', '')
    city = City.objects.filter(slug=slug, is_active=True).first()
    if city is None:
        city = request.city
    else:
        set_active_city(request, city)

    if request.headers.get('HX-Request'):
        response = render(request, 'partials/city_chrome.html', {
            'active_city': city,
            'active_phone': city.phone if city else '',
            'cities': request.cities,
            'city_branches': list(get_city_branches(city)),
        })
        apply_city_cookie(response, city)
        response['HX-Trigger'] = 'cityChanged'
        return response

    response = redirect(request.META.get('HTTP_REFERER', '/'))
    if city:
        apply_city_cookie(response, city)
    return response


def select_city_redirect(request, slug):
    city = get_object_or_404(City, slug=slug, is_active=True)
    set_active_city(request, city)
    response = redirect('core:home')
    apply_city_cookie(response, city)
    return response
