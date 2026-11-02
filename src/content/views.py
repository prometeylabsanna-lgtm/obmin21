from types import SimpleNamespace

from django.shortcuts import render

from src.blog.selectors import get_published_posts
from src.content.faq_defaults import public_faq_items
from src.content.models import (
    AdvantageItem,
    AdvantagesPage,
    ContactsPage,
    CookiePage,
    FaqItem,
    FaqPage,
    HomePage,
    OfferPage,
    PrivacyPage,
    ReviewsPage,
    Service,
    ServicesPage,
)
from src.content.service_blocks import SERVICE_BLOCKS
from src.core.exchange_mode import mode_meta, mode_text
from src.network.models import Branch
from src.reviews.selectors import get_published_reviews


def _service_block_text(svc, block, request):
    source = SimpleNamespace(
        text=block.get('text') or '',
        short_desc=svc.short_desc or '',
        short_desc_mode=getattr(svc, 'short_desc_mode', ''),
    )
    return mode_meta(source, 'text', 'short_desc', limit=None, request=request)


def _first_paragraph(body):
    text = body or ''
    return text.split('\n\n', 1)[0].replace('\n', ' ').strip()


def _legal_description(page, request):
    source = SimpleNamespace(
        seo_description=page.seo_description,
        seo_description_mode=getattr(page, 'seo_description_mode', ''),
        lead=_first_paragraph(page.body),
        lead_mode=_first_paragraph(mode_text(page, 'body', request)),
    )
    return mode_meta(source, 'seo_description', 'lead', request=request)


def _shared_blocks():
    faq_page = FaqPage.load()
    reviews_page = ReviewsPage.load()
    return {
        'faq_page': faq_page,
        'faq_items': FaqItem.objects.filter(is_active=True).visible()[:8],
        'home_reviews': get_published_reviews(8),
        'reviews_page': reviews_page,
    }


def services_list(request):
    page = ServicesPage.load()
    services = []
    for svc in Service.objects.filter(is_active=True).visible():
        block = SERVICE_BLOCKS.get(svc.slug, {})
        svc.block_text = _service_block_text(svc, block, request)
        svc.block_points = list(block.get('points', ()))
        svc.block_cta = block.get('cta', 'Забронювати заявку')
        for name in ('block_text_mode', 'block_points_mode', 'block_cta_mode'):
            setattr(svc, name, getattr(svc, name, ''))
        services.append(svc)
    ctx = {
        'page': page,
        'services': services,
        'home_page': HomePage.load(),
        'news_posts': list(get_published_posts()[:10]),
        'page_title': mode_meta(page, 'seo_title', 'title', limit=None, request=request),
        'page_description': mode_meta(page, 'seo_description', 'hero_text', request=request),
    }
    ctx.update(_shared_blocks())
    return render(request, 'content/services_list.html', ctx)


def advantages_page(request):
    page = AdvantagesPage.load()
    ctx = {
        'page': page,
        'items': AdvantageItem.objects.filter(is_active=True).visible(),
        'audiences': AdvantageItem.Audience.choices,
        'page_title': mode_meta(page, 'seo_title', 'title', limit=None, request=request),
        'page_description': mode_meta(page, 'seo_description', 'hero_lead', request=request),
    }
    ctx.update(_shared_blocks())
    return render(request, 'content/advantages.html', ctx)


def contacts_page(request):
    map_branches = list(
        Branch.objects.filter(is_active=True, city__is_active=True)
        .select_related('city')
        .order_by('city__sort_order', 'sort_order', 'id')
    )
    active = getattr(request, 'active_branch', None)
    if active is None or active.pk not in {item.pk for item in map_branches}:
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
        'page_title': mode_meta(page, 'seo_title', 'title', limit=None, request=request),
        'page_description': mode_meta(
            page, 'seo_description', 'heading', limit=None, request=request,
        ),
    })


def _split_title(title):
    text = (title or '').strip()
    if ' ' not in text:
        return text, ''
    head, accent = text.rsplit(' ', 1)
    return head, accent


def _legal_page(request, page, current, qa):
    head, accent = _split_title(page.title)
    return render(request, 'content/legal.html', {
        'page': page,
        'legal_current': current,
        'title_head': head,
        'title_accent': accent,
        'legal_qa': qa,
        'page_title': mode_meta(page, 'seo_title', 'title', limit=None, request=request),
        'page_description': _legal_description(page, request),
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
        'page_title': mode_meta(page, 'seo_title', 'title', limit=None, request=request),
        'page_description': mode_meta(
            page, 'seo_description', 'lead', 'title', limit=None, request=request,
        ),
    }
    ctx.update(_shared_blocks())
    ctx['faq_items'] = public_faq_items()
    return render(request, 'content/faq.html', ctx)
