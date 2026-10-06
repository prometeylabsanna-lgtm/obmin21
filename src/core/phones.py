import re


def phone_digits(phone):
    return re.sub(r'\D+', '', phone or '')


def phone_tel(phone):
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
