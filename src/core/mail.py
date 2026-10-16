import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

_RESEND_URL = 'https://api.resend.com/emails'


class ResendEmailBackend(BaseEmailBackend):
    """Відправка через Resend. Працює, коли в середовищі є RESEND_API_KEY."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        sent = 0
        for message in email_messages:
            if self._send(message):
                sent += 1
        return sent

    def _send(self, message):
        key = (getattr(settings, 'RESEND_API_KEY', '') or '').strip()
        if not key:
            logger.info('Resend skipped: RESEND_API_KEY is empty')
            return False
        recipients = list(message.to or [])
        if not recipients:
            logger.info('Resend skipped: no recipients for %s', message.subject)
            return False
        payload = {
            'from': message.from_email or settings.DEFAULT_FROM_EMAIL,
            'to': recipients,
            'subject': message.subject or '',
            'text': message.body or '',
        }
        if message.cc:
            payload['cc'] = list(message.cc)
        if message.bcc:
            payload['bcc'] = list(message.bcc)
        html = _html_body(message)
        if html:
            payload['html'] = html
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        request = urllib.request.Request(
            _RESEND_URL,
            data=data,
            headers={
                'Authorization': f'Bearer {key}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                response.read()
            return True
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode('utf-8', errors='replace')[:500]
            logger.error('Resend HTTP %s: %s', exc.code, detail)
            if not self.fail_silently:
                raise
            return False
        except urllib.error.URLError:
            logger.exception('Resend request failed')
            if not self.fail_silently:
                raise
            return False


def _html_body(message):
    if getattr(message, 'content_subtype', '') == 'html':
        return message.body or ''
    for content, mimetype in getattr(message, 'alternatives', ()) or ():
        if mimetype == 'text/html':
            return content
    return ''
