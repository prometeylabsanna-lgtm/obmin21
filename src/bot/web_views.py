import logging

from django.core.cache import cache
from django.shortcuts import render
from django.views.decorators.http import require_http_methods, require_POST

from src.bot.conversation import handle_callback, handle_text
from src.bot.models import ChatMessage
from src.bot.outbox import Outgoing
from src.bot.web_identity import ensure_web_chat_id, web_from_user

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 40
RATE_LIMIT = 40


def _rate_ok(chat_id: str) -> bool:
    key = f'webchat:{chat_id}'
    n = cache.get(key, 0)
    if n >= RATE_LIMIT:
        return False
    cache.set(key, n + 1, 60)
    return True


def _store(chat_id: str, role: str, text: str, buttons=None) -> ChatMessage:
    msg = ChatMessage.objects.create(
        chat_id=chat_id,
        role=role,
        text=text,
        buttons=buttons or [],
    )
    keep_ids = list(
        ChatMessage.objects.filter(chat_id=chat_id)
        .order_by('-created_at')
        .values_list('id', flat=True)[:HISTORY_LIMIT]
    )
    ChatMessage.objects.filter(chat_id=chat_id).exclude(id__in=keep_ids).delete()
    return msg


def _store_replies(chat_id: str, replies: list[Outgoing]) -> list[ChatMessage]:
    saved = []
    for item in replies:
        saved.append(_store(
            chat_id,
            ChatMessage.Role.BOT,
            item.html.replace('\n', '<br>'),
            item.buttons,
        ))
    return saved


@require_http_methods(['GET'])
def chat_log(request):
    chat_id = ensure_web_chat_id(request)
    user = web_from_user(request)
    messages = list(ChatMessage.objects.filter(chat_id=chat_id))
    if not messages:
        replies = handle_text(user, '/start')
        messages = _store_replies(chat_id, replies)
    return render(request, 'bot/chat_messages.html', {'messages': messages})


@require_POST
def chat_send(request):
    chat_id = ensure_web_chat_id(request)
    user = web_from_user(request)
    text = (request.POST.get('text') or '').strip()[:2000]
    if not text:
        return render(request, 'bot/chat_messages.html', {'messages': []})
    if not _rate_ok(chat_id):
        return render(request, 'bot/chat_messages.html', {
            'messages': [_store(chat_id, ChatMessage.Role.BOT, 'Забагато запитів. Зачекайте хвилину.')],
        })
    user_msg = _store(chat_id, ChatMessage.Role.USER, text)
    try:
        replies = handle_text(user, text)
    except Exception:
        logger.exception('Web chat text failed')
        replies = [Outgoing(html='Сталася помилка. Спробуйте /start')]
    bot_msgs = _store_replies(chat_id, replies)
    return render(request, 'bot/chat_messages.html', {'messages': [user_msg, *bot_msgs]})


@require_POST
def chat_callback(request):
    chat_id = ensure_web_chat_id(request)
    user = web_from_user(request)
    data = (request.POST.get('data') or '')[:64]
    if not data:
        return render(request, 'bot/chat_messages.html', {'messages': []})
    if not _rate_ok(chat_id):
        return render(request, 'bot/chat_messages.html', {
            'messages': [_store(chat_id, ChatMessage.Role.BOT, 'Забагато запитів. Зачекайте хвилину.')],
        })
    label = (request.POST.get('label') or data)[:80]
    user_msg = _store(chat_id, ChatMessage.Role.USER, label)
    try:
        replies = handle_callback(user, data)
    except Exception:
        logger.exception('Web chat callback failed')
        replies = [Outgoing(html='Сталася помилка. Спробуйте /start')]
    bot_msgs = _store_replies(chat_id, replies)
    return render(request, 'bot/chat_messages.html', {'messages': [user_msg, *bot_msgs]})
