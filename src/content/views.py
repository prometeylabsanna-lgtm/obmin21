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
from src.leads.forms import ContactMessageForm
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
    })


def contacts_page(request):
    return render(request, 'content/contacts.html', {
        'page': ContactsPage.load(),
        'form': ContactMessageForm(),
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
