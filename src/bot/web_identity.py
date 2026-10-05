from types import SimpleNamespace

WEB_PREFIX = 'w:'


def ensure_web_chat_id(request) -> str:
    if not request.session.session_key:
        request.session.create()
    key = request.session.session_key or ''
    return f'{WEB_PREFIX}{key[:30]}'


def web_from_user(request):
    chat_id = ensure_web_chat_id(request)
    return SimpleNamespace(
        id=chat_id,
        username='',
        first_name='Гість сайту',
        last_name='',
    )
