import re

from django.conf import settings
from django.utils import timezone

from src.core.models import SiteSettings
from src.core.notifications import notify_contact, notify_new_lead
from src.core.phones import phone_digits
from src.leads.models import ContactMessage, ExchangeRequest

PHONE_RE = re.compile(r'^\+?[\d\s\-()]{10,20}$')


def normalize_phone(phone):
    return re.sub(r'\s+', ' ', phone.strip())


def validate_phone(phone):
    return bool(PHONE_RE.match(phone or ''))


def create_exchange_request(*, cleaned, city, hold_minutes=None, source='web', telegram_chat_id=''):
    settings_obj = SiteSettings.load()
    minutes = hold_minutes or settings_obj.rate_hold_minutes or settings.RATE_HOLD_MINUTES
    expires_at = timezone.now() + timezone.timedelta(minutes=minutes)
    phone_norm = normalize_phone(cleaned['phone'])
    digits = phone_digits(phone_norm)

    existing = (
        ExchangeRequest.objects.filter(
            city=city,
            pair=cleaned['pair'],
            status=ExchangeRequest.Status.NEW,
            expires_at__gt=timezone.now(),
        )
        .order_by('-created_at')
    )
    for obj in existing[:25]:
        if phone_digits(obj.phone) == digits:
            return obj

    obj = ExchangeRequest.objects.create(
        name=cleaned['name'].strip(),
        phone=phone_norm,
        messenger=cleaned.get('messenger', '').strip(),
        pair=cleaned['pair'],
        board=cleaned.get('board', 'retail'),
        direction=cleaned['direction'],
        amount_give=cleaned['amount_give'],
        amount_receive=cleaned['amount_receive'],
        rate_fixed=cleaned['rate_fixed'],
        city=city,
        branch=cleaned['branch'],
        consent=True,
        expires_at=expires_at,
        source=source,
        telegram_chat_id=telegram_chat_id or '',
    )
    notify_new_lead(obj)
    return obj


def create_contact_message(*, cleaned, city=None, source='web', telegram_chat_id=''):
    obj = ContactMessage.objects.create(
        name=cleaned['name'].strip(),
        phone=normalize_phone(cleaned['phone']),
        message=cleaned['message'].strip(),
        city=city,
        consent=True,
        source=source,
        telegram_chat_id=telegram_chat_id or '',
    )
    notify_contact(obj)
    return obj
