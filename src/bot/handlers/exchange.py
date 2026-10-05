from src.bot import keyboards, services, texts
from src.bot.handlers.common import send_menu
from src.bot.states import EXCHANGE_STATES, BotState
from src.leads.models import ExchangeRequest
from src.leads.services import normalize_phone, validate_phone
from src.network.selectors import get_city_branches


def start_exchange(bot, chat_id: int, profile) -> None:
    cities = services.list_cities()
    if not cities:
        bot.send_message(chat_id, texts.NO_CITIES)
        return
    if len(cities) == 1:
        after_city(bot, chat_id, profile, cities[0])
        return
    services.patch_session(profile.chat_id, state=BotState.EX_CITY, purpose='e')
    bot.send_message(
        chat_id,
        texts.NEED_CITY,
        reply_markup=keyboards.cities_keyboard(cities, 'e'),
    )


def after_city(bot, chat_id: int, profile, city) -> None:
    services.set_profile_city(profile.chat_id, city)
    pairs = services.exchange_pairs()
    if not pairs:
        services.clear_session(profile.chat_id)
        bot.send_message(chat_id, texts.NO_PAIRS)
        send_menu(bot, chat_id)
        return
    services.patch_session(
        profile.chat_id,
        state=BotState.EX_PAIR,
        city_id=city.pk,
    )
    bot.send_message(
        chat_id,
        texts.CHOOSE_PAIR,
        reply_markup=keyboards.pairs_keyboard(pairs),
    )


def register(bot) -> None:
    @bot.message_handler(commands=['zayavka'])
    def cmd_exchange(message) -> None:
        profile = services.upsert_profile(message.from_user)
        start_exchange(bot, message.chat.id, profile)

    @bot.callback_query_handler(func=lambda c: (c.data or '').startswith('p:'))
    def cb_pair(call) -> None:
        bot.answer_callback_query(call.id)
        profile = services.upsert_profile(call.from_user)
        session = services.get_session(profile.chat_id)
        if session.state != BotState.EX_PAIR:
            return
        try:
            pair_id = int(call.data.split(':', 1)[1])
        except (ValueError, IndexError):
            return
        pair = services.pair_by_id(pair_id)
        if pair is None:
            bot.send_message(call.message.chat.id, texts.NO_PAIRS)
            return
        services.patch_session(
            profile.chat_id,
            state=BotState.EX_DIRECTION,
            pair_id=pair.pk,
        )
        bot.send_message(
            call.message.chat.id,
            texts.CHOOSE_DIRECTION,
            reply_markup=keyboards.direction_keyboard(),
        )

    @bot.callback_query_handler(func=lambda c: (c.data or '').startswith('d:'))
    def cb_direction(call) -> None:
        bot.answer_callback_query(call.id)
        profile = services.upsert_profile(call.from_user)
        session = services.get_session(profile.chat_id)
        if session.state != BotState.EX_DIRECTION:
            return
        direction = call.data.split(':', 1)[1]
        if direction not in {ExchangeRequest.Direction.BUY, ExchangeRequest.Direction.SELL}:
            return
        services.patch_session(
            profile.chat_id,
            state=BotState.EX_AMOUNT,
            direction=direction,
        )
        bot.send_message(call.message.chat.id, texts.ENTER_AMOUNT)

    @bot.callback_query_handler(func=lambda c: (c.data or '').startswith('br:'))
    def cb_branch(call) -> None:
        bot.answer_callback_query(call.id)
        profile = services.upsert_profile(call.from_user)
        session = services.get_session(profile.chat_id)
        if session.state != BotState.EX_BRANCH:
            return
        city = services.resolve_city(profile, session.data)
        try:
            branch_id = int(call.data.split(':', 1)[1])
        except (ValueError, IndexError):
            return
        branch = services.branch_by_id(branch_id, city) if city else None
        if branch is None:
            bot.send_message(call.message.chat.id, texts.NO_BRANCHES)
            return
        services.patch_session(
            profile.chat_id,
            state=BotState.EX_NAME,
            branch_id=branch.pk,
        )
        bot.send_message(call.message.chat.id, texts.ENTER_NAME)

    @bot.callback_query_handler(
        func=lambda c: c.data in {keyboards.CB_CONSENT_YES, keyboards.CB_CONSENT_NO}
        and services.get_session(str(c.from_user.id)).state == BotState.EX_CONSENT,
    )
    def cb_consent(call) -> None:
        bot.answer_callback_query(call.id)
        profile = services.upsert_profile(call.from_user)
        chat_id = call.message.chat.id
        if call.data == keyboards.CB_CONSENT_NO:
            bot.send_message(chat_id, texts.NEED_CONSENT)
            services.clear_session(profile.chat_id)
            send_menu(bot, chat_id)
            return
        session = services.patch_session(profile.chat_id, state=BotState.EX_CONFIRM)
        bot.send_message(
            chat_id,
            _confirm_text(profile, session.data),
            reply_markup=keyboards.confirm_keyboard(),
        )

    @bot.callback_query_handler(func=lambda c: c.data == keyboards.CB_CONFIRM)
    def cb_confirm(call) -> None:
        bot.answer_callback_query(call.id)
        profile = services.upsert_profile(call.from_user)
        session = services.get_session(profile.chat_id)
        chat_id = call.message.chat.id
        if session.state != BotState.EX_CONFIRM:
            return
        try:
            obj = services.submit_exchange(profile.chat_id, profile, session.data)
        except ValueError:
            bot.send_message(chat_id, texts.UNKNOWN)
            services.clear_session(profile.chat_id)
            send_menu(bot, chat_id)
            return
        services.clear_session(profile.chat_id)
        bot.send_message(
            chat_id,
            texts.SAVED_REQUEST.format(
                until=obj.expires_at.strftime('%H:%M %d.%m.%Y'),
                address=texts.safe(obj.branch.address),
            ),
        )
        send_menu(bot, chat_id)

    @bot.message_handler(
        func=lambda m: services.get_session(str(m.from_user.id)).state in EXCHANGE_STATES,
        content_types=['text', 'contact'],
    )
    def on_exchange_input(message) -> None:
        profile = services.upsert_profile(message.from_user)
        session = services.get_session(profile.chat_id)
        chat_id = message.chat.id
        if session.state == BotState.EX_AMOUNT:
            _handle_amount(bot, chat_id, profile, session, message.text or '')
        elif session.state == BotState.EX_NAME:
            _handle_name(bot, chat_id, profile, message.text or '')
        elif session.state == BotState.EX_PHONE:
            _handle_phone(bot, chat_id, profile, message)


