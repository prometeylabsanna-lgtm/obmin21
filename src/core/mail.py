import logging

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

from src.core.notifications.resend import post_resend_email, resolve_from_email

logger = logging.getLogger(__name__)


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
        from_email = message.from_email or resolve_from_email()
        html = _html_body(message)
        ok = post_resend_email(
            api_key=key,
            from_email=from_email,
            to=recipients,
            subject=message.subject or '',
            text=message.body or '',
            html=html,
            cc=list(message.cc) if message.cc else None,
            bcc=list(message.bcc) if message.bcc else None,
            timeout=5,
        )
        if not ok and not self.fail_silently:
            raise RuntimeError(f'Resend failed for subject={message.subject!r}')
        return ok


def _html_body(message):
    if getattr(message, 'content_subtype', '') == 'html':
        return message.body or ''
    for content, mimetype in getattr(message, 'alternatives', ()) or ():
        if mimetype == 'text/html':
            return content
    return ''
