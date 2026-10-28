import json

from django.conf import settings
from django.db.models import Avg, Count
from django.templatetags.static import static
from django.utils.safestring import mark_safe

from src.core.exchange_mode import NEUTRAL_DESCRIPTION, is_exchange_only, mode_meta
from src.core.exchange_stopwords import matches_stop_words
from src.core.seo_words import contains_stop_word, strip_stop_words

OG_IMAGE = 'images/og-obmin21.webp'
OG_WIDTH = 1200
OG_HEIGHT = 630
LOGO_IMAGE = 'images/logo.webp'
FALLBACK_DESCRIPTION = 'Обмін готівкової валюти у відділеннях Обмін21.'
SITEMAP_PATH = '/sitemap.xml'

_ROBOTS_DISALLOW = (
    '/admin/',
    '/partials/',
    '/tinymce/',
    '/htmx/',
    '/telegram/',
    '/*/obraty/',
    '/*?*sort=',
    '/*?*utm_',
    '/*?*utm=',
    '/*?*fbclid=',
    '/*?*gclid=',
    '/*?*yclid=',
    '/*?*gbraid=',
    '/*?*wbraid=',
    '/*?*board=',
    '/*?*limit=',
    '/*?*home=',
    '/*?*hide_full=',
    '/*?*city=',
    '/*?*direct=',
    '/*?*ref=',
    '/*?*_openstat=',
)

_LLMS_SECTIONS = (
    ('Головна', '/'),
    ('Курси валют', '/kursy/'),
    ('Послуги', '/posluhy/'),
    ('Переваги', '/perevahy/'),
    ('Блог', '/blog/'),
    ('Відгуки', '/vidhuky/'),
    ('Контакти', '/kontakty/'),
    ('Міста', '/mista/'),
    ('Питання та відповіді', '/faq/'),
    ('Політика конфіденційності', '/polityka-konfidentsiynosti/'),
    ('Публічна оферта', '/publichna-oferta/'),
    ('Політика cookie', '/polityka-cookie/'),
)

_LLMS_RULES = (
    'Мова сайту українська. Окремої російської версії немає.',
    'Не вигадуй курс, наявність готівки, адресу відділення чи телефон. Бери їх лише з відкритих сторінок.',
    'Канонічна адреса сторінки без параметрів запиту: sort, utm, board, limit, fbclid, gclid.',
    'Не цитуй службові адреси форм, фрагментів сторінки і вебхуків.',
    'Не шукай і не публікуй адресу панелі керування сайтом.',
    'Оцінку став лише з опублікованих відгуків, які видно на сайті.',
    'Не додавай послуги, яких немає на відкритих сторінках.',
)

_FULL_EXTRA = (
    'Окрім готівкового обміну, на сайті є сторінки про криптовалюту, '
    'інвестиційне золото, грошові перекази та SWIFT.'
)


def site_origin():
    raw = str(getattr(settings, 'SITE_URL', '') or '').strip().rstrip('/')
    if raw.startswith('https://') and ' ' not in raw:
        return raw
    return 'https://obmin21.com'


def absolute_url(path):
    raw = str(path or '').strip()
    if not raw:
        return site_origin() + '/'
    raw = raw.split('#', 1)[0].split('?', 1)[0]
    if raw.startswith('https://') or raw.startswith('http://'):
        return raw
    if not raw.startswith('/'):
        raw = '/' + raw
    return site_origin() + raw


def canonical_url(request):
    path = getattr(request, 'path', '') or '/'
    if not path.startswith('/'):
        path = '/' + path
    return site_origin() + path


def robots_body():
    lines = ['User-agent: *', 'Allow: /', '']
    lines.extend(f'Disallow: {rule}' for rule in _ROBOTS_DISALLOW)
    lines.append('')
    lines.append(f'Sitemap: {site_origin()}{SITEMAP_PATH}')
    return '\n'.join(lines) + '\n'


def _dirty(text):
    return contains_stop_word(text) or matches_stop_words(text)


def _exchange_clean(text):
    cleaned = strip_stop_words(text)
    if not _dirty(cleaned):
        return cleaned
    kept = [line for line in cleaned.splitlines() if line.strip() and not _dirty(line)]
    result = '\n'.join(kept).strip()
    if not result or _dirty(result):
        return ''
    return result


