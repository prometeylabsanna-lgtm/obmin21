"""Telegram Bot API backend for staff notifications."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

_API = 'https://api.telegram.org/bot{token}/sendMessage'
_TIMEOUT = 5


def resolve_chat_ids() -> list[str]:
    raw = getattr(settings, 'TELEGRAM_CHAT_ID', None) or []
    if isinstance(raw, str):
        chats = [part.strip() for part in raw.split(',') if part.strip()]
    else:
        chats = [str(part).strip() for part in raw if str(part).strip()]
    if chats:
        return chats
    try:
        from src.core.models import SiteSettings

        fallback = (SiteSettings.load().notify_telegram_chat_id or '').strip()
        if fallback:
            return [fallback]
    except Exception:
        logger.exception('Telegram: failed to load SiteSettings chat fallback')
    return []


def send_telegram_html(text: str) -> bool:
    """Send HTML message to all configured staff chats. Never raises."""
    try:
        token = (getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or '').strip()
        if not token:
            logger.warning('Telegram notify skipped: TELEGRAM_BOT_TOKEN is empty')
            return False
        chats = resolve_chat_ids()
        if not chats:
            logger.warning('Telegram notify skipped: no chat id configured')
            return False
        if not (text or '').strip():
            logger.warning('Telegram notify skipped: empty text')
            return False

        ok_any = False
        for chat_id in chats:
            if _send_one(token, chat_id, text):
                ok_any = True
        return ok_any
    except Exception:
        logger.exception('Telegram notify failed')
        return False


def _send_one(token: str, chat_id: str, text: str) -> bool:
    payload = json.dumps(
        {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True,
        },
        ensure_ascii=False,
    ).encode('utf-8')
    request = urllib.request.Request(
        _API.format(token=token),
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
            response.read()
        return True
    except Exception:
        logger.exception('Telegram send failed for chat_id=%s', chat_id)
        return False
