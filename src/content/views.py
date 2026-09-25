from django.shortcuts import render

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
from src.leads.forms import ContactMessageForm


def services_list(request):
    page = ServicesPage.load()
    return render(request, 'content/services_list.html', {
        'page': page,
        'services': Service.objects.filter(is_active=True),
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
