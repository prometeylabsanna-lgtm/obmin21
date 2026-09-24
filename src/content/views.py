from django.shortcuts import get_object_or_404, render

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
from src.core.breadcrumbs import safe_reverse, trail
from src.leads.forms import ContactMessageForm


def services_list(request):
    return render(request, 'content/services_list.html', {
        'page': ServicesPage.load(),
        'services': Service.objects.filter(is_active=True),
    })


def service_detail(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    other = Service.objects.filter(is_active=True).exclude(pk=service.pk)[:4]
    return render(request, 'content/service_detail.html', {
        'service': service,
        'other_services': other,
        'page_title': service.seo_title or service.title,
        'page_description': service.seo_description or service.short_desc[:160],
        'breadcrumb_items': trail(
            ('Послуги', safe_reverse('content:services')),
            (service.title, None),
        ),
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
