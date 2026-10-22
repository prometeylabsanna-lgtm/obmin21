from django.shortcuts import render
from django.urls import Resolver404, resolve

from src.core.breadcrumbs import safe_reverse
from src.core.exchange_mode import hidden_page_status, is_exchange_only

_SKIP_PREFIXES = ('/admin', '/tinymce', '/static', '/media')
_SERVICE_URL_NAMES = (
    'content:service_detail',
    'content:service',
    'content:service_page',
)
_DEFAULT_RETRY_AFTER = 86400


def retry_after_header_value():
    from src.core.models import SiteSettings

    stored = SiteSettings.objects.filter(pk=1).values_list(
        'retry_after_seconds', flat=True,
    ).first()
    if isinstance(stored, int) and stored > 0:
        return stored
    return _DEFAULT_RETRY_AFTER


def service_public_path(slug):
    if not slug:
        return ''
    for name in _SERVICE_URL_NAMES:
        path = safe_reverse(name, slug=slug)
        if path:
            return path
    return ''


def match_key(match):
    if match.namespace and match.url_name:
        return f'{match.namespace}:{match.url_name}'
    return match.url_name or ''


def is_service_detail(match):
    if match_key(match) in _SERVICE_URL_NAMES:
        return True
    route = match.route or ''
    if match.url_name == 'services':
        return False
    return 'slug' in match.kwargs and route.startswith('posluhy/')


def is_hidden_match(match):
    key = match_key(match)
    if key == 'blog:post_detail':
        return _post_is_hidden(match.kwargs.get('slug') or '')
    if key == 'blog:category':
        return _category_is_hidden(match.kwargs.get('category_slug') or '')
    if key == 'rates:pair_detail':
        return _pair_is_hidden(match.kwargs.get('slug') or '')
    if is_service_detail(match):
        return _service_is_hidden(match.kwargs.get('slug') or '')
    return False


def is_hidden_path(path, request=None):
    if not is_exchange_only(request):
        return False
    clean = (path or '').split('?', 1)[0]
    if not clean.startswith('/') or clean.startswith(_SKIP_PREFIXES):
        return False
    cache = None
    if request is not None:
        cache = getattr(request, '_hidden_path_cache', None)
        if cache is None:
            cache = {}
            request._hidden_path_cache = cache
        if clean in cache:
            return cache[clean]
    try:
        match = resolve(clean)
    except Resolver404:
        hidden = False
    else:
        hidden = is_hidden_match(match)
    if cache is not None:
        cache[clean] = hidden
    return hidden


def is_hidden_request(request):
    if not is_exchange_only(request):
        return False
    path = request.path_info or '/'
    if path.startswith(_SKIP_PREFIXES):
        return False
    return is_hidden_path(path, request)


def hidden_page_response(request):
    status = hidden_page_status(request)
    response = render(request, 'core/hidden_page.html', status=status)
    if status == 503:
        response['Retry-After'] = str(retry_after_header_value())
    return response


class HiddenPageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if is_hidden_request(request):
            return hidden_page_response(request)
        return self.get_response(request)


def _post_is_hidden(slug):
    from src.blog.models import Post

    if not slug:
        return False
    post = Post.objects.filter(
        slug=slug,
        status=Post.Status.PUBLISHED,
    ).only('id', 'exchange_safe').first()
    if post is None:
        return False
    return not post.exchange_safe


def _category_is_hidden(slug):
    from src.blog.models import Category
    from src.blog.selectors import get_published_posts

    if not slug:
        return False
    category = Category.objects.filter(slug=slug).only('id').first()
    if category is None:
        return False
    visible = (
        get_published_posts()
        .visible()
        .filter(category=category)
        .exclude(slug='')
    )
    return not visible.exists()


def _pair_is_hidden(slug):
    from src.rates.models import CurrencyPair

    if not slug:
        return False
    active = CurrencyPair.objects.filter(slug=slug, is_active=True)
    if not active.exists():
        return False
    return not active.visible().exists()


def _service_is_hidden(slug):
    from src.content.models import Service
    from src.core.seo_words import contains_stop_word

    if not slug:
        return False
    service = Service.objects.filter(slug=slug, is_active=True).only(
        'id', 'exchange_safe', 'title', 'slug', 'seo_title', 'seo_description',
    ).first()
    if service is None:
        return False
    if not service.exchange_safe:
        return True
    blob = ' '.join(
        part for part in (
            service.title,
            service.slug,
            service.seo_title,
            service.seo_description,
        ) if part
    )
    return contains_stop_word(blob)
