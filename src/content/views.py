from django.shortcuts import render

from src.blog.selectors import get_published_posts
from src.content.models import (
    AdvantageItem,
    AdvantagesPage,
    ContactsPage,
    FaqItem,
    FaqPage,
    PrivacyPage,
    Service,
    ServicesPage,
)
from src.content.service_blocks import SERVICE_BLOCKS
from src.network.models import Branch
from src.reviews.selectors import get_published_reviews


def services_list(request):
    page = ServicesPage.load()
    services = []
    for svc in Service.objects.filter(is_active=True):
        block = SERVICE_BLOCKS.get(svc.slug, {})
        svc.block_text = block.get('text') or svc.short_desc
        svc.block_points = list(block.get('points', ()))
        svc.block_cta = block.get('cta', 'Забронювати заявку')
        services.append(svc)
    return render(request, 'content/services_list.html', {
        'page': page,
        'services': services,
        'home_reviews': list(get_published_reviews()[:8]),
        'news_posts': list(get_published_posts()[:10]),
        'page_title': page.seo_title or page.title,
        'page_description': page.seo_description or page.intro[:160],
    })


def advantages_page(request):
    return render(request, 'content/advantages.html', {
        'page': AdvantagesPage.load(),
        'items': AdvantageItem.objects.filter(is_active=True),
        'audiences': AdvantageItem.Audience.choices,
        'home_reviews': list(get_published_reviews()[:8]),
    })


def contacts_page(request):
    map_branches = list(
        Branch.objects.filter(is_active=True, city__is_active=True)
        .select_related('city')
        .order_by('city__sort_order', 'sort_order', 'id')
    )
    active = map_branches[0] if map_branches else None
    if request.city:
        for item in map_branches:
            if item.city_id == request.city.id:
                active = item
                break
    return render(request, 'content/contacts.html', {
        'page': ContactsPage.load(),
        'map_branches': map_branches,
        'active_branch': active,
        'branches': request.city_branches,
    })


def privacy_page(request):
    return render(request, 'content/privacy.html', {
        'page': PrivacyPage.load(),
    })


def faq_page(request):
    page = FaqPage.load()
    return render(request, 'content/faq.html', {
        'page': page,
        'items': FaqItem.objects.filter(is_active=True),
        'page_title': page.seo_title or page.title,
        'page_description': page.seo_description or page.intro[:160],
    })
