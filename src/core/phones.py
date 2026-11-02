import re

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
    if not digits:
        return ''
    if digits.startswith('380'):
        return f'+{digits}'
    if digits.startswith('0') and len(digits) == 10:
        return f'+38{digits}'
    if digits.startswith('38'):
        return f'+{digits}'
    return f'+{digits}'
