"""Resend HTTP helper and staff email notifications.

Forms do not collect client email addresses. Only staff recipients
(NOTIFY_EMAIL_TO / SiteSettings.notify_email) are notified — there is
no client confirmation email.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

RESEND_URL = 'https://api.resend.com/emails'
_TIMEOUT = 5


def resolve_from_email() -> str:
    value = (getattr(settings, 'EMAIL_FROM', '') or '').strip()
    if value:
        return value
    return (getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '').strip()


def resolve_staff_recipients(override: list[str] | None = None) -> list[str]:
    if override is not None:
        return [str(item).strip() for item in override if str(item).strip()]
    raw = getattr(settings, 'NOTIFY_EMAIL_TO', None) or []
    if isinstance(raw, str):
        recipients = [part.strip() for part in raw.split(',') if part.strip()]
    else:
        recipients = [str(part).strip() for part in raw if str(part).strip()]
    if recipients:
        return recipients
    try:
        from src.core.models import SiteSettings

        fallback = (SiteSettings.load().notify_email or '').strip()
        if fallback:
            return [fallback]
    except Exception:
        logger.exception('Resend: failed to load SiteSettings email fallback')
    return []


def post_resend_email(
    *,
    api_key: str,
    from_email: str,
    to: list[str],
    subject: str,
    text: str = '',
    html: str = '',
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    timeout: float = _TIMEOUT,
) -> bool:
    """POST JSON to Resend emails API. Returns True on HTTP success."""
    payload: dict = {
        'from': from_email,
        'to': list(to),
        'subject': subject or '',
        'text': text or '',
    }
    if html:
        payload['html'] = html
    if cc:
        payload['cc'] = list(cc)
    if bcc:
        payload['bcc'] = list(bcc)
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    request = urllib.request.Request(
        RESEND_URL,
        data=data,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
        return True
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')[:500]
        logger.error('Resend HTTP %s: %s', exc.code, detail)
        return False
    except Exception:
        logger.exception('Resend request failed')
        return False


def send_staff_email(subject: str, text: str, *, to_override: list[str] | None = None) -> bool:
    """Send staff notification via Resend. Never raises. Returns bool."""
    try:
        key = (getattr(settings, 'RESEND_API_KEY', '') or '').strip()
        if not key:
            logger.warning('Email notify skipped: RESEND_API_KEY is empty')
            return False
        recipients = resolve_staff_recipients(to_override)
        if not recipients:
            logger.warning('Email notify skipped: no recipients configured')
            return False
        from_email = resolve_from_email()
        if not from_email:
            logger.warning('Email notify skipped: EMAIL_FROM / DEFAULT_FROM_EMAIL empty')
            return False
        return post_resend_email(
            api_key=key,
            from_email=from_email,
            to=recipients,
            subject=subject,
            text=text,
            timeout=_TIMEOUT,
        )
    except Exception:
        logger.exception('Email notify failed')
        return False
