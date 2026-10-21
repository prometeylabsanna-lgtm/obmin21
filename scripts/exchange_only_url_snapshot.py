#!/usr/bin/env python3
"""Знімок кодів відповіді публічних адрес. База db.sqlite3 лише для читання."""

import os
import sys
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]

SECTION_NAMES = (
    'core:home',
    'rates:rates_page',
    'content:services',
    'content:advantages',
    'content:faq',
    'blog:post_list',
    'reviews:review_list',
    'content:contacts',
    'network:city_list',
)

LEGAL_NAMES = (
    'content:privacy',
    'content:offer',
    'content:cookies',
)


def _bootstrap():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.develop')
    import django
    from django.conf import settings

    _force_readonly_sqlite(settings)
    django.setup()


def _force_readonly_sqlite(settings):
    db = settings.DATABASES['default']
    if db.get('ENGINE') != 'django.db.backends.sqlite3':
        raise SystemExit('Очікується локальна SQLite (db.sqlite3).')
    path = Path(db['NAME'])
    if not path.is_file():
        raise SystemExit(f'База не знайдена: {path}')
    quoted = quote(path.resolve().as_posix(), safe='/')
    db['NAME'] = f'file://{quoted}?mode=ro'
    options = dict(db.get('OPTIONS') or {})
    options['uri'] = True
    db['OPTIONS'] = options


def _http_host():
    from django.conf import settings
    from django.http.request import validate_host

    allowed = [str(host).strip() for host in settings.ALLOWED_HOSTS if str(host).strip()]
    candidates = []
    for host in allowed:
        if host == '*':
            candidates.append('localhost')
        elif host.startswith('.'):
            candidates.append(f'www{host}')
        else:
            candidates.append(host)
    if not candidates:
        candidates.append('localhost')
    for host in candidates:
        if validate_host(host, allowed or ['localhost']):
            return host
    raise SystemExit('ALLOWED_HOSTS не містить хоста для тестового клієнта.')


def _unique(paths):
    seen = set()
    ordered = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return ordered


def collect_paths():
    from django.urls import reverse

    from src.blog.models import Category, Post
    from src.network.models import City
    from src.rates.models import CurrencyPair, RateBoard

    paths = [reverse(name) for name in SECTION_NAMES]
    cities = City.objects.exclude(slug='').order_by('slug')
    paths.extend(
        reverse('network:city_detail', kwargs={'slug': city.slug})
        for city in cities
    )
    paths.extend(reverse(name) for name in LEGAL_NAMES)
    pairs = CurrencyPair.objects.exclude(slug='').order_by('slug')
    paths.extend(
        reverse('rates:pair_detail', kwargs={'slug': pair.slug})
        for pair in pairs
    )
    posts = Post.objects.exclude(slug='').order_by('slug')
    paths.extend(
        reverse('blog:post_detail', kwargs={'slug': post.slug})
        for post in posts
    )
    categories = Category.objects.exclude(slug='').order_by('slug')
    paths.extend(
        reverse('blog:category', kwargs={'category_slug': category.slug})
        for category in categories
    )
    paths.append(reverse('core:sitemap'))
    paths.append(reverse('core:robots'))
    rates_partial = reverse('core:rates_partial')
    for board in RateBoard.values:
        paths.append(f'{rates_partial}?board={board}')
    paths.append(reverse('core:quotes_json'))
    return _unique(paths)


def snapshot(out_path):
    from django.test import Client

    client = Client(HTTP_HOST=_http_host(), raise_request_exception=False)
    lines = []
    for path in collect_paths():
        response = client.get(path)
        lines.append(f'{response.status_code} {path}')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return len(lines)


def main(argv):
    if len(argv) != 2 or not argv[1].strip():
        sys.stderr.write(
            'Використання: .venv/bin/python scripts/exchange_only_url_snapshot.py <out.txt>\n',
        )
        return 2
    _bootstrap()
    count = snapshot(Path(argv[1]))
    sys.stdout.write(f'{count}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
