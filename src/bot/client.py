import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


def send_telegram_message(chat_id: str, text: str) -> bool:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or not chat_id or not text:
        logger.info('Telegram send skipped (missing token/chat/text)')
        return False
    payload = json.dumps(
        {'chat_id': chat_id, 'text': text, 'disable_web_page_preview': True},
        ensure_ascii=False,
    ).encode('utf-8')
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{token}/sendMessage',
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
        return True
    except urllib.error.URLError:
        logger.exception('Telegram send failed')
        return False


def telegram_api(method: str, payload: dict) -> dict:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError('TELEGRAM_BOT_TOKEN is empty')
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        f'https://api.telegram.org/bot{token}/{method}',
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode('utf-8'))
