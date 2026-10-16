from django.shortcuts import render

from src.blog.selectors import get_published_posts
from src.content.models import (
    AdvantageItem,
    AdvantagesPage,
    ContactsPage,
    CookiePage,
    FaqItem,
    FaqPage,
    OfferPage,
    PrivacyPage,
    ReviewsPage,
    Service,
    ServicesPage,
)
from src.content.service_blocks import SERVICE_BLOCKS
from src.core.crypto_visibility import mentions_crypto, visible_queryset
from src.network.models import Branch
from src.reviews.selectors import get_published_reviews


def _shared_blocks():
    faq_page = FaqPage.load()
    reviews_page = ReviewsPage.load()
    return {
        'faq_page': faq_page,
        'faq_items': visible_queryset(
            FaqItem.objects.filter(is_active=True),
            'question', 'answer',
        )[:8],
        'home_reviews': get_published_reviews(8),
        'reviews_page': reviews_page,
    }


def services_list(request):
    page = ServicesPage.load()
    services = []
    for svc in visible_queryset(
        Service.objects.filter(is_active=True),
        'title', 'slug', 'short_desc', 'body', 'seo_title', 'seo_description',
    ):
        block = SERVICE_BLOCKS.get(svc.slug, {})
        svc.block_text = block.get('text') or svc.short_desc
        svc.block_points = list(block.get('points', ()))
        svc.block_cta = block.get('cta', 'Забронювати заявку')
        blob = ' '.join([svc.block_text, svc.block_cta, *svc.block_points])
        if mentions_crypto(blob):
            continue
        services.append(svc)
    ctx = {
        'page': page,
        'services': services,
        'news_posts': list(get_published_posts()[:10]),
        'page_title': page.seo_title or page.title,
        'page_description': page.seo_description or page.hero_text[:160],
    }
    ctx.update(_shared_blocks())
    return render(request, 'content/services_list.html', ctx)


def advantages_page(request):
    page = AdvantagesPage.load()
    ctx = {
        'page': page,
        'items': visible_queryset(
            AdvantageItem.objects.filter(is_active=True),
            'text', 'description',
        ),
        'audiences': AdvantageItem.Audience.choices,
        'page_title': page.seo_title or page.title,
        'page_description': page.seo_description or page.hero_lead[:160],
    }
    ctx.update(_shared_blocks())
    return render(request, 'content/advantages.html', ctx)


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
    page = ContactsPage.load()
    return render(request, 'content/contacts.html', {
        'page': page,
        'map_branches': map_branches,
        'active_branch': active,
        'branches': request.city_branches,
        'page_title': page.seo_title or page.title,
        'page_description': page.seo_description or page.heading,
    })


def _split_title(title):
    text = (title or '').strip()
    if ' ' not in text:
        return text, ''
    head, accent = text.rsplit(' ', 1)
    return head, accent


def _legal_page(request, page, current, qa):
    head, accent = _split_title(page.title)
    body = page.body or ''
    lead = body.split('\n\n', 1)[0].replace('\n', ' ').strip()
    return render(request, 'content/legal.html', {
        'page': page,
        'legal_current': current,
        'title_head': head,
        'title_accent': accent,
        'legal_qa': qa,
        'page_title': page.seo_title or page.title,
        'page_description': page.seo_description or lead[:160],
    })


def privacy_page(request):
    return _legal_page(request, PrivacyPage.load(), 'privacy', 'privacy-page')


def offer_page(request):
    return _legal_page(request, OfferPage.load(), 'offer', 'offer-page')


def cookies_page(request):
    return _legal_page(request, CookiePage.load(), 'cookies', 'cookies-page')


def faq_page(request):
    page = FaqPage.load()
    ctx = {
        'page': page,
        'page_title': page.seo_title or page.title,
        'page_description': page.seo_description or page.lead or page.title,
    }
    ctx.update(_shared_blocks())
    ctx['faq_items'] = visible_queryset(
        FaqItem.objects.filter(is_active=True),
        'question', 'answer',
    )
    return render(request, 'content/faq.html', ctx)
