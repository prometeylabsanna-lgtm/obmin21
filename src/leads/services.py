import logging
import re

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from src.core.models import SiteSettings
from src.leads.models import ContactMessage, ExchangeRequest

logger = logging.getLogger(__name__)

PHONE_RE = re.compile(r'^\+?[\d\s\-()]{10,20}$')


def normalize_phone(phone):
    return re.sub(r'\s+', ' ', phone.strip())


def validate_phone(phone):
    return bool(PHONE_RE.match(phone or ''))


def create_exchange_request(*, cleaned, city, hold_minutes=None):
    settings_obj = SiteSettings.load()
    minutes = hold_minutes or settings_obj.rate_hold_minutes or settings.RATE_HOLD_MINUTES
    expires_at = timezone.now() + timezone.timedelta(minutes=minutes)

    obj = ExchangeRequest.objects.create(
        name=cleaned['name'].strip(),
        phone=normalize_phone(cleaned['phone']),
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
    )
    notify_new_lead(obj)
    return obj


def create_contact_message(*, cleaned, city=None):
    obj = ContactMessage.objects.create(
        name=cleaned['name'].strip(),
        phone=normalize_phone(cleaned['phone']),
        message=cleaned['message'].strip(),
        city=city,
        consent=True,
    )
    notify_contact(obj)
    return obj


def notify_new_lead(obj):
    site = SiteSettings.load()
    body = (
        f'Нова заявка #{obj.pk}\n'
        f'{obj.name} · {obj.phone}\n'
        f'{obj.pair.code} · {obj.get_direction_display()}\n'
        f'Віддає: {obj.amount_give} · Отримує: {obj.amount_receive}\n'
        f'Курс: {obj.rate_fixed}\n'
        f'{obj.city.name} · {obj.branch.address}\n'
        f'До: {obj.expires_at:%d.%m.%Y %H:%M}'
    )
    _send_email(site, f'Заявка Обмін21 #{obj.pk}', body)
    _send_telegram(site, body)


def notify_contact(obj):
    site = SiteSettings.load()
    body = (
        f'Звернення #{obj.pk}\n'
        f'{obj.name} · {obj.phone}\n'
        f'{obj.message}'
    )
    _send_email(site, f'Звернення Обмін21 #{obj.pk}', body)
    _send_telegram(site, body)


def _send_email(site, subject, body):
    to = site.notify_email
    if not to:
        logger.info('Lead notify email skipped (empty notify_email): %s', subject)
        return
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=True)
    except Exception:
        logger.exception('Email notify failed')


def _send_telegram(site, body):
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = site.notify_telegram_chat_id or settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        logger.info('Telegram notify skipped (missing token/chat)')
        return
    try:
        import json
        import urllib.request

        payload = json.dumps(
            {'chat_id': chat_id, 'text': body},
            ensure_ascii=False,
        ).encode('utf-8')
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
    except Exception:
        logger.exception('Telegram notify failed')
