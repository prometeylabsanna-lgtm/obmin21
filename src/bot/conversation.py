from src.bot import keyboards, services, texts
from src.bot.handlers import branches, contact, exchange, rates
from src.bot.handlers.common import cancel_flow, send_menu, start_welcome
from src.bot.outbox import CollectorBot, Outgoing
from src.bot.states import EXCHANGE_STATES, FEEDBACK_STATES, BotState


def handle_text(from_user, text: str) -> list[Outgoing]:
    bot = CollectorBot()
    profile = services.upsert_profile(from_user)
    chat_id = profile.chat_id
    raw = (text or '').strip()
    if not raw:
        send_menu(bot, chat_id)
        return bot.items

    lowered = raw.lower()
    if lowered in {'/start', '/menu', 'меню'}:
        start_welcome(bot, chat_id, profile)
        return bot.items
    if lowered in {'/help', 'допомога'}:
        bot.send_message(chat_id, texts.HELP, reply_markup=keyboards.main_menu())
        return bot.items
    if lowered in {'/cancel', 'скасувати'}:
        cancel_flow(bot, chat_id)
        return bot.items
    if lowered in {'/kursy', 'курси'}:
        rates.start_rates(bot, chat_id, profile)
        return bot.items
    if lowered in {'/zayavka', 'заявка'}:
        exchange.start_exchange(bot, chat_id, profile)
        return bot.items
    if lowered in {'/kontakty', 'звернення'}:
        contact.start_feedback(bot, chat_id, profile)
        return bot.items
    if lowered in {'/viddilennya', 'відділення'}:
        branches.start_branches(bot, chat_id, profile)
        return bot.items

    session = services.get_session(chat_id)
    if session.state in FEEDBACK_STATES:
        contact.handle_feedback_text(bot, chat_id, profile, raw)
        return bot.items
    if session.state in EXCHANGE_STATES:
        exchange.handle_exchange_text(bot, chat_id, profile, raw)
        return bot.items

    send_menu(bot, chat_id, texts.UNKNOWN)
    return bot.items


def handle_callback(from_user, data: str) -> list[Outgoing]:
    bot = CollectorBot()
    profile = services.upsert_profile(from_user)
    chat_id = profile.chat_id
    payload = data or ''
    session = services.get_session(chat_id)

    if payload == keyboards.CB_CANCEL:
        cancel_flow(bot, chat_id)
        return bot.items
    if payload == keyboards.CB_MENU:
        services.clear_session(chat_id)
        send_menu(bot, chat_id)
        return bot.items
    if payload == keyboards.CB_RATES:
        rates.start_rates(bot, chat_id, profile)
        return bot.items
    if payload == keyboards.CB_EX:
        exchange.start_exchange(bot, chat_id, profile)
        return bot.items
    if payload == keyboards.CB_FB:
        contact.start_feedback(bot, chat_id, profile)
        return bot.items
    if payload == keyboards.CB_BR:
        branches.start_branches(bot, chat_id, profile)
        return bot.items
    if payload.startswith('c:'):
        _city(bot, chat_id, profile, payload)
        return bot.items
    if payload.startswith('p:'):
        exchange.handle_pair(bot, chat_id, profile, payload)
        return bot.items
    if payload.startswith('d:'):
        exchange.handle_direction(bot, chat_id, profile, payload)
        return bot.items
    if payload.startswith('br:'):
        exchange.handle_branch(bot, chat_id, profile, payload)
        return bot.items
    if payload in {keyboards.CB_CONSENT_YES, keyboards.CB_CONSENT_NO}:
        if session.state == BotState.FB_CONSENT:
            contact.apply_feedback_consent(bot, chat_id, profile, payload)
        elif session.state == BotState.EX_CONSENT:
            exchange.handle_consent(bot, chat_id, profile, payload)
        return bot.items
    if payload == keyboards.CB_CONFIRM:
        exchange.handle_confirm(bot, chat_id, profile)
        return bot.items

    send_menu(bot, chat_id, texts.UNKNOWN)
    return bot.items


def _city(bot, chat_id, profile, payload: str) -> None:
    parts = payload.split(':')
    if len(parts) != 3:
        return
    try:
        city_id = int(parts[2])
    except ValueError:
        return
    city = services.city_by_id(city_id)
    if city is None:
        bot.send_message(chat_id, texts.NO_CITIES)
        return
    rates.start_city_action(bot, chat_id, profile, parts[1], city)
