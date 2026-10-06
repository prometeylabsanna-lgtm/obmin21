from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
import json

from src.network.models import City
from src.network.selectors import get_city_branches
from src.network.services import apply_city_cookie, set_active_city
from src.content.models import CitiesPage
from src.core.breadcrumbs import safe_reverse, trail
from src.core.phones import phone_tel


def city_list(request):
    page = CitiesPage.load()
    return render(request, 'network/city_list.html', {
        'page': page,
        'cities_list': request.cities,
        'page_title': page.seo_title or page.title,
        'page_description': page.seo_description or page.intro[:160],
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
            'phone_href': phone_tel(city.phone) if city else '',
            'cities': request.cities,
            'city_branches': list(get_city_branches(city)),
        })
        apply_city_cookie(response, city)
        response['HX-Trigger'] = json.dumps({
            'cityChanged': {
                'slug': city.slug,
                'name': city.name,
                'nameIn': city.name_in,
                'bannerUrl': city.banner_src(),
                'bannerTitle': city.banner_title,
                'bannerSuffix': city.banner_suffix,
                'bannerText': city.banner_text,
            }
        })
        return response

    next_url = request.META.get('HTTP_REFERER', '')
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = '/'
    response = redirect(next_url)
    if city:
        apply_city_cookie(response, city)
    return response


def select_city_redirect(request, slug):
    city = get_object_or_404(City, slug=slug, is_active=True)
    set_active_city(request, city)
    response = redirect('core:home')
    apply_city_cookie(response, city)
    return response
