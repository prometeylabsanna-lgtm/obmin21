from __future__ import annotations

from django.contrib.staticfiles import finders
from django.templatetags.static import static

IMAGE_FALLBACKS = {
    'header_logo': 'images/logo.png',
    'footer_logo': 'images/logo-footer.png',
    'banner_exchange': 'images/coins.png',
    'banner_service': 'images/coins-a.png',
    'banner_cta': 'images/coins-b.png',
    'map_image': 'images/hero-kyiv.jpg',
}

CONTAIN_FIELDS = frozenset({'header_logo', 'footer_logo'})


def image_fallback_url(field_name: str, instance=None) -> str:
    if field_name == 'cover' and instance is not None:
        slug = getattr(instance, 'slug', '') or ''
        article = f'images/articles/{slug}.jpg'
        if slug and finders.find(article):
            return static(article)
        return static('images/service-1.png')
    path = IMAGE_FALLBACKS.get(field_name)
    return static(path) if path else ''


def image_preview_fit(field_name: str) -> str:
    return 'contain' if field_name in CONTAIN_FIELDS else 'cover'
