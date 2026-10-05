from src.bot import keyboards, services, texts
from src.bot.handlers.common import send_menu
from src.bot.states import BotState


def start_rates(bot, chat_id: int, profile) -> None:
    cities = services.list_cities()
    if not cities:
        bot.send_message(chat_id, texts.NO_CITIES)
        return
    if len(cities) == 1:
        _show_rates(bot, chat_id, profile, cities[0])
        return
    services.patch_session(profile.chat_id, state=BotState.CITY_PICK, purpose='r')
    bot.send_message(
        chat_id,
        texts.NEED_CITY,
        reply_markup=keyboards.cities_keyboard(cities, 'r'),
    )


def _show_rates(bot, chat_id: int, profile, city) -> None:
    services.set_profile_city(profile.chat_id, city)
    services.clear_session(profile.chat_id)
    body = services.format_rates(city)
    bot.send_message(chat_id, body or texts.NO_PAIRS)
    send_menu(bot, chat_id)


def start_city_action(bot, chat_id: int, profile, purpose: str, city) -> None:
    from src.bot.handlers import branches, exchange

    if purpose == 'r':
        _show_rates(bot, chat_id, profile, city)
    elif purpose == 'e':
        exchange.after_city(bot, chat_id, profile, city)
    else:
        branches.after_city(bot, chat_id, profile, city)


def register(bot) -> None:
    @bot.message_handler(commands=['kursy'])
    def cmd_rates(message) -> None:
        profile = services.upsert_profile(message.from_user)
        start_rates(bot, message.chat.id, profile)

    @bot.callback_query_handler(func=lambda c: (c.data or '').startswith('c:'))
    def cb_city(call) -> None:
        bot.answer_callback_query(call.id)
        profile = services.upsert_profile(call.from_user)
        parts = (call.data or '').split(':')
        if len(parts) != 3:
            return
        _, purpose, raw_id = parts
        try:
            city_id = int(raw_id)
        except ValueError:
            return
        city = services.city_by_id(city_id)
        if city is None:
            bot.send_message(call.message.chat.id, texts.NO_CITIES)
            return
        start_city_action(bot, call.message.chat.id, profile, purpose, city)
