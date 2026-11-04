import re
from contextvars import ContextVar
from urllib.parse import urlparse

_MIN_TEL_DIGITS = 7
_phone_request = ContextVar('obmin_site_phone_request', default=None)
_TME_HOSTS = frozenset({'t.me', 'telegram.me'})
_TME_NICK = re.compile(r'[A-Za-z0-9_]{1,64}')

_UA_MOBILE = re.compile(r'^380\d{9}$')


def phone_digits(phone):
    return re.sub(r'\D+', '', phone or '')


def normalize_ua_phone(phone):
    """Нормалізує до +380XXXXXXXXX або '' якщо порожньо; None якщо формат невірний."""
    raw = (phone or '').strip()
    if not raw:
        return ''
    digits = phone_digits(raw)
    if digits.startswith('0') and len(digits) == 10:
        digits = '38' + digits
    if digits.startswith('38') and not digits.startswith('380'):
        return None
    if len(digits) == 9 and digits[0] in '345679':
        digits = '380' + digits
    if not _UA_MOBILE.match(digits):
        return None
    return f'+{digits}'


def is_ua_phone(phone):
    return normalize_ua_phone(phone) is not None and bool((phone or '').strip())


def phone_tel(phone):
    normalized = normalize_ua_phone(phone)
    if normalized:
        return normalized
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


FALLBACK_TELEGRAM_USERNAME = 'obmin21'
_CONTACTS_ATTR = '_obmin_contacts'


def telegram_display_from_url(url):
    raw = str(url or '').strip()
    if not raw:
        return ''
    parsed = urlparse(raw)
    segments = [part for part in (parsed.path or '').split('/') if part]
    if not segments:
        return ''
    name = segments[-1].strip().lstrip('@')
    if not name:
        return ''
    return f'@{name}'


def get_contacts(request, settings=None):
    """Контакти вибраного відділення. Один раз на запит.

    phone / phone_href — телефон відділення, якщо він є.
    Інакше загальний телефон SiteSettings.
    telegram — нік відділення; якщо поле порожнє, @obmin21.
    Без відділення Telegram береться із SiteSettings.
    source: branch, якщо телефон із відділення, інакше global.
    """
    if request is None:
        request = _phone_request.get()
    if request is not None:
        cached = getattr(request, _CONTACTS_ATTR, None)
        if cached is not None:
            return cached
    if settings is None:
        from src.core.models import SiteSettings

        settings = SiteSettings.load()
    branch = getattr(request, 'active_branch', None) if request is not None else None

    phone = ''
    source = 'global'
    if branch is not None and _text(getattr(branch, 'phone', '')):
        phone = _text(branch.phone)
        source = 'branch'
    elif settings is not None:
        phone = _text(getattr(settings, 'default_phone', ''))

    if branch is not None:
        username = _text(getattr(branch, 'telegram_username', '') or getattr(branch, 'telegram', ''))
        if username.startswith('@'):
            username = username[1:]
        if username:
            telegram_url = f'https://t.me/{username}'
            telegram_display = f'@{username}'
        else:
            telegram_url = f'https://t.me/{FALLBACK_TELEGRAM_USERNAME}'
            telegram_display = f'@{FALLBACK_TELEGRAM_USERNAME}'
    else:
        telegram_url = safe_telegram_url(getattr(settings, 'telegram_url', ''))
        telegram_display = telegram_display_from_url(telegram_url)

    data = {
        'phone': phone,
        'phone_href': phone_tel(phone),
        'telegram_url': telegram_url,
        'telegram_display': telegram_display,
        'source': source,
    }
    if request is not None:
        setattr(request, _CONTACTS_ATTR, data)
    return data


def resolve_site_phone(request, settings=None):
    """Телефон вибраного відділення, інакше загальний."""
    contacts = get_contacts(request, settings)
    return contacts['phone'], contacts['phone_href']


def resolve_branch_phone(request, settings=None, branch=None):
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
