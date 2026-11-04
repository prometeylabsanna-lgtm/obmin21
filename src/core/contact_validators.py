import re
from urllib.parse import urlparse

from django.core.exceptions import ValidationError

from src.core.phones import is_ua_phone, normalize_ua_phone

_PHONE_MSG = 'Введіть український номер у форматі +380XXXXXXXXX'
_TG_MSG = 'Вкажіть Telegram у форматі @name або https://t.me/name'
_TG_NAME = re.compile(r'^[A-Za-z0-9_]{5,32}$')
_TG_URL_PREFIX = re.compile(r'(?i)^(?:https?://)?t\.me/')


def validate_ua_phone_or_blank(value):
    if value is None or (isinstance(value, str) and not value.strip()):
        return
    if not is_ua_phone(value):
        raise ValidationError(_PHONE_MSG)


def display_ua_phone(value):
    raw = (value or '').strip()
    if not raw:
        return ''
    normalized = normalize_ua_phone(raw)
    if not normalized:
        return ''
    local = normalized[4:]
    return f'+38 (0{local[:2]}) {local[2:5]}-{local[5:7]}-{local[7:9]}'


def _telegram_name(value):
    raw = (value or '').strip()
    if not raw:
        return ''
    if raw.startswith('@'):
        name = raw[1:].strip()
    elif _TG_URL_PREFIX.match(raw):
        url = raw if '://' in raw else f'https://{raw}'
        parsed = urlparse(url)
        host = (parsed.hostname or '').lower()
        if host != 't.me':
            raise ValidationError(_TG_MSG)
        name = (parsed.path or '').strip('/').split('/')[0]
    else:
        raise ValidationError(_TG_MSG)
    if not _TG_NAME.match(name):
        raise ValidationError(_TG_MSG)
    return name


def normalize_telegram_url(value):
    name = _telegram_name(value)
    if not name:
        return ''
    return f'https://t.me/{name}'


def normalize_telegram_handle(value):
    name = _telegram_name(value)
    if not name:
        return ''
    return f'@{name}'


_TG_USER_MSG = (
    'Вкажіть нік Telegram: 5–32 символи (латиниця, цифри та _), '
    'або @нік, або посилання t.me/нік чи telegram.me/нік.'
)
_TG_USER = re.compile(r'^[A-Za-z0-9_]{5,32}$')
_TG_HOSTS = frozenset({'t.me', 'telegram.me'})


def normalize_telegram_username(value):
    """Нік для відділення. Порожнє лишається порожнім. Інакше ValidationError українською."""
    raw = (value or '').strip()
    if not raw:
        return ''
    if any(ch.isspace() or ord(ch) < 32 for ch in raw):
        raise ValidationError(_TG_USER_MSG)
    name = _telegram_username_from(raw)
    if not _TG_USER.fullmatch(name or ''):
        raise ValidationError(_TG_USER_MSG)
    return name


def _telegram_username_from(raw):
    if raw.startswith('@'):
        rest = raw[1:]
        if any(mark in rest for mark in ('/', '?', '#', '@')):
            raise ValidationError(_TG_USER_MSG)
        return rest
    lower = raw.lower()
    looks_like_url = (
        '://' in raw
        or lower.startswith('t.me/')
        or lower.startswith('telegram.me/')
    )
    if not looks_like_url:
        return raw
    url = raw if '://' in raw else f'https://{raw}'
    parsed = urlparse(url)
    scheme = (parsed.scheme or '').lower()
    host = (parsed.hostname or '').lower()
    if host.startswith('www.'):
        host = host[4:]
    if scheme not in {'http', 'https'} or host not in _TG_HOSTS:
        raise ValidationError(_TG_USER_MSG)
    if parsed.username or parsed.password or parsed.port not in (None, 80, 443):
        raise ValidationError(_TG_USER_MSG)
    if parsed.query or parsed.fragment:
        raise ValidationError(_TG_USER_MSG)
    segments = [part for part in (parsed.path or '').split('/') if part]
    if len(segments) != 1:
        raise ValidationError(_TG_USER_MSG)
    return segments[0]
