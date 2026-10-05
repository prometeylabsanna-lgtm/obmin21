from src.bot import keyboards, services, texts
from src.bot.handlers.common import send_menu
from src.bot.states import BotState, FEEDBACK_STATES
from src.leads.services import normalize_phone, validate_phone


def start_feedback(bot, chat_id: int, profile) -> None:
    services.patch_session(profile.chat_id, state=BotState.FB_NAME)
    bot.send_message(chat_id, texts.ENTER_NAME)


def register(bot) -> None:
    @bot.message_handler(commands=['kontakty'])
    def cmd_feedback(message) -> None:
        profile = services.upsert_profile(message.from_user)
        start_feedback(bot, message.chat.id, profile)

    @bot.message_handler(
        func=lambda m: services.get_session(str(m.from_user.id)).state in FEEDBACK_STATES,
        content_types=['text', 'contact'],
    )
    def on_feedback_input(message) -> None:
        profile = services.upsert_profile(message.from_user)
        session = services.get_session(profile.chat_id)
        state = session.state
        chat_id = message.chat.id

        if state == BotState.FB_NAME:
            name = (message.text or '').strip()
            if not services.is_valid_name(name):
                bot.send_message(chat_id, texts.BAD_NAME)
                return
            services.remember_contacts(profile.chat_id, name=name)
            services.patch_session(profile.chat_id, state=BotState.FB_PHONE, name=name)
            bot.send_message(chat_id, texts.ENTER_PHONE, reply_markup=keyboards.phone_keyboard())
            return

        if state == BotState.FB_PHONE:
            phone = _phone_from_message(message)
            if not phone or not validate_phone(phone):
                bot.send_message(chat_id, texts.BAD_PHONE, reply_markup=keyboards.phone_keyboard())
                return
            phone = normalize_phone(phone)
            services.remember_contacts(profile.chat_id, phone=phone)
            services.patch_session(profile.chat_id, state=BotState.FB_TEXT, phone=phone)
            bot.send_message(chat_id, 'Дякуємо.', reply_markup=keyboards.remove_reply())
            bot.send_message(chat_id, texts.ENTER_FEEDBACK)
            return

        if state == BotState.FB_TEXT:
            body = (message.text or '').strip()
            if not services.is_valid_feedback(body):
                bot.send_message(chat_id, texts.BAD_FEEDBACK)
                return
            services.patch_session(profile.chat_id, state=BotState.FB_CONSENT, message=body)
            bot.send_message(chat_id, texts.ASK_CONSENT, reply_markup=keyboards.consent_keyboard())

    @bot.callback_query_handler(
        func=lambda c: c.data in {keyboards.CB_CONSENT_YES, keyboards.CB_CONSENT_NO}
        and services.get_session(str(c.from_user.id)).state == BotState.FB_CONSENT,
    )
    def cb_feedback_consent(call) -> None:
        bot.answer_callback_query(call.id)
        profile = services.upsert_profile(call.from_user)
        chat_id = call.message.chat.id
        if call.data == keyboards.CB_CONSENT_NO:
            bot.send_message(chat_id, texts.NEED_CONSENT)
            services.clear_session(profile.chat_id)
            send_menu(bot, chat_id)
            return
        session = services.get_session(profile.chat_id)
        try:
            services.submit_feedback(profile.chat_id, profile, session.data)
        except ValueError:
            bot.send_message(chat_id, texts.UNKNOWN)
            services.clear_session(profile.chat_id)
            send_menu(bot, chat_id)
            return
        services.clear_session(profile.chat_id)
        bot.send_message(chat_id, texts.SAVED_FEEDBACK)
        send_menu(bot, chat_id)


def _phone_from_message(message) -> str:
    if message.contact and message.contact.phone_number:
        return message.contact.phone_number
    return (message.text or '').strip()
