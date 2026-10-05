from src.bot.keyboards import (
    CB_BR,
    CB_CANCEL,
    CB_EX,
    CB_FB,
    CB_MENU,
    CB_RATES,
    main_menu,
    remove_reply,
)
from src.bot import services, texts


def send_menu(bot, chat_id: int, text: str = texts.MENU_HINT) -> None:
    bot.send_message(chat_id, text, reply_markup=main_menu())


def cancel_flow(bot, chat_id: int) -> None:
    services.clear_session(str(chat_id))
    bot.send_message(chat_id, texts.CANCELLED, reply_markup=remove_reply())
    send_menu(bot, chat_id)


def register(bot) -> None:
    @bot.message_handler(commands=['start', 'menu'])
    def cmd_start(message) -> None:
        profile = services.upsert_profile(message.from_user)
        services.clear_session(profile.chat_id)
        bot.send_message(message.chat.id, texts.WELCOME, reply_markup=remove_reply())
        send_menu(bot, message.chat.id)

    @bot.message_handler(commands=['help'])
    def cmd_help(message) -> None:
        services.upsert_profile(message.from_user)
        bot.send_message(message.chat.id, texts.HELP, reply_markup=main_menu())

    @bot.message_handler(commands=['cancel'])
    def cmd_cancel(message) -> None:
        services.upsert_profile(message.from_user)
        cancel_flow(bot, message.chat.id)

    @bot.callback_query_handler(func=lambda c: c.data == CB_CANCEL)
    def cb_cancel(call) -> None:
        bot.answer_callback_query(call.id)
        cancel_flow(bot, call.message.chat.id)

    @bot.callback_query_handler(func=lambda c: c.data == CB_MENU)
    def cb_menu(call) -> None:
        bot.answer_callback_query(call.id)
        services.clear_session(str(call.from_user.id))
        send_menu(bot, call.message.chat.id)

    @bot.callback_query_handler(func=lambda c: c.data in {CB_RATES, CB_EX, CB_FB, CB_BR})
    def cb_menu_items(call) -> None:
        from src.bot.handlers import branches, contact, exchange, rates

        bot.answer_callback_query(call.id)
        profile = services.upsert_profile(call.from_user)
        mapping = {
            CB_RATES: rates.start_rates,
            CB_EX: exchange.start_exchange,
            CB_FB: contact.start_feedback,
            CB_BR: branches.start_branches,
        }
        mapping[call.data](bot, call.message.chat.id, profile)
