import logging

from django.core.cache import cache
from django.shortcuts import render
from django.views.decorators.http import require_http_methods, require_POST

from src.bot.conversation import handle_callback, handle_text
from src.bot.models import ChatMessage
from src.bot.outbox import Outgoing
from src.bot.web_identity import ensure_web_chat_id, web_from_user
from src.core.phones import pop_phone_request, push_phone_request
from src.leads.models import ExchangeRequest

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 40
# Ліміт на діалог: не менше 20 повідомлень/хв (кнопки бота теж рахуються).
RATE_LIMIT = 40
RATE_WINDOW = 60
# Ліміт на IP (кілька вкладок/сесій з одного IP) — запас від спаму, не для звичайної розмови.
IP_RATE_LIMIT = 120


def _rate_ok(chat_id: str) -> bool:
    """Фіксоване вікно 60 с: лічильник не продовжує TTL на кожне повідомлення."""
    key = f'webchat:{chat_id}'
    cache.add(key, 0, RATE_WINDOW)
    try:
        n = cache.incr(key)
    except ValueError:
        cache.set(key, 1, RATE_WINDOW)
        n = 1
    return n <= RATE_LIMIT


def _call_with_phone(request, fn):
    token = push_phone_request(request)
    try:
        return fn()
    finally:
        pop_phone_request(token)


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
            item.html,
            item.buttons,
        ))
    return saved


def _last_lead_id(chat_id: str) -> int:
    last = (
        ExchangeRequest.objects.filter(telegram_chat_id=str(chat_id))
        .order_by('-id').values_list('id', flat=True).first()
    )
    return last or 0


def _fresh_context(chat_id: str, before: int, user_msg, bot_msgs) -> dict:
    """lead-success лише у свіжому фрагменті, де саме зараз створено заявку (рівно 1 раз)."""
    ctx = {'messages': [user_msg, *bot_msgs]}
    lead_id = _last_lead_id(chat_id)
    if lead_id > before and bot_msgs:
        ctx['success_msg_id'] = bot_msgs[0].id
        ctx['success_lead_id'] = lead_id
    return ctx


@require_http_methods(['GET'])
def chat_log(request):
    chat_id = ensure_web_chat_id(request)
    user = web_from_user(request)
    messages = list(ChatMessage.objects.filter(chat_id=chat_id))
    if not messages:
        replies = _call_with_phone(request, lambda: handle_text(user, '/start'))
        messages = _store_replies(chat_id, replies)
    return render(request, 'bot/chat_messages.html', {'messages': messages})


@require_POST
def chat_send(request):
    from src.core.rate_limit import allow_request

    chat_id = ensure_web_chat_id(request)
    user = web_from_user(request)
    text = (request.POST.get('text') or '').strip()[:2000]
    if request.POST.get('website'):
        # Honeypot заповнений — бот. Мовчки нічого не зберігаємо.
        return render(request, 'bot/chat_messages.html', {'messages': []})
    if not text:
        return render(request, 'bot/chat_messages.html', {'messages': []})
    if not _rate_ok(chat_id) or not allow_request(
        request, 'chat', limit=IP_RATE_LIMIT, window=RATE_WINDOW,
    ):
        return render(request, 'bot/chat_messages.html', {
            'messages': [_store(chat_id, ChatMessage.Role.BOT, 'Забагато запитів. Зачекайте хвилину.')],
        })
    user_msg = _store(chat_id, ChatMessage.Role.USER, text)
    before = _last_lead_id(chat_id)
    try:
        replies = _call_with_phone(request, lambda: handle_text(user, text))
    except Exception:
        logger.exception('Web chat text failed')
        replies = [Outgoing(html='Сталася помилка. Спробуйте /start')]
    bot_msgs = _store_replies(chat_id, replies)
    return render(request, 'bot/chat_messages.html', _fresh_context(chat_id, before, user_msg, bot_msgs))


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
    before = _last_lead_id(chat_id)
    try:
        replies = _call_with_phone(request, lambda: handle_callback(user, data))
    except Exception:
        logger.exception('Web chat callback failed')
        replies = [Outgoing(html='Сталася помилка. Спробуйте /start')]
    bot_msgs = _store_replies(chat_id, replies)
    return render(request, 'bot/chat_messages.html', _fresh_context(chat_id, before, user_msg, bot_msgs))
