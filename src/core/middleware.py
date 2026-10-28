from django.conf import settings


def _admin_prefix():
    raw = str(getattr(settings, 'ADMIN_URL', '') or '').strip('/')
    if not raw:
        return ''
    return '/' + raw


def is_admin_path(path):
    prefix = _admin_prefix()
    if not prefix or prefix == '/':
        return False
    clean = path or '/'
    return clean == prefix or clean.startswith(prefix + '/')


class AdminRobotsMiddleware:
    """Закриває префікс ADMIN_URL від індексації, не друкуючи його в robots.txt."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if is_admin_path(request.path):
            response['X-Robots-Tag'] = 'noindex, nofollow'
        return response
