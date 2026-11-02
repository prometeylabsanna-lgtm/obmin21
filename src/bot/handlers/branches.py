from src.bot import keyboards, services, texts
from src.bot.handlers.common import send_menu
from src.core.models import SiteSettings
from src.core.phones import bound_phone_request, resolve_site_phone


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


def _contact_line(city):
    request = bound_phone_request()
    if request is None:
        phone = str(getattr(city, 'phone', '') or '').strip()
        if not phone:
            return ''
        return f'Телефон міста: {phone}'
    display, _href = resolve_site_phone(request, SiteSettings.load())
    if not display:
        return ''
    return f'Телефон: {display}'


def after_city(bot, chat_id: int, profile, city) -> None:
    services.set_profile_city(profile.chat_id, city)
    services.clear_session(profile.chat_id)
    body = services.format_branches(city)
    extra = _contact_line(city)
    if body:
        text = body if not extra else f'{body}\n\n{extra}'
        bot.send_message(chat_id, text)
    else:
        fallback = extra.removeprefix('Телефон: ').removeprefix('Телефон міста: ').strip()
        bot.send_message(chat_id, fallback or texts.NO_BRANCHES or texts.CONTACTS_EMPTY)
    send_menu(bot, chat_id)


def register(bot) -> None:
    @bot.message_handler(commands=['viddilennya'])
    def cmd_branches(message) -> None:
        profile = services.upsert_profile(message.from_user)
        start_branches(bot, message.chat.id, profile)
