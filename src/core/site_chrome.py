"""Дані шапки/підвалу/іконок для шаблонів (context processor site_chrome)."""

from __future__ import annotations

from django.templatetags.static import static
from django.urls import reverse

DEFAULT_CTA_LABEL = 'Зробити заявку'
ICON_VERSION = '10'


def _file_url(field):
    if not field or not getattr(field, 'name', ''):
        return ''
    try:
        if not field.storage.exists(field.name):
            return ''
        return field.url
    except (OSError, ValueError):
        return ''


def _current(request, href):
    path = getattr(request, 'path', '') or ''
    if not href or not href.startswith('/'):
        return False
    if href == '/':
        return path == '/'
    return path.startswith(href)


def header_menu(request):
    from src.core.models import HeaderMenuItem

    items = []
    for item in HeaderMenuItem.objects.filter(is_active=True):
        href = item.href
        if not href:
            continue
        items.append({
            'label': item.label,
            'href': href,
            'new_tab': item.open_new_tab,
            'show_desktop': item.show_desktop,
            'show_mobile': item.show_mobile,
            'is_current': _current(request, href),
            'page': item.page,
        })
    return items


def header_cta(settings):
    return {
        'enabled': bool(settings.header_cta_enabled),
        'label': (settings.header_cta_label or '').strip() or DEFAULT_CTA_LABEL,
        'modal_url': reverse('leads:contact_modal'),
    }


def footer_columns(request, services=()):
    from src.core.exchange_mode import shows_in_exchange_mode
    from src.core.models import FooterColumn

    columns = []
    for col in FooterColumn.objects.filter(is_active=True).prefetch_related('links'):
        links = []
        if col.kind == FooterColumn.Kind.SERVICES:
            services_url = reverse('content:services')
            for svc in services:
                if not shows_in_exchange_mode(svc):
                    continue
                links.append({
                    'label': svc.title,
                    'href': f'{services_url}#svc-{svc.slug}',
                    'new_tab': False,
                })
        else:
            for link in col.links.all():
                if not link.is_active or not link.href:
                    continue
                links.append({'label': link.label, 'href': link.href, 'new_tab': link.open_new_tab})
        if links:
            columns.append({'title': col.title, 'kind': col.kind, 'links': links})
    return columns


def site_icons(settings):
    fav = _file_url(settings.favicon)
    png = _file_url(settings.favicon_png)
    apple = _file_url(settings.apple_touch_icon)
    v = f'?v={ICON_VERSION}'
    return {
        'favicon': fav or static('images/favicon.ico') + v,
        'favicon_32': png or static('images/favicon-32x32.png') + v,
        'favicon_48': png or static('images/favicon-48x48.png') + v,
        'apple_touch': apple or static('images/apple-touch-icon.png') + v,
        'manifest_url': reverse('core:webmanifest'),
        'theme_color': settings.theme_color or '#052145',
    }


def manifest_payload(settings):
    app = _file_url(settings.app_icon)
    if app:
        icons = [{'src': app, 'sizes': '512x512', 'type': 'image/png'}]
    else:
        icons = [
            {'src': static('images/icon-192.png'), 'sizes': '192x192', 'type': 'image/png'},
            {'src': static('images/icon-512.png'), 'sizes': '512x512', 'type': 'image/png'},
        ]
    return {
        'name': settings.manifest_name or settings.site_name or 'Обмін21',
        'short_name': settings.manifest_short_name or settings.manifest_name or 'Обмін21',
        'icons': icons,
        'theme_color': settings.theme_color or '#052145',
        'background_color': settings.manifest_background_color or '#ffffff',
        'display': 'standalone',
    }