def llms_body(request):
    origin = site_origin()
    exchange = is_exchange_only(request)
    intro = (
        'Обмін21 — мережа обміну готівкової валюти у відділеннях в Україні. '
        'На сайті курс долара, євро та польської валюти, контакти відділень '
        'і фіксація курсу онлайн.'
    )
    lines = ['# Обмін21', '', intro, '', '## Розділи']
    for title, path in _LLMS_SECTIONS:
        lines.append(f'- {title}: {origin}{path}')
    if not exchange:
        lines.extend(['', '## Інші послуги', _FULL_EXTRA])
    lines.extend(['', '## Правила для ШІ'])
    lines.extend(f'- {rule}' for rule in _LLMS_RULES)
    if exchange:
        lines.append(
            '- Зараз на сайті відкрито лише готівковий обмін валюти у відділеннях.'
        )
    text = '\n'.join(lines).strip() + '\n'
    if not exchange:
        return text
    cleaned = _exchange_clean(text)
    return (cleaned or _exchange_fallback(origin)).rstrip() + '\n'


def _exchange_fallback(origin):
    lines = [
        '# Обмін21',
        '',
        FALLBACK_DESCRIPTION,
        '',
        '## Розділи',
    ]
    for title, path in _LLMS_SECTIONS:
        lines.append(f'- {title}: {origin}{path}')
    lines.extend(['', '## Правила для ШІ'])
    lines.extend(f'- {rule}' for rule in _LLMS_RULES)
    lines.append('- Зараз на сайті відкрито лише готівковий обмін валюти у відділеннях.')
    return '\n'.join(lines)


def _one_line(text):
    return ' '.join(str(text or '').split())


def _site_name(context):
    site = context.get('site_settings') if context else None
    name = getattr(site, 'site_name', '') if site is not None else ''
    if name:
        return name
    from src.core.models import SiteSettings

    return SiteSettings.load().site_name or 'Обмін21'


def _plain_title(context, request):
    page_title = _one_line(context.get('page_title'))
    if not page_title:
        page = context.get('page')
        if page is not None:
            page_title = _one_line(mode_meta(
                page, 'seo_title', 'title', limit=None, request=request,
            ))
    if is_exchange_only(request):
        if page_title == NEUTRAL_DESCRIPTION:
            return ''
        page_title = _exchange_clean(page_title)
    return page_title


def _description(context, request):
    text = _one_line(context.get('page_description'))
    if (
        is_exchange_only(request)
        and text
        and text != NEUTRAL_DESCRIPTION
    ):
        text = _exchange_clean(text)
    return text or FALLBACK_DESCRIPTION


def _public_title(context, request):
    site_name = _site_name(context)
    page_title = _plain_title(context, request)
    if page_title and page_title != site_name:
        return f'{page_title} · {site_name}'
    return site_name


def _json(data):
    raw = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    return raw.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')


def _logo_url():
    return absolute_url(static(LOGO_IMAGE))


def _og_image_url():
    return absolute_url(static(OG_IMAGE))


def _visible_rating():
    from src.reviews.models import Review

    stats = (
        Review.objects.visible()
        .filter(is_published=True)
        .aggregate(avg=Avg('rating'), total=Count('id'))
    )
    total = stats['total'] or 0
    if not total or stats['avg'] is None:
        return None
    return {
        '@type': 'AggregateRating',
        'ratingValue': round(float(stats['avg']), 1),
        'reviewCount': total,
        'bestRating': 5,
        'worstRating': 1,
    }


def _same_as(site, request):
    found = []
    if site is None:
        return found
    exchange = is_exchange_only(request)
    for field in ('telegram_url', 'youtube_url', 'instagram_url', 'facebook_url'):
        value = str(getattr(site, field, '') or '').strip()
        if not value.startswith(('https://', 'http://')):
            continue
        value = value.split('#', 1)[0].split('?', 1)[0]
        if exchange and _dirty(value):
            continue
        found.append(value)
    return found


