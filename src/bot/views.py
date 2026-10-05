import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from telebot.types import Update

from src.bot.bot import get_bot
from src.bot.models import TelegramProfile

logger = logging.getLogger(__name__)


def _secret_ok(request) -> bool:
    expected = settings.TELEGRAM_WEBHOOK_SECRET
    if not expected:
        return False
    got = request.META.get('HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN', '')
    if len(got) != len(expected):
        return False
    return hmac.compare_digest(got, expected)


@csrf_exempt
@require_POST
def telegram_webhook(request):
    if not _secret_ok(request):
        return HttpResponseForbidden('forbidden')
    if not settings.TELEGRAM_BOT_TOKEN:
        return HttpResponse(status=503)
    try:
        payload = json.loads(request.body.decode('utf-8'))
        update = Update.de_json(payload)
        if update is None:
            raise ValueError('empty update')
        if _is_blocked(update):
            return JsonResponse({'ok': True})
        get_bot().process_new_updates([update])
    except Exception:
        logger.exception('Telegram webhook failed')
    return JsonResponse({'ok': True})


def _is_blocked(update: Update) -> bool:
    user = None
    if update.message and update.message.from_user:
        user = update.message.from_user
    elif update.callback_query and update.callback_query.from_user:
        user = update.callback_query.from_user
    if user is None:
        return False
    return TelegramProfile.objects.filter(
        chat_id=str(user.id),
        is_blocked=True,
    ).exists()
