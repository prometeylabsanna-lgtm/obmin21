from django.urls import NoReverseMatch, reverse


def crumb(title, url=None):
    return {'title': title, 'url': url}


def trail(*items):
    """Build breadcrumb list: home + items. Last item usually has url=None."""
    result = [crumb('Головна', reverse('core:home'))]
    for item in items:
        if isinstance(item, dict):
            result.append(item)
        else:
            title = item[0]
            url = item[1] if len(item) > 1 else None
            result.append(crumb(title, url))
    return result


def safe_reverse(name, **kwargs):
    try:
        return reverse(name, kwargs=kwargs) if kwargs else reverse(name)
    except NoReverseMatch:
        return None


STATIC_TRAILS = {
    'content:contacts': lambda: trail(('Контакти', None)),
    'content:services': lambda: trail(('Послуги', None)),
    'content:advantages': lambda: trail(('Переваги', None)),
    'content:privacy': lambda: trail(('Політика конфіденційності', None)),
    'content:faq': lambda: trail(('FAQ', None)),
    'blog:post_list': lambda: trail(('Блог', None)),
    'reviews:review_list': lambda: trail(('Відгуки', None)),
    'rates:rates_page': lambda: trail(('Курси', None)),
    'network:city_list': lambda: trail(('Міста', None)),
}


def breadcrumbs_for_request(request):
    match = getattr(request, 'resolver_match', None)
    if not match:
        return None
    key = f'{match.namespace}:{match.url_name}'
    if key == 'core:home':
        return None
    builder = STATIC_TRAILS.get(key)
    if builder:
        return builder()
    return []
