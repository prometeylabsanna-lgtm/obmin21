from __future__ import annotations

from django.core.cache import cache

from src.core.colors import ACCENT_HOVER_DEFAULT, ACCENT_RGB_DEFAULT

THEME_CSS_CACHE_KEY = 'theme_css_v1'
THEME_VERSION_KEY = 'theme_css_version'

URL_THEME_MAP = {
    'core:home': 'home',
    'rates:rates_page': 'rates',
    'rates:pair_detail': 'rates',
    'content:contacts': 'contacts',
    'content:services': 'services',
    'content:advantages': 'advantages',
    'content:faq': 'faq',
    'content:privacy': 'privacy',
    'content:offer': 'offer',
    'content:cookies': 'cookies',
    'blog:post_list': 'blog',
    'blog:category': 'blog',
    'blog:post_detail': 'blog',
    'reviews:review_list': 'reviews',
    'network:city_list': 'cities',
    'network:city_detail': 'cities',
}


def bump_theme_cache() -> None:
    from time import time

    cache.delete(THEME_CSS_CACHE_KEY)
    cache.set(THEME_VERSION_KEY, int(time()), None)


def theme_version() -> int:
    return int(cache.get(THEME_VERSION_KEY) or 0)


def _hover_from_accent(accent: str) -> tuple[str, str]:
    raw = (accent or '').strip()
    if len(raw) != 7 or not raw.startswith('#'):
        return ACCENT_HOVER_DEFAULT, ACCENT_RGB_DEFAULT
    r = int(raw[1:3], 16)
    g = int(raw[3:5], 16)
    b = int(raw[5:7], 16)
    hover = f'#{int(r * 0.82):02x}{int(g * 0.82):02x}{int(b * 0.82):02x}'
    return hover, f'{r}, {g}, {b}'


def _rule(slug: str, bg: str, text: str, accent: str) -> str:
    hover, rgb = _hover_from_accent(accent)
    return (
        f'[data-theme="{slug}"] {{\n'
        f'  --color-bg: {bg};\n'
        f'  --color-text: {text};\n'
        f'  --color-heading: {text};\n'
        f'  --color-navy: {text};\n'
        f'  --color-accent: {accent};\n'
        f'  --color-accent-hover: {hover};\n'
        f'  --color-accent-rgb: {rgb};\n'
        f'  --color-accent-soft: rgba({rgb}, 0.14);\n'
        f'}}\n'
    )


def build_theme_css() -> str:
    from src.content.models import (
        AdvantagesPage,
        BlogPage,
        CitiesPage,
        ContactsPage,
        CookiePage,
        FaqPage,
        HomePage,
        OfferPage,
        PrivacyPage,
        RatesPage,
        ReviewsPage,
        ServicesPage,
    )
    from src.core.models import SiteSettings

    settings = SiteSettings.load()
    parts = [
        _rule(
            'header',
            settings.header_color_bg,
            settings.header_color_text,
            settings.header_color_accent,
        ),
        _rule(
            'footer',
            settings.footer_color_bg,
            settings.footer_color_text,
            settings.footer_color_accent,
        ),
    ]
    pages = (
        HomePage,
        RatesPage,
        ContactsPage,
        ServicesPage,
        AdvantagesPage,
        BlogPage,
        ReviewsPage,
        CitiesPage,
        FaqPage,
        PrivacyPage,
        OfferPage,
        CookiePage,
    )
    for model in pages:
        obj = model.load()
        parts.append(_rule(obj.theme_slug, obj.color_bg, obj.color_text, obj.color_accent))
    return ''.join(parts)


def theme_css_cached() -> str:
    css = cache.get(THEME_CSS_CACHE_KEY)
    if css is None:
        css = build_theme_css()
        cache.set(THEME_CSS_CACHE_KEY, css, 3600)
    return css
