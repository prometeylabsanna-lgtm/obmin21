import logging
from threading import Lock

from django.conf import settings
from telebot import TeleBot

from src.bot.handlers import register_handlers

logger = logging.getLogger(__name__)

_lock = Lock()
_bot: TeleBot | None = None


def get_bot() -> TeleBot:
    global _bot
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError('TELEGRAM_BOT_TOKEN is empty')
    with _lock:
        if _bot is None:
            # threaded=False: gunicorn-воркер сам обробляє HTTP, окремі потоки telebot не потрібні
            instance = TeleBot(token, parse_mode='HTML', threaded=False)
            register_handlers(instance)
            _bot = instance
            logger.info('Telegram bot handlers registered')
        return _bot


def reset_bot() -> None:
    global _bot
    with _lock:
        _bot = None