def _breadcrumb_node(items, request, canonical):
    if not items:
        return None
    elements = []
    exchange = is_exchange_only(request)
    for item in items:
        name = _one_line(item.get('title'))
        if exchange:
            name = _exchange_clean(name)
        if not name:
            continue
        element = {
            '@type': 'ListItem',
            'position': len(elements) + 1,
            'name': name,
        }
        url = item.get('url')
        element['item'] = absolute_url(url) if url else canonical
        elements.append(element)
    if not elements:
        return None
    return {
        '@type': 'BreadcrumbList',
        '@id': canonical + '#breadcrumbs',
        'itemListElement': elements,
    }


def _article_image(post, request):
    raw = post.image_url() if callable(getattr(post, 'image_url', None)) else ''
    if not raw:
        return ''
    url = absolute_url(raw)
    if is_exchange_only(request) and _dirty(url):
        return ''
    return url


def _article_node(context, request, canonical, site_name):
    match = getattr(request, 'resolver_match', None)
    if match is None or match.namespace != 'blog' or match.url_name != 'post_detail':
        return None
    post = context.get('post')
    if post is None:
        return None
    headline = _plain_title(context, request) or site_name
    node = {
        '@type': 'Article',
        'headline': headline,
        'mainEntityOfPage': canonical,
        'image': _article_image(post, request) or _og_image_url(),
        'author': {'@type': 'Organization', 'name': site_name},
        'publisher': {
            '@type': 'Organization',
            'name': site_name,
            'logo': {'@type': 'ImageObject', 'url': _logo_url()},
        },
    }
    published = getattr(post, 'published_at', None)
    if published is not None:
        node['datePublished'] = published.isoformat()
    updated = getattr(post, 'updated_at', None)
    if updated is not None:
        node['dateModified'] = updated.isoformat()
    return node


def _graph(context, request, canonical, site_name, description):
    origin = site_origin()
    org_id = origin + '/#organization'
    business_id = origin + '/#business'
    exchange = is_exchange_only(request)
    site = context.get('site_settings')
    organization = {
        '@type': 'Organization',
        '@id': org_id,
        'name': site_name,
        'url': origin + '/',
        'logo': _logo_url(),
    }
    business = {
        '@type': ['FinancialService', 'LocalBusiness'],
        '@id': business_id,
        'name': site_name,
        'url': origin + '/',
        'image': _og_image_url(),
        'description': description,
        'areaServed': 'UA',
        'parentOrganization': {'@id': org_id},
    }
    if not exchange:
        business['currenciesAccepted'] = 'UAH, USD, EUR, PLN'
    phone = _one_line(context.get('active_phone'))
    if phone and not (exchange and _dirty(phone)):
        business['telephone'] = phone
    same = _same_as(site, request)
    if same:
        organization['sameAs'] = same
        business['sameAs'] = same
    rating = _visible_rating()
    if rating is not None:
        business['aggregateRating'] = rating
    from src.core.seo_schema import branch_departments, faq_node

    departments = branch_departments(request)
    if departments:
        business['department'] = departments
    graph = [organization, business]
    crumbs = _breadcrumb_node(context.get('breadcrumb_items'), request, canonical)
    if crumbs is not None:
        graph.append(crumbs)
    article = _article_node(context, request, canonical, site_name)
    if article is not None:
        graph.append(article)
    faq = faq_node(request, canonical)
    if faq is not None:
        graph.append(faq)
    return {'@context': 'https://schema.org', '@graph': graph}


def build_head(request, context):
    context = context or {}
    site_name = _site_name(context)
    description = _description(context, request)
    title = _public_title(context, request)
    canonical = canonical_url(request)
    match = getattr(request, 'resolver_match', None)
    og_type = 'article' if (
        match is not None and match.namespace == 'blog' and match.url_name == 'post_detail'
    ) else 'website'
    robots_meta = 'noindex, follow' if getattr(request, 'GET', None) else ''
    payload = _graph(context, request, canonical, site_name, description)
    return {
        'site_name': site_name,
        'title': title,
        'description': description,
        'canonical': canonical,
        'og_type': og_type,
        'og_image': _og_image_url(),
        'og_width': OG_WIDTH,
        'og_height': OG_HEIGHT,
        'robots_meta': robots_meta,
        'json_ld': mark_safe(_json(payload)),
    }
