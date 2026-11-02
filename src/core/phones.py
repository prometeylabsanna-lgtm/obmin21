import re
from contextvars import ContextVar
from urllib.parse import urlparse

_MIN_TEL_DIGITS = 7
_phone_request = ContextVar('obmin_site_phone_request', default=None)
_TME_HOSTS = frozenset({'t.me', 'telegram.me'})
_TME_NICK = re.compile(r'[A-Za-z0-9_]{1,64}')


def phone_digits(phone):
    return re.sub(r'\D+', '', phone or '')


def phone_tel(phone):
    digits = phone_digits(phone)
    if len(digits) < _MIN_TEL_DIGITS:
        return ''
    if digits.startswith('380'):
        return f'+{digits}'
    if digits.startswith('0') and len(digits) == 10:
        return f'+38{digits}'
    if digits.startswith('38'):
        return f'+{digits}'
    return f'+{digits}'


def push_phone_request(request):
    return _phone_request.set(request)


def pop_phone_request(token):
    _phone_request.reset(token)


def bound_phone_request():
    return _phone_request.get()


def _text(value):
    return str(value or '').strip()


def resolve_site_phone(request, settings):
    """Телефон вибраного відділення, інакше міста, інакше загальний."""
    if request is None:
        request = _phone_request.get()
    display = ''
    branch = getattr(request, 'active_branch', None) if request is not None else None
    if branch is not None:
        display = _text(getattr(branch, 'phone', ''))
    if not display and request is not None:
        city = getattr(request, 'city', None)
        if city is not None:
            display = _text(getattr(city, 'phone', ''))
    if not display and settings is not None:
        display = _text(getattr(settings, 'default_phone', ''))
    return display, phone_tel(display)


def resolve_branch_phone(request, settings, branch=None):
    """Те саме джерело, що resolve_site_phone."""
    return resolve_site_phone(request, settings)


def safe_telegram_url(value):
    """https://t.me/<нік> або https://telegram.me/<нік>. Інакше порожній рядок."""
    raw = str(value or '').strip()
    if not raw or re.search(r'\s', raw):
        return ''
    parsed = urlparse(raw)
    host = (parsed.hostname or '').lower()
    if parsed.scheme.lower() != 'https' or host not in _TME_HOSTS:
        return ''
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        return ''
    segments = [part for part in (parsed.path or '').split('/') if part]
    if not segments or not all(_TME_NICK.fullmatch(part) for part in segments):
        return ''
    return raw
