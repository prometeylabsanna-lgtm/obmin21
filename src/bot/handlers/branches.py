from src.bot import keyboards, services, texts
from src.bot.handlers.common import send_menu


def start_branches(bot, chat_id: int, profile) -> None:
    cities = services.list_cities()
    if not cities:
        bot.send_message(chat_id, texts.NO_CITIES)
        return
    if len(cities) == 1:
        after_city(bot, chat_id, profile, cities[0])
        return
    from src.bot.states import BotState

    services.patch_session(profile.chat_id, state=BotState.CITY_PICK, purpose='b')
    bot.send_message(
        chat_id,
        texts.NEED_CITY,
        reply_markup=keyboards.cities_keyboard(cities, 'b'),
    )


def after_city(bot, chat_id: int, profile, city) -> None:
    services.set_profile_city(profile.chat_id, city)
    services.clear_session(profile.chat_id)
    body = services.format_branches(city)
    extra = city.phone or ''
    if body:
        text = body if not extra else f'{body}\n\nТелефон міста: {extra}'
        bot.send_message(chat_id, text)
    else:
        bot.send_message(chat_id, extra or texts.NO_BRANCHES or texts.CONTACTS_EMPTY)
    send_menu(bot, chat_id)


def register(bot) -> None:
    @bot.message_handler(commands=['viddilennya'])
    def cmd_branches(message) -> None:
        profile = services.upsert_profile(message.from_user)
        start_branches(bot, message.chat.id, profile)