def _handle_amount(bot, chat_id, profile, session, raw: str) -> None:
    amount = services.parse_amount(raw)
    if amount is None:
        bot.send_message(chat_id, texts.BAD_AMOUNT)
        return
    city = services.resolve_city(profile, session.data)
    pair = services.pair_by_id(int(session.data['pair_id']))
    direction = session.data.get('direction')
    if not city or not pair or not direction:
        bot.send_message(chat_id, texts.UNKNOWN)
        return
    calc = services.quote_amounts(pair, city, direction, amount)
    if calc is None:
        bot.send_message(chat_id, texts.NO_QUOTE)
        return
    branches = list(get_city_branches(city))
    if not branches:
        bot.send_message(chat_id, texts.NO_BRANCHES)
        services.clear_session(profile.chat_id)
        send_menu(bot, chat_id)
        return
    services.patch_session(
        profile.chat_id,
        state=BotState.EX_BRANCH,
        amount_give=str(calc['amount_give']),
        amount_receive=str(calc['amount_receive']),
        rate=str(calc['rate']),
    )
    bot.send_message(
        chat_id,
        f'Курс {calc["rate"]}. Отримаєте ≈ {calc["amount_receive"]}.\n{texts.CHOOSE_BRANCH}',
        reply_markup=keyboards.branches_keyboard(branches),
    )


def _handle_name(bot, chat_id, profile, raw: str) -> None:
    name = raw.strip()
    if not services.is_valid_name(name):
        bot.send_message(chat_id, texts.BAD_NAME)
        return
    services.remember_contacts(profile.chat_id, name=name)
    services.patch_session(profile.chat_id, state=BotState.EX_PHONE, name=name)
    bot.send_message(chat_id, texts.ENTER_PHONE, reply_markup=keyboards.phone_keyboard())


def _handle_phone(bot, chat_id, profile, message) -> None:
    phone = ''
    if message.contact and message.contact.phone_number:
        phone = message.contact.phone_number
    else:
        phone = (message.text or '').strip()
    if not validate_phone(phone):
        bot.send_message(chat_id, texts.BAD_PHONE, reply_markup=keyboards.phone_keyboard())
        return
    phone = normalize_phone(phone)
    services.remember_contacts(profile.chat_id, phone=phone)
    services.patch_session(profile.chat_id, state=BotState.EX_CONSENT, phone=phone)
    bot.send_message(chat_id, 'Дякуємо.', reply_markup=keyboards.remove_reply())
    bot.send_message(chat_id, texts.ASK_CONSENT, reply_markup=keyboards.consent_keyboard())


def _confirm_text(profile, data: dict) -> str:
    pair = services.pair_by_id(int(data['pair_id']))
    city = services.resolve_city(profile, data)
    branch = services.branch_by_id(int(data['branch_id']), city) if city else None
    direction = 'Продати' if data.get('direction') == 'sell' else 'Купити'
    name = texts.safe(data.get('name'))
    phone = texts.safe(data.get('phone'))
    pair_code = texts.safe(pair.code if pair else '')
    address = texts.safe(branch.address if branch else '')
    city_name = texts.safe(city.name if city else '')
    return (
        f'{texts.CONFIRM_PREFIX}\n'
        f'{name} · {phone}\n'
        f'{pair_code} · {direction}\n'
        f'Віддаєте: {data.get("amount_give")} · Отримуєте: {data.get("amount_receive")}\n'
        f'Курс: {data.get("rate")}\n'
        f'{city_name} · {address}'
    )
