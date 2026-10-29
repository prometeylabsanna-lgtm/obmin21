"""Staff notifications for form submissions (exchange, contact, review).

Forms do not collect client email addresses. Only staff are notified via
Telegram — there is no client confirmation email.
"""

from __future__ import annotations

import logging
import threading

from django.conf import settings
from django.db import transaction

from . import messages
from .telegram import send_telegram_html

logger = logging.getLogger(__name__)

KIND_EXCHANGE = 'exchange'
KIND_CONTACT = 'contact'
KIND_REVIEW = 'review'


def notify_submission(kind: str, obj) -> None:
    """Build and dispatch staff notifications. Never raises; never blocks request when async."""
    try:
        _subject, _plain, html_body = messages.build(kind, obj)
    except Exception:
        logger.exception('notify_submission: failed to build message kind=%s', kind)
        return

    def _dispatch() -> None:
        try:
            send_telegram_html(html_body)
        except Exception:
            logger.exception('notify_submission: telegram failed kind=%s', kind)

    try:
        if getattr(settings, 'NOTIFICATIONS_ASYNC', True):
            transaction.on_commit(
                lambda: threading.Thread(target=_dispatch, daemon=True).start(),
            )
        else:
            transaction.on_commit(_dispatch)
    except Exception:
        logger.exception('notify_submission: dispatch failed kind=%s', kind)


def notify_new_lead(obj) -> None:
    notify_submission(KIND_EXCHANGE, obj)


def notify_contact(obj) -> None:
    notify_submission(KIND_CONTACT, obj)


def notify_review(obj) -> None:
    notify_submission(KIND_REVIEW, obj)
