from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
import json

from src.network.models import City
from src.network.selectors import get_city_branches, get_visible_branches
from src.network.services import apply_city_cookie, set_active_city
from src.content.models import CitiesPage
from src.core.breadcrumbs import safe_reverse, trail
from src.core.exchange_mode import is_exchange_only, mode_meta, mode_text
from src.core.phones import phone_tel


def city_list(request):
    page = CitiesPage.load()
    return render(request, 'network/city_list.html', {
        'page': page,
        'cities_list': request.cities,
        'list_branches': getattr(request, 'list_branches', list(get_visible_branches())),
        'page_title': mode_meta(page, 'seo_title', 'title', limit=None, request=request),
        'page_description': mode_meta(page, 'seo_description', 'intro', request=request),
    })


def city_detail(request, slug):
    city = get_object_or_404(City, slug=slug, is_active=True)
    return render(request, 'network/city_detail.html', {
        'city': city,
        'branches': get_city_branches(city),
        'page_title': mode_meta(city, 'seo_title', 'name', limit=None, request=request),
        'page_description': mode_meta(city, 'seo_description', request=request),
        'breadcrumb_items': trail(
            ('Міста', safe_reverse('network:city_list')),
            (mode_text(city, 'name', request), None),
        ),
    })


def _posted_branch(request, city):
    raw = request.POST.get('branch') or request.POST.get('branch_id', '')
    if city is None or not raw:
        return None
    return city.branches.filter(pk=raw, is_active=True).first()


@require_POST
def set_city(request):
    slug = request.POST.get('city') or request.POST.get('slug', '')
    city = City.objects.filter(slug=slug, is_active=True).first()
    branch = _posted_branch(request, city)
    if city is None:
        city = request.city
        branch = getattr(request, 'active_branch', None)
    else:
        set_active_city(request, city, branch)
        branch = request.active_branch

    if request.headers.get('HX-Request'):
        response = render(request, 'partials/city_chrome.html', {
            'active_city': city,
            'active_branch': branch,
            'active_phone': city.phone if city else '',
            'phone_href': phone_tel(city.phone) if city else '',
            'cities': request.cities,
            'list_branches': getattr(request, 'list_branches', list(get_visible_branches())),
            'city_branches': list(get_city_branches(city)),
        })
        apply_city_cookie(response, city, branch)
        banner_title = mode_text(city, 'banner_title', request)
        banner_text = mode_text(city, 'banner_text', request)
        response['HX-Trigger'] = json.dumps({
            'cityChanged': {
                'slug': city.slug,
                'name': mode_text(city, 'name', request),
                'nameIn': city.name_in,
                'bannerUrl': city.banner_src(),
                'bannerTitle': banner_title,
                'bannerSuffix': mode_text(city, 'banner_suffix', request),
                'bannerText': banner_text,
                'bannerHidden': bool(
                    is_exchange_only(request) and not banner_title and not banner_text
                ),
                'branchId': branch.pk if branch else None,
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
        apply_city_cookie(response, city, branch)
    return response


def select_city_redirect(request, slug):
    city = get_object_or_404(City, slug=slug, is_active=True)
    set_active_city(request, city)
    response = redirect('core:home')
    apply_city_cookie(response, city, getattr(request, 'active_branch', None))
    return response
